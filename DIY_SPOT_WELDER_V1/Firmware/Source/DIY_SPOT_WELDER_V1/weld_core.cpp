// SPDX-License-Identifier: GPL-3.0-or-later
#include "weld_core.h"
#include "config.h"
#include "pgm_compat.h"

void settings_default(Settings &s) {
    s.main_ms = 10;
    s.pre_pct = 12;
    s.gap_ms = 10;
    s.trigger_delay_ms = 300;
    s.mode = MODE_FOOT;
    s.auto_delay_ms = 1500;
    s.sound = 1;
    s.rstage_uohm = 5900;   // 6x IRLZ44N hot, see doc 03 (ESTIMATE)
}

template <typename T> static T clampv(T v, T lo, T hi) { return v < lo ? lo : (v > hi ? hi : v); }

void settings_sanitize(Settings &s) {
    s.main_ms = clampv<uint16_t>(s.main_ms, HARD_MIN_MAIN_US / 1000, HARD_MAX_MAIN_US / 1000);
    s.pre_pct = clampv<uint8_t>(s.pre_pct, 0, HARD_MAX_PRE_PCT);
    s.gap_ms = clampv<uint16_t>(s.gap_ms, HARD_MIN_GAP_US / 1000, HARD_MAX_GAP_US / 1000);
    s.trigger_delay_ms = clampv<uint16_t>(s.trigger_delay_ms, MIN_TRIGGER_DELAY_MS, MAX_TRIGGER_DELAY_MS);
    s.mode = s.mode == MODE_AUTO ? MODE_AUTO : MODE_FOOT;
    s.auto_delay_ms = clampv<uint16_t>(s.auto_delay_ms, MIN_AUTO_DELAY_MS, MAX_AUTO_DELAY_MS);
    s.sound = s.sound ? 1 : 0;
    s.rstage_uohm = clampv<uint16_t>(s.rstage_uohm, 500, 50000);
}

bool WeldCore::fault_is_clearable(uint8_t f) {
    switch (f) {
    case F_GATE_STUCK: case F_RELAY_WELDED: case F_LIMITER_TEST: case F_UVLO_TEST:
    case F_STUCK_CURRENT: case F_SEQUENCER:
        return false;
    default:
        return true;
    }
}

bool WeldCore::fault_clearable() const { return fault_is_clearable(fault_); }

// Strings live in flash on the AVR (returned pointers are PROGMEM pointers there).
static const char FN0[] PROGMEM = "NONE";
static const char FN1[] PROGMEM = "WDT RESET";
static const char FN2[] PROGMEM = "BROWNOUT";
static const char FN3[] PROGMEM = "TRIG AT BOOT";
static const char FN4[] PROGMEM = "ARM AT BOOT";
static const char FN5[] PROGMEM = "GATE STUCK";
static const char FN6[] PROGMEM = "RELAY WELDED";
static const char FN7[] PROGMEM = "RELAY NO CLOSE";
static const char FN8[] PROGMEM = "RELAY DROPPED";
static const char FN9[] PROGMEM = "LIMITER TEST";
static const char FN10[] PROGMEM = "UVLO TEST";
static const char FN11[] PROGMEM = "UNDERVOLT";
static const char FN12[] PROGMEM = "OVERVOLT";
static const char FN13[] PROGMEM = "VDRV LOW";
static const char FN14[] PROGMEM = "VHOLD LOW";
static const char FN15[] PROGMEM = "OVERTEMP";
static const char FN16[] PROGMEM = "NTC INVALID";
static const char FN17[] PROGMEM = "STUCK CURRENT";
static const char FN18[] PROGMEM = "HW INTERVENED";
static const char FN19[] PROGMEM = "SEQUENCER";
static const char FN20[] PROGMEM = "PLAN INVALID";
static const char *const FAULT_NAMES[F_COUNT] PROGMEM = {FN0, FN1, FN2, FN3, FN4, FN5, FN6, FN7, FN8, FN9, FN10, FN11, FN12, FN13, FN14, FN15, FN16, FN17, FN18, FN19, FN20};
static const char FN_UNKNOWN[] PROGMEM = "?";

const char *WeldCore::fault_name(uint8_t f) {
    return f < F_COUNT ? (const char *)pgm_read_ptr(&FAULT_NAMES[f]) : FN_UNKNOWN;
}

const char *WeldCore::state_name(State s) {
    switch (s) {
    case State::BOOT: return PSTR("BOOT");
    case State::SELFTEST: return PSTR("SELFTEST");
    case State::DISARMED: return PSTR("DISARMED");
    case State::ARM_LIMTEST: case State::ARM_RECOVER: case State::ARM_RELAY: return PSTR("ARMING");
    case State::READY: return PSTR("READY");
    case State::TRIGGER_WAIT: return PSTR("TRIGGER");
    case State::PULSING: return PSTR("PULSE");
    case State::COOLDOWN: return PSTR("COOLDOWN");
    case State::FAULT: return PSTR("FAULT");
    }
    return PSTR("?");
}

void WeldCore::begin(const Settings &s, uint8_t reset_flags, uint32_t now_ms) {
    set_ = s;
    settings_sanitize(set_);
    reset_flags_ = reset_flags;
    fault_ = F_NONE;
    vbat_f_ = 0;
    t_activity_ = now_ms;
    enter(State::SELFTEST, now_ms);
}

void WeldCore::enter(State s, uint32_t now) {
    st_ = s;
    t_state_ = now;
    fb_seen_ = false;
    mismatch_ = 0;
    uvlo_phase_ = 0;
}

void WeldCore::raise(Fault f, Outputs &out, uint32_t now) {
    if (st_ == State::FAULT) return;              // first fault wins (root cause)
    fault_ = f;
    out.new_fault = f;
    out.abort_pulse = true;
    out.relay = false;
    out.gate_test = false;
    out.start_pulse = false;
    out.beep = BEEP_FAULT;
    enter(State::FAULT, now);
}

bool WeldCore::armed(const Inputs &in) const { return in.arm_a && in.vdrv_mv >= VDRV_OK_MV; }

bool WeldCore::trigger(const Inputs &in) const {
    if (set_.mode == MODE_AUTO)
        return in.vbat_mv > VBAT_PRESENT_MV && (uint32_t)in.vdrain_mv * 100UL >= (uint32_t)in.vbat_mv * CONTACT_FRAC;
    return foot_db_;
}

uint32_t WeldCore::derate(int16_t t) const {
    if (t <= T_HS_DERATE_START_DC) return HARD_MAX_MAIN_US;
    if (t >= T_HS_LIMIT_DC) return DERATED_MIN_MAIN_US;
    return HARD_MAX_MAIN_US - (HARD_MAX_MAIN_US - DERATED_MIN_MAIN_US) * (uint32_t)(t - T_HS_DERATE_START_DC) /
                                  (uint32_t)(T_HS_LIMIT_DC - T_HS_DERATE_START_DC);
}

bool WeldCore::timing_critical() const {
    return st_ == State::ARM_LIMTEST || st_ == State::ARM_RECOVER || st_ == State::ARM_RELAY ||
           st_ == State::TRIGGER_WAIT || st_ == State::PULSING || st_ == State::SELFTEST;
}

bool WeldCore::condition_cleared(const Inputs &in) const {
    switch (fault_) {
    case F_UNDERVOLT: return in.vbat_mv >= VBAT_UV_MV + 300;
    case F_OVERVOLT: return in.vbat_mv <= VBAT_OV_MV - 300;
    case F_OVERTEMP: return in.t_hs_dc <= T_HS_RESUME_DC && in.t_hs_dc >= T_HS_MIN_VALID_DC;
    case F_NTC_INVALID: return in.t_hs_dc > T_HS_MIN_VALID_DC && in.t_hs_dc < T_HS_MAX_VALID_DC;
    case F_TRIGGER_AT_BOOT: return !foot_db_;
    case F_ARMED_AT_BOOT: return !in.arm_a && in.vdrv_mv < VDRV_OK_MV;
    default: return true;
    }
}

// common supervision for READY / TRIGGER_WAIT / COOLDOWN. Returns false if a fault was raised.
bool WeldCore::supervise(const Inputs &in, Outputs &out, bool grace) {
    uint32_t now = in.now_ms;
    uint16_t vf = (uint16_t)(vbat_f_ >> 4);
    if (in.gate_fb && !in.gate_cmd) { raise(F_GATE_STUCK, out, now); return false; }
    if (!grace && vf > VBAT_PRESENT_MV && in.vbat_mv + STUCK_SAG_MV < vf) { raise(F_STUCK_CURRENT, out, now); return false; }
    if (!grace && vf < VBAT_UV_MV) { raise(F_UNDERVOLT, out, now); return false; }
    if (vf > VBAT_OV_MV) { raise(F_OVERVOLT, out, now); return false; }
    if (in.vhold_mv < VHOLD_OK_MV) { raise(F_VHOLD_LOW, out, now); return false; }
    if (in.t_hs_dc <= T_HS_MIN_VALID_DC || in.t_hs_dc >= T_HS_MAX_VALID_DC) { raise(F_NTC_INVALID, out, now); return false; }
    if (in.t_hs_dc >= T_HS_LIMIT_DC) { raise(F_OVERTEMP, out, now); return false; }
    if (!grace && (uint32_t)in.velec_mv * 100UL < (uint32_t)in.vbat_mv * VELEC_CLOSED_FRAC) { raise(F_RELAY_DROPPED, out, now); return false; }
    return true;
}

void WeldCore::step(const Inputs &in, Outputs &out) {
    const uint32_t now = in.now_ms;
    const uint32_t dt = now - t_state_;
    out = Outputs();
    out.plan = plan_;

    // --- input conditioning --------------------------------------------------------------
    if (vbat_f_ == 0) vbat_f_ = (uint32_t)in.vbat_mv << 4;
    else if (st_ != State::PULSING) vbat_f_ += ((int32_t)((uint32_t)in.vbat_mv << 4) - (int32_t)vbat_f_) / 32;  // slow EMA
    if (in.foot != foot_raw_prev_) { foot_raw_prev_ = in.foot; t_foot_chg_ = now; }
    if (now - t_foot_chg_ >= DEBOUNCE_MS) foot_db_ = in.foot;
    if (in.ack != ack_raw_prev_) { ack_raw_prev_ = in.ack; t_ack_chg_ = now; }
    if (now - t_ack_chg_ >= DEBOUNCE_MS) ack_db_ = in.ack;
    bool ack_edge = ack_db_ && !ack_prev_;
    ack_prev_ = ack_db_;
    if (in.activity || foot_db_ || ack_db_) t_activity_ = now;
    if (!in.arm_a && in.vdrv_mv < VDRV_OK_MV) arm_seen_off_ = true;
    allowed_main_us_ = derate(in.t_hs_dc);

    switch (st_) {
    case State::BOOT:
        enter(State::SELFTEST, now);
        break;

    case State::SELFTEST:
        // Relay open, no pulse. Let filters / hold-up settle, then test.
        if (uvlo_phase_ == 0) {
            if (dt < 200) break;
            if (reset_flags_ & RST_WDT) { raise(F_WDT_RESET, out, now); break; }
            if (reset_flags_ & RST_BOR) { raise(F_BROWNOUT_RESET, out, now); break; }
            if (in.gate_fb) { raise(F_GATE_STUCK, out, now); break; }
            if (in.vbat_mv > VBAT_PRESENT_MV && in.velec_mv > VELEC_OPEN_MV) { raise(F_RELAY_WELDED, out, now); break; }
            if (foot_db_) { raise(F_TRIGGER_AT_BOOT, out, now); break; }
            if (in.arm_a || in.vdrv_mv >= VDRV_OK_MV) { raise(F_ARMED_AT_BOOT, out, now); break; }
            uvlo_phase_ = 1;              // UVLO test: driver unpowered -> GIN must stay low
            t_state_ = now;
            out.gate_test = true;
            break;
        }
        out.gate_test = true;
        if (in.gate_fb && now - t_state_ >= 1) { out.gate_test = false; raise(F_UVLO_TEST, out, now); break; }
        if (now - t_state_ >= 5) { out.gate_test = false; enter(State::DISARMED, now); }
        break;

    case State::DISARMED:
        out.relay = false;
        if (in.gate_fb && !in.gate_cmd) { raise(F_GATE_STUCK, out, now); break; }
        if (in.vbat_mv > VBAT_PRESENT_MV && in.velec_mv > VELEC_OPEN_MV && dt > RELAY_SETTLE_MS) { raise(F_RELAY_WELDED, out, now); break; }
        if (armed(in) && arm_seen_off_ && dt > 300) {
            // preconditions for arming
            if (in.vbat_mv < VBAT_UV_MV) { raise(F_UNDERVOLT, out, now); break; }
            if (in.vbat_mv > VBAT_OV_MV) { raise(F_OVERVOLT, out, now); break; }
            if (in.t_hs_dc <= T_HS_MIN_VALID_DC || in.t_hs_dc >= T_HS_MAX_VALID_DC) { raise(F_NTC_INVALID, out, now); break; }
            if (in.t_hs_dc >= T_HS_LIMIT_DC) { raise(F_OVERTEMP, out, now); break; }
            if (in.vhold_mv < VHOLD_OK_MV) { raise(F_VHOLD_LOW, out, now); break; }
            arm_seen_off_ = false;
            vbat_f_ = (uint32_t)in.vbat_mv << 4;
            enter(State::ARM_LIMTEST, now);
            out.gate_test = true;                  // relay is OPEN: no current path exists
        }
        break;

    case State::ARM_LIMTEST:
        // GATE_CMD high with the relay open. GATE_FB must rise at once and must be pulled low
        // by the hardware limiter (U3A) inside [LIMTEST_MIN_MS, LIMTEST_MAX_MS].
        out.relay = false;
        out.gate_test = true;
        if (!armed(in)) { out.gate_test = false; enter(State::DISARMED, now); break; }
        if (in.gate_fb) fb_seen_ = true;
        if (!fb_seen_ && dt > LIMTEST_FB_RISE_MS) { out.gate_test = false; raise(F_LIMITER_TEST, out, now); break; }
        if (fb_seen_ && !in.gate_fb) {
            out.gate_test = false;
            if (dt < LIMTEST_MIN_MS) { raise(F_LIMITER_TEST, out, now); break; }
            enter(State::ARM_RECOVER, now);
            break;
        }
        if (dt > LIMTEST_MAX_MS) { out.gate_test = false; raise(F_LIMITER_TEST, out, now); }
        break;

    case State::ARM_RECOVER:
        out.relay = false;
        if (in.gate_fb) { raise(F_GATE_STUCK, out, now); break; }
        if (!armed(in)) { enter(State::DISARMED, now); break; }
        if (dt >= LIMTEST_RECOVER_MS) {
            if (in.velec_mv > VELEC_OPEN_MV) { raise(F_RELAY_WELDED, out, now); break; }
            enter(State::ARM_RELAY, now);
            out.relay = true;
        }
        break;

    case State::ARM_RELAY:
        out.relay = true;
        if (in.gate_fb) { raise(F_GATE_STUCK, out, now); break; }
        if (!armed(in)) { out.relay = false; enter(State::DISARMED, now); break; }
        if (dt >= RELAY_SETTLE_MS) {
            if ((uint32_t)in.velec_mv * 100UL < (uint32_t)in.vbat_mv * VELEC_CLOSED_FRAC) { raise(F_RELAY_NO_CLOSE, out, now); break; }
            t_activity_ = now;
            out.beep = BEEP_READY;
            enter(State::READY, now);
        }
        break;

    case State::READY:
        out.relay = true;
        out.led_ready = true;
        if (!armed(in)) { out.relay = false; enter(State::DISARMED, now); break; }
        if (!supervise(in, out, false)) break;
        if (now - t_activity_ > STANDBY_MS) { out.relay = false; arm_seen_off_ = false; enter(State::DISARMED, now); break; }
        if (trigger(in)) enter(State::TRIGGER_WAIT, now);
        break;

    case State::TRIGGER_WAIT:
        out.relay = true;
        out.led_ready = true;
        if (!armed(in)) { out.relay = false; enter(State::DISARMED, now); break; }
        if (!supervise(in, out, false)) break;
        if (!trigger(in)) { enter(State::READY, now); break; }   // released / glitch: NO pulse
        if (dt >= (set_.mode == MODE_AUTO ? set_.auto_delay_ms : set_.trigger_delay_ms)) {
            plan_ = make_plan(set_.main_ms, set_.pre_pct, set_.gap_ms, allowed_main_us_);
            if (!plan_valid(plan_)) { raise(F_PLAN_INVALID, out, now); break; }
            if (in.seq_active || in.gate_fb) { raise(F_GATE_STUCK, out, now); break; }
            out.plan = plan_;
            out.start_pulse = true;
            if (set_.sound) out.beep = BEEP_WELD;
            last_.vbat_min_mv = 0xFFFF;
            last_.vds_mv = 0;
            last_.on_us = plan_on_us(plan_);
            enter(State::PULSING, now);
        }
        break;

    case State::PULSING: {
        out.relay = true;
        // Effective gate must follow the command (hardware may only cut it).
        if (in.gate_cmd && !in.gate_fb) mismatch_++;
        else if (!in.gate_cmd && in.gate_fb) mismatch_ += 2;   // 2 consecutive samples (ISR edge race)
        else mismatch_ = 0;
        if (mismatch_ >= 4) {
            out.abort_pulse = true;
            raise(in.gate_cmd ? F_HW_INTERVENED : F_GATE_STUCK, out, now);
            break;
        }
        if (in.gate_cmd) {
            if (in.vbat_mv < last_.vbat_min_mv) last_.vbat_min_mv = in.vbat_mv;
            if (in.vdrain_mv > last_.vds_mv) last_.vds_mv = in.vdrain_mv;
        }
        if (dt > plan_total_us(plan_) / 1000UL + SEQ_GUARD_MS) { out.abort_pulse = true; raise(F_SEQUENCER, out, now); break; }
        if (!in.seq_active && dt >= 1) {
            if (last_.vbat_min_mv == 0xFFFF) last_.vbat_min_mv = in.vbat_mv;
            last_.i_est_a = (uint16_t)((uint32_t)last_.vds_mv * 1000UL / set_.rstage_uohm);
            welds_++;
            last_on_us_ = plan_on_us(plan_);
            t_last_end_ = now;
            out.weld_done = true;
            enter(State::COOLDOWN, now);
        }
        break;
    }

    case State::COOLDOWN: {
        out.relay = true;
        if (!armed(in)) { out.relay = false; enter(State::DISARMED, now); break; }
        bool grace = (now - t_last_end_) < 1000;      // battery recovers after the pulse
        if (!supervise(in, out, grace)) break;
        uint32_t min_gap = last_on_us_ / 1000UL * DUTY_FACTOR;
        if (min_gap < RETRIGGER_DELAY_MS) min_gap = RETRIGGER_DELAY_MS;
        if (!trigger(in) && now - t_last_end_ >= min_gap && !grace) enter(State::READY, now);
        break;
    }

    case State::FAULT:
        out.relay = false;
        out.led_fault = true;
        out.abort_pulse = in.seq_active;
        if (fault_is_clearable(fault_) && ack_edge && condition_cleared(in) && !foot_db_) {
            fault_ = F_NONE;
            out.beep = BEEP_SHORT;
            enter(State::DISARMED, now);         // ARM must be cycled off -> on to re-arm
        }
        break;
    }
    // global invariants
    if (st_ == State::FAULT || st_ == State::DISARMED || st_ == State::SELFTEST) out.start_pulse = false;
    if (out.relay && (st_ == State::FAULT || st_ == State::DISARMED || st_ == State::SELFTEST || st_ == State::ARM_LIMTEST)) out.relay = false;
}
