// SPDX-License-Identifier: GPL-3.0-or-later
// DIY_SPOT_WELDER_V1 - host tests: pulse plan/timing, state machine, fault injection, fuzzing.
// Build & run:  make -C Firmware/Tests     (g++ >= 7)
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <random>
#include <string>
#include <vector>
#include "config.h"
#include "sim_plant.h"

static int g_fail = 0, g_checks = 0;
static std::string g_test;
#define CHECK(c) do { g_checks++; if (!(c)) { g_fail++; std::printf("  FAIL %s:%d [%s] %s\n", __FILE__, __LINE__, g_test.c_str(), #c); } } while (0)
#define CHECK_EQ(a, b) do { g_checks++; auto _a = (a); auto _b = (b); if (!(_a == _b)) { g_fail++; \
    std::printf("  FAIL %s:%d [%s] %s == %s  (%lld vs %lld)\n", __FILE__, __LINE__, g_test.c_str(), #a, #b, (long long)_a, (long long)_b); } } while (0)

struct Rig {
    SimPlant p;
    WeldCore core;
    Settings s;
    Outputs last{};
    std::vector<uint8_t> faults_logged;
    int pulses_started = 0;
    explicit Rig(uint8_t reset = RST_POR) {
        settings_default(s);
        core.begin(s, reset, 0);
    }
    void step(int ms = 1) {
        for (int i = 0; i < ms; i++) {
            Inputs in = p.inputs();
            Outputs o;
            core.step(in, o);
            // ---- invariants checked on every step ----
            if (o.start_pulse) { pulses_started++; CHECK(core.state() == State::PULSING); CHECK(o.relay); }
            if (o.gate_test) CHECK(!o.relay);
            if (core.state() == State::FAULT) { CHECK(!o.relay); CHECK(!o.start_pulse); }
            if (o.new_fault) faults_logged.push_back(o.new_fault);
            p.apply(o);
            last = o;
            p.tick_1ms();
        }
    }
    void press_ack() { p.ack = true; step(60); p.ack = false; step(60); }
    bool arm_to_ready(int max_ms = 2000) {
        p.arm = true;
        for (int i = 0; i < max_ms; i++) { step(); if (core.state() == State::READY) return true; if (core.state() == State::FAULT) return false; }
        return false;
    }
};

static void test(const char *name, const std::function<void()> &f) {
    g_test = name;
    int before = g_fail;
    f();
    std::printf("%s %s\n", g_fail == before ? "PASS" : "FAIL", name);
}

int main() {
    // ------------------------------------------------------------------ pulse plan & sequencer
    test("plan: default 10 ms / 12 % / 10 ms gap", [] {
        PulsePlan p = make_plan(10, 12, 10, HARD_MAX_MAIN_US);
        CHECK_EQ(p.main_us, 10000u); CHECK_EQ(p.pre_us, 1200u); CHECK_EQ(p.gap_us, 10000u); CHECK(plan_valid(p));
    });
    test("plan: hard limits cannot be exceeded", [] {
        PulsePlan p = make_plan(500, 100, 500, 0xFFFFFFFF);
        CHECK(p.main_us <= HARD_MAX_MAIN_US); CHECK(p.pre_us <= p.main_us * HARD_MAX_PRE_PCT / 100);
        CHECK(p.gap_us <= HARD_MAX_GAP_US); CHECK(plan_on_us(p) <= HARD_MAX_TOTAL_ON_US); CHECK(plan_valid(p));
        PulsePlan q = make_plan(0, 0, 0, 0);
        CHECK_EQ(q.main_us, (uint32_t)HARD_MIN_MAIN_US); CHECK_EQ(q.pre_us, 0u); CHECK(plan_valid(q));
    });
    test("plan: thermal derating limits main pulse", [] {
        PulsePlan p = make_plan(50, 0, 10, 20000);
        CHECK_EQ(p.main_us, 20000u);
    });
    test("plan: invalid plans rejected by sequencer (gate stays OFF)", [] {
        PulseSequencer s; bool g = true; uint32_t n;
        PulsePlan bad{0, 0, HARD_MAX_MAIN_US + 1};
        CHECK(!s.start(bad, &g, &n)); CHECK(!g); CHECK(!s.active());
        PulsePlan bad2{HARD_MAX_MAIN_US, 100, 10000};
        CHECK(!s.start(bad2, &g, &n)); CHECK(!g);
    });
    test("sequencer: step order and durations", [] {
        PulseSequencer s; bool g; uint32_t n;
        PulsePlan p = make_plan(20, 10, 5, HARD_MAX_MAIN_US);
        CHECK(s.start(p, &g, &n)); CHECK(g); CHECK_EQ(n, 2000u);
        CHECK(s.on_timer(&g, &n)); CHECK(!g); CHECK_EQ(n, 5000u);
        CHECK(s.on_timer(&g, &n)); CHECK(g); CHECK_EQ(n, 20000u);
        CHECK(!s.on_timer(&g, &n)); CHECK(!g); CHECK(!s.active());
        bool g2; uint32_t n2;
        CHECK(s.start(make_plan(5, 0, 0, HARD_MAX_MAIN_US), &g2, &n2)); CHECK_EQ(n2, 5000u);
        s.abort(); CHECK(!s.active());
    });

    // ------------------------------------------------------------------ boot / self-test
    test("boot: normal power-up reaches DISARMED, relay open, gate off", [] {
        Rig r; r.step(400);
        CHECK(r.core.state() == State::DISARMED); CHECK(!r.last.relay); CHECK(!r.p.gate_pin); CHECK_EQ(r.pulses_started, 0);
    });
    test("boot: watchdog reset is reported and latched until ACK", [] {
        Rig r(RST_WDT); r.step(400);
        CHECK(r.core.state() == State::FAULT); CHECK_EQ(r.core.fault(), F_WDT_RESET);
        r.step(1000); CHECK(r.core.state() == State::FAULT);
        r.press_ack(); CHECK(r.core.state() == State::DISARMED);
    });
    test("boot: foot switch held at power-up -> fault, clears only after release + ACK", [] {
        Rig r; r.p.foot = true; r.step(400);
        CHECK_EQ(r.core.fault(), F_TRIGGER_AT_BOOT);
        r.press_ack(); CHECK(r.core.state() == State::FAULT);       // still pressed
        r.p.foot = false; r.step(100); r.press_ack(); CHECK(r.core.state() == State::DISARMED);
    });
    test("boot: ARM closed at power-up -> fault; must open ARM, ACK, then re-arm", [] {
        Rig r; r.p.arm = true; r.step(400);
        CHECK_EQ(r.core.fault(), F_ARMED_AT_BOOT);
        r.press_ack(); CHECK(r.core.state() == State::FAULT);
        r.p.arm = false; r.step(50); r.press_ack(); CHECK(r.core.state() == State::DISARMED);
        CHECK(r.arm_to_ready());
    });
    test("boot: gate feedback stuck high -> non-clearable fault", [] {
        Rig r; r.p.gate_fb_stuck_high = true; r.step(400);
        CHECK_EQ(r.core.fault(), F_GATE_STUCK); r.p.gate_fb_stuck_high = false; r.press_ack();
        CHECK(r.core.state() == State::FAULT);
    });
    test("boot: welded relay detected (electrode live with relay open)", [] {
        Rig r; r.p.relay_welded = true; r.p.relay_closed = true; r.step(400);
        CHECK_EQ(r.core.fault(), F_RELAY_WELDED);
    });
    test("boot: broken UVLO detected by self-test", [] {
        Rig r; r.p.uvlo_broken = true; r.step(400);
        CHECK_EQ(r.core.fault(), F_UVLO_TEST);
    });

    // ------------------------------------------------------------------ arming
    test("arm: limiter self-test passes, relay closes, READY; no current during test", [] {
        Rig r; r.p.touching = true; r.step(400);
        CHECK(r.arm_to_ready());
        CHECK_EQ(r.p.max_current, 0.0);                 // relay was open during the MOSFET-on self-test
        CHECK(r.p.relay_closed);
        CHECK_EQ(r.pulses_started, 0);
    });
    test("arm: broken hardware limiter -> LIMITER_TEST fault (non-clearable)", [] {
        Rig r; r.p.limiter_broken = true; r.step(400);
        CHECK(!r.arm_to_ready()); CHECK_EQ(r.core.fault(), F_LIMITER_TEST);
        r.press_ack(); CHECK(r.core.state() == State::FAULT);
    });
    test("arm: limiter tripping too early (e.g. wrong capacitor) -> fault", [] {
        Rig r; r.p.pl_tau_ms = 20; r.step(400);
        CHECK(!r.arm_to_ready()); CHECK_EQ(r.core.fault(), F_LIMITER_TEST);
    });
    test("arm: relay that does not close -> RELAY_NO_CLOSE", [] {
        Rig r; r.p.relay_operate_ms = 1e9; r.step(400);
        CHECK(!r.arm_to_ready()); CHECK_EQ(r.core.fault(), F_RELAY_NO_CLOSE);
    });
    test("arm: undervoltage battery refuses to arm", [] {
        Rig r; r.p.ocv = 11.0; r.step(400);
        CHECK(!r.arm_to_ready()); CHECK_EQ(r.core.fault(), F_UNDERVOLT);
    });
    test("arm: opening ARM while READY opens relay -> DISARMED, re-arm requires off->on", [] {
        Rig r; r.step(400); CHECK(r.arm_to_ready());
        r.p.arm = false; r.step(30); CHECK(r.core.state() == State::DISARMED); CHECK(!r.last.relay);
        r.step(30); CHECK(!r.p.relay_closed);
        CHECK(r.arm_to_ready());
    });

    // ------------------------------------------------------------------ triggering & pulses
    test("trigger: foot glitch shorter than trigger delay gives NO pulse (reference bug fixed)", [] {
        Rig r; r.step(400); CHECK(r.arm_to_ready()); r.p.touching = true;
        r.p.foot = true; r.step(10); r.p.foot = false; r.step(400);      // 10 ms glitch
        r.p.foot = true; r.step(200); r.p.foot = false; r.step(400);     // 200 ms < 300 ms delay
        CHECK_EQ(r.pulses_started, 0); CHECK(r.p.on_intervals.empty());
    });
    test("trigger: one pulse per press, exact timing, no re-trigger while held", [] {
        Rig r; r.step(400); CHECK(r.arm_to_ready()); r.p.touching = true;
        r.p.foot = true; r.step(3000);
        CHECK_EQ(r.pulses_started, 1);
        CHECK_EQ(r.p.on_intervals.size(), (size_t)2);                   // pre + main
        if (r.p.on_intervals.size() == 2) {
            double pre = r.p.on_intervals[0].t_off_us - r.p.on_intervals[0].t_on_us;
            double gap = r.p.on_intervals[1].t_on_us - r.p.on_intervals[0].t_off_us;
            double mn = r.p.on_intervals[1].t_off_us - r.p.on_intervals[1].t_on_us;
            CHECK(std::fabs(pre - 1200) <= 10); CHECK(std::fabs(gap - 10000) <= 10); CHECK(std::fabs(mn - 10000) <= 10);
        }
        CHECK(r.p.max_current > 200 && r.p.max_current < 400);          // model estimate ~294 A
        r.p.foot = false; r.step(1500); CHECK(r.core.state() == State::READY);
        r.p.foot = true; r.step(1000); CHECK_EQ(r.pulses_started, 2);
        CHECK_EQ(r.core.weld_count(), 2u);
    });
    test("trigger: AUTO mode needs continuous contact for the auto delay", [] {
        Rig r; r.s.mode = MODE_AUTO; r.core.set_settings(r.s); r.step(400); CHECK(r.arm_to_ready());
        r.p.touching = true; r.step(800); r.p.touching = false; r.step(300);   // 800 ms < 1500 ms
        CHECK_EQ(r.pulses_started, 0);
        r.p.touching = true; r.step(2500); CHECK_EQ(r.pulses_started, 1);
        r.step(3000); CHECK_EQ(r.pulses_started, 1);                         // still touching: no repeat
    });
    test("pulse: maximum main pulse is 50 ms even if the setting is larger", [] {
        Rig r; r.s.main_ms = 400; r.s.pre_pct = 0; r.core.set_settings(r.s); r.step(400); CHECK(r.arm_to_ready());
        r.p.touching = true; r.p.foot = true; r.step(1500);
        CHECK_EQ(r.p.on_intervals.size(), (size_t)1);
        if (!r.p.on_intervals.empty()) CHECK(r.p.on_intervals[0].t_off_us - r.p.on_intervals[0].t_on_us <= HARD_MAX_MAIN_US + 10);
    });
    test("pulse: duty-cycle limit enforces >= 20x ON time between welds", [] {
        Rig r; r.s.main_ms = 50; r.s.pre_pct = 0; r.core.set_settings(r.s); r.step(400); CHECK(r.arm_to_ready());
        r.p.touching = true; r.p.foot = true; r.step(400); r.p.foot = false;
        double t_end = r.p.on_intervals.empty() ? 0 : r.p.on_intervals[0].t_off_us / 1000.0;
        while (r.core.state() != State::READY && r.p.t_ms < 10000) r.step();
        CHECK(r.p.t_ms - t_end >= 50 * DUTY_FACTOR - 2);
    });

    // ------------------------------------------------------------------ fault injection
    test("fault: MOSFET short while READY -> STUCK_CURRENT, relay opens, non-clearable", [] {
        Rig r; r.step(400); CHECK(r.arm_to_ready());
        r.p.fet_shorted = true; r.p.touching = true; r.step(5);
        CHECK_EQ(r.core.fault(), F_STUCK_CURRENT); CHECK(!r.last.relay);
        r.step(20); CHECK(!r.p.relay_closed); CHECK_EQ(r.p.current(), 0.0);
        r.p.touching = false; r.press_ack(); CHECK(r.core.state() == State::FAULT);
    });
    test("fault: hardware limiter cutting a pulse is detected (HW_INTERVENED)", [] {
        // limiter capacitor 4x too small -> trips during a long pulse but after the arming test window? use tau so test passes, pulse cut
        Rig r; r.s.main_ms = 50; r.s.pre_pct = 30; r.s.gap_ms = 2; r.core.set_settings(r.s); r.step(400);
        CHECK(r.arm_to_ready());
        r.p.pl_tau_ms = 35;                       // degrade after arming (component drift)
        r.p.touching = true; r.p.foot = true; r.step(500);
        CHECK_EQ(r.core.fault(), F_HW_INTERVENED);
    });
    test("fault: sequencer hang -> SEQUENCER fault and pulse aborted by the core", [] {
        Rig r; r.step(400); CHECK(r.arm_to_ready());
        r.p.seq_hang = true; r.p.touching = true; r.p.foot = true; r.step(500);
        CHECK_EQ(r.core.fault(), F_SEQUENCER); CHECK(!r.p.gate_pin);
        // the RC limiter would have cut the hardware pulse anyway: effective ON <= HW window
        for (auto &iv : r.p.on_intervals) CHECK(iv.t_off_us - iv.t_on_us <= 100000);
    });
    test("fault: over-temperature locks out, clears below 50 C with ACK", [] {
        Rig r; r.step(400); CHECK(r.arm_to_ready());
        r.p.t_hs_c = 61; r.step(5); CHECK_EQ(r.core.fault(), F_OVERTEMP);
        r.p.t_hs_c = 55; r.press_ack(); CHECK(r.core.state() == State::FAULT);
        r.p.t_hs_c = 45; r.press_ack(); CHECK(r.core.state() == State::DISARMED);
    });
    test("fault: open NTC -> NTC_INVALID", [] {
        Rig r; r.step(400); CHECK(r.arm_to_ready()); r.p.ntc_open = true; r.step(5);
        CHECK_EQ(r.core.fault(), F_NTC_INVALID);
    });
    test("derate: 50 C heatsink limits pulse to 35 ms", [] {
        Rig r; r.s.main_ms = 50; r.s.pre_pct = 0; r.core.set_settings(r.s); r.p.t_hs_c = 50; r.step(400);
        CHECK(r.arm_to_ready()); r.p.touching = true; r.p.foot = true; r.step(600);
        CHECK_EQ(r.p.on_intervals.size(), (size_t)1);
        if (!r.p.on_intervals.empty()) { double d = r.p.on_intervals[0].t_off_us - r.p.on_intervals[0].t_on_us; CHECK(std::fabs(d - 35000) <= 20); }
    });
    test("fault: battery disconnected while READY -> relay dropped / undervoltage, relay opened", [] {
        Rig r; r.step(400); CHECK(r.arm_to_ready()); r.p.battery_connected = false; r.step(200);
        CHECK(r.core.state() == State::FAULT); CHECK(!r.last.relay);
    });

    // ------------------------------------------------------------------ fuzz
    test("fuzz: 200 random scenarios x 20 s - safety invariants hold", [] {
        std::mt19937 rng(12345);
        int scen = 0, pulses = 0;
        for (; scen < 200; scen++) {
            Rig r(rng() % 8 == 0 ? RST_WDT : RST_POR);
            r.s.main_ms = rng() % 120; r.s.pre_pct = rng() % 60; r.s.gap_ms = rng() % 80;
            r.s.mode = rng() % 3 == 0 ? MODE_AUTO : MODE_FOOT; r.core.set_settings(r.s);
            for (int t = 0; t < 20000; t++) {
                if (rng() % 300 == 0) r.p.foot = !r.p.foot;
                if (rng() % 500 == 0) r.p.arm = !r.p.arm;
                if (rng() % 400 == 0) r.p.touching = !r.p.touching;
                if (rng() % 700 == 0) r.p.ack = !r.p.ack;
                if (rng() % 20000 == 0) r.p.fet_shorted = true;
                if (rng() % 20000 == 0) r.p.t_hs_c = 70;
                if (rng() % 15000 == 0) r.p.ocv = 11.2;
                r.step();
                // invariant: an effective gate ON interval never exceeds the HW limiter window or the FW limit
                // (only when the MOSFETs are not shorted)
                // invariant: current only flows while READY/PULSING/COOLDOWN or with an injected short
                if (r.p.current() > 0 && !r.p.fet_shorted)
                    CHECK(r.core.state() == State::PULSING || r.core.state() == State::COOLDOWN);
            }
            for (auto &iv : r.p.on_intervals) {
                double d = iv.t_off_us - iv.t_on_us;
                if (!r.p.fet_shorted) CHECK(d <= HARD_MAX_MAIN_US + 20 || r.p.relay_closed == false);
            }
            pulses += r.pulses_started;
        }
        std::printf("    (%d scenarios, %d pulses started)\n", scen, pulses);
        CHECK(pulses > 50);
    });

    std::printf("\n%d checks, %d failures\n", g_checks, g_fail);
    return g_fail ? 1 : 0;
}
