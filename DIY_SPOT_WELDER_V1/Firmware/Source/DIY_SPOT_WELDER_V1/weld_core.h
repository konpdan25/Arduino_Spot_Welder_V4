// SPDX-License-Identifier: GPL-3.0-or-later
// DIY_SPOT_WELDER_V1 - weld-enable state machine, supervision and latched faults.
// Hardware independent: compiled for the AVR target AND for the host test harness.
//
// IMPORTANT: this software layer is NOT the only protection. Hardware layers (fuse, disconnect,
// E-STOP/ARM chain, default-off pull-down, RC pulse limiter, gate-drive UVLO) act without it.
#pragma once
#include <stdint.h>
#include "pulse_sequencer.h"

enum class State : uint8_t {
    BOOT, SELFTEST, DISARMED, ARM_LIMTEST, ARM_RECOVER, ARM_RELAY, READY, TRIGGER_WAIT, PULSING, COOLDOWN, FAULT
};

enum Fault : uint8_t {
    F_NONE = 0,
    F_WDT_RESET,        // last reset was caused by the watchdog
    F_BROWNOUT_RESET,   // last reset was a brown-out
    F_TRIGGER_AT_BOOT,  // foot switch pressed during power-up
    F_ARMED_AT_BOOT,    // ARM chain closed during power-up
    F_GATE_STUCK,       // GATE_FB high while the gate command is low       (non-clearable)
    F_RELAY_WELDED,     // electrode voltage present with relay open        (non-clearable)
    F_RELAY_NO_CLOSE,   // relay commanded closed but electrode voltage missing
    F_RELAY_DROPPED,    // electrode voltage lost while READY
    F_LIMITER_TEST,     // hardware pulse limiter self-test failed          (non-clearable)
    F_UVLO_TEST,        // gate-drive UVLO self-test failed                 (non-clearable)
    F_UNDERVOLT,
    F_OVERVOLT,
    F_VDRV_LOW,
    F_VHOLD_LOW,
    F_OVERTEMP,
    F_NTC_INVALID,
    F_STUCK_CURRENT,    // battery sag without a commanded pulse (MOSFET short?) (non-clearable)
    F_HW_INTERVENED,    // GATE_FB dropped during a commanded pulse (limiter/UVLO acted)
    F_SEQUENCER,        // pulse did not end in time                        (non-clearable)
    F_PLAN_INVALID,
    F_COUNT
};

enum ResetFlags : uint8_t { RST_POR = 1, RST_EXT = 2, RST_BOR = 4, RST_WDT = 8 };
enum Mode : uint8_t { MODE_FOOT = 0, MODE_AUTO = 1 };
enum Beep : uint8_t { BEEP_NONE = 0, BEEP_SHORT, BEEP_WELD, BEEP_FAULT, BEEP_READY };

struct Settings {
    uint16_t main_ms;           // 1..50
    uint8_t  pre_pct;           // 0..30
    uint16_t gap_ms;            // 2..50
    uint16_t trigger_delay_ms;  // 150..2000
    uint8_t  mode;              // MODE_FOOT / MODE_AUTO
    uint16_t auto_delay_ms;     // 500..5000
    uint8_t  sound;             // 0/1
    uint16_t rstage_uohm;       // effective MOSFET stage resistance for the current ESTIMATE
};

void settings_default(Settings &s);
void settings_sanitize(Settings &s);

struct Inputs {
    uint32_t now_ms;
    uint16_t vbat_mv, vdrain_mv, velec_mv, vdrv_mv, vhold_mv;
    int16_t  t_hs_dc;           // heatsink NTC, 0.1 C
    bool     foot;              // raw (debounced in the core)
    bool     ack;               // raw
    bool     arm_a;             // relay pole of the ARM chain closed
    bool     gate_cmd;          // actual state of the GATE_CMD pin
    bool     gate_fb;           // effective driver input (after limiter / UVLO)
    bool     seq_active;        // pulse sequencer running
    bool     activity;          // encoder / button activity (standby timer)
};

struct Outputs {
    bool      relay;
    bool      gate_test;        // drive GATE_CMD high directly (self-tests, relay OPEN only)
    bool      start_pulse;      // one-shot request to start `plan`
    PulsePlan plan;
    bool      abort_pulse;
    bool      led_fault, led_ready;
    uint8_t   beep;
    uint8_t   new_fault;        // != F_NONE once, when a fault is latched (for the EEPROM log)
    bool      weld_done;        // one-shot after each completed pulse
};

struct WeldRecord {
    uint16_t vbat_min_mv;       // battery minimum during the pulse
    uint16_t vds_mv;            // drain voltage during the main pulse (max sample)
    uint16_t i_est_a;           // = vds / rstage (ESTIMATE, +-30 %)
    uint32_t on_us;
};

class WeldCore {
public:
    void begin(const Settings &s, uint8_t reset_flags, uint32_t now_ms);
    void step(const Inputs &in, Outputs &out);
    void set_settings(const Settings &s) { set_ = s; settings_sanitize(set_); }
    const Settings &settings() const { return set_; }

    State state() const { return st_; }
    Fault fault() const { return fault_; }
    bool  fault_clearable() const;
    bool  timing_critical() const;     // UI must not block (I2C) in these states
    uint32_t weld_count() const { return welds_; }
    void  set_weld_count(uint32_t n) { welds_ = n; }
    const WeldRecord &last() const { return last_; }
    uint32_t allowed_main_us() const { return allowed_main_us_; }
    uint16_t vbat_filt_mv() const { return (uint16_t)(vbat_f_ >> 4); }

    static bool fault_is_clearable(uint8_t f);
    static const char *fault_name(uint8_t f);   // PROGMEM pointer on the AVR
    static const char *state_name(State s);     // PROGMEM pointer on the AVR

private:
    void enter(State s, uint32_t now);
    void raise(Fault f, Outputs &out, uint32_t now);
    bool supervise(const Inputs &in, Outputs &out, bool after_pulse_grace);
    bool condition_cleared(const Inputs &in) const;
    bool armed(const Inputs &in) const;
    bool trigger(const Inputs &in) const;
    uint32_t derate(int16_t t_dc) const;

    Settings set_;
    State st_ = State::BOOT;
    Fault fault_ = F_NONE;
    uint8_t reset_flags_ = 0;
    uint32_t t_state_ = 0, t_last_end_ = 0, t_activity_ = 0, last_on_us_ = 0;
    uint32_t vbat_f_ = 0;                   // filtered VBAT x16
    bool foot_db_ = false, ack_db_ = false, ack_prev_ = false;
    uint32_t t_foot_chg_ = 0, t_ack_chg_ = 0;
    bool foot_raw_prev_ = false, ack_raw_prev_ = false;
    bool arm_seen_off_ = false;
    bool fb_seen_ = false;
    uint8_t mismatch_ = 0;
    uint8_t uvlo_phase_ = 0;
    uint32_t welds_ = 0;
    uint32_t allowed_main_us_ = 0;
    WeldRecord last_ = {0, 0, 0, 0};
    PulsePlan plan_ = {0, 0, 0};
};
