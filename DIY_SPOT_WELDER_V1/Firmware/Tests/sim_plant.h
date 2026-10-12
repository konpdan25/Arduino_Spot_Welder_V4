// SPDX-License-Identifier: GPL-3.0-or-later
// Host simulation of the DIY_SPOT_WELDER_V1 hardware around the MCU (non-energised test harness).
// Models: relay operate/release delay, RC pulse limiter + LM393, gate-drive UVLO, battery +
// welding loop (ESTIMATED values from doc 03), NTC temperature, operator inputs, fault injection.
// It is a logic-level model for exercising the firmware; it proves nothing about the power stage.
#pragma once
#include <cmath>
#include <cstdint>
#include <vector>
#include "weld_core.h"
#include "pulse_sequencer.h"

struct Interval { double t_on_us, t_off_us; };

struct SimPlant {
    // ---- parameters ----
    double ocv = 12.7, rint = 0.032, rext = 0.01125, rfet = 0.0059;
    double relay_operate_ms = 15, relay_release_ms = 8;
    double pl_tau_ms = 68.0, pl_dis_tau_ms = 4.7, pl_vth_frac = 0.6875 * 5.0 / 4.9;
    // ---- fault injection ----
    bool fet_shorted = false, relay_welded = false, limiter_broken = false, uvlo_broken = false;
    bool gate_fb_stuck_high = false, ntc_open = false, seq_hang = false;
    // ---- operator / environment ----
    bool foot = false, ack = false, arm = false, touching = false;
    double t_hs_c = 25.0;
    bool battery_connected = true;
    // ---- state ----
    double t_ms = 0;
    bool relay_cmd = false, relay_closed = false;
    double relay_t_change = -1e9;
    bool gate_test = false, gate_pin = false;
    double vct = 0;                       // limiter capacitor voltage fraction (0..1 of VOH)
    PulseSequencer seq;
    double seq_next_us = 0;               // absolute time of next sequencer event
    std::vector<Interval> on_intervals;   // effective MOSFET-ON intervals with the relay closed
    bool eff_prev = false;
    double eff_t_on = 0;
    double max_current = 0;

    double vdrv() const { return arm ? 11.5 : 0.0; }
    bool uvlo_ok() const { return uvlo_broken || vdrv() >= 8.0; }
    bool limiter_ok() const { return limiter_broken || vct < pl_vth_frac; }
    bool gate_fb() const { return gate_fb_stuck_high || (gate_pin && uvlo_ok() && limiter_ok()); }
    bool fet_on() const { return fet_shorted || (gate_fb() && vdrv() >= 4.0); }
    double current() const {
        if (!battery_connected || !relay_closed || !touching || !fet_on()) return 0.0;
        return ocv / (rint + rext);
    }
    double vbat() const { return battery_connected ? ocv - current() * rint : 0.0; }

    Inputs inputs() const {
        Inputs in{};
        in.now_ms = (uint32_t)t_ms;
        double vb = vbat();
        in.vbat_mv = (uint16_t)(vb * 1000);
        double vel = (relay_closed && battery_connected) ? vb : 0.0;
        in.velec_mv = (uint16_t)(vel * 1000);
        double vd = 0;
        if (touching && relay_closed) vd = fet_on() ? current() * rfet : vel;
        in.vdrain_mv = (uint16_t)(vd * 1000);
        in.vdrv_mv = (uint16_t)(vdrv() * 1000);
        in.vhold_mv = battery_connected ? 11200 : 0;
        in.t_hs_dc = ntc_open ? 2000 : (int16_t)lround(t_hs_c * 10);
        in.foot = foot;
        in.ack = ack;
        in.arm_a = arm;
        in.gate_cmd = gate_pin;
        in.gate_fb = gate_fb();
        in.seq_active = seq.active();
        in.activity = false;
        return in;
    }

    // apply firmware outputs (mirrors hal_avr.cpp apply())
    void apply(const Outputs &o) {
        if (o.abort_pulse) { seq.abort(); gate_pin = false; }
        if (o.start_pulse && o.relay) {
            bool g; uint32_t next;
            if (seq.start(o.plan, &g, &next)) { gate_pin = g; seq_next_us = t_ms * 1000.0 + next; }
        }
        if (!seq.active()) gate_pin = (o.gate_test && !o.relay);
        if (o.relay != relay_cmd) { relay_cmd = o.relay; relay_t_change = t_ms; }
    }

    // advance 1 ms with 10 us internal resolution
    void tick_1ms() {
        for (int i = 0; i < 100; i++) {
            double t_us = t_ms * 1000.0 + i * 10.0;
            if (seq.active() && !seq_hang && t_us >= seq_next_us) {
                bool g; uint32_t next;
                bool more = seq.on_timer(&g, &next);
                gate_pin = g;
                if (more) seq_next_us += next;
            }
            // limiter capacitor
            double dt = 0.01;
            if (gate_pin) vct += (1.0 - vct) * dt / pl_tau_ms;
            else vct -= vct * dt / pl_dis_tau_ms;
            bool eff = fet_on() && relay_closed;      // current-capable ON interval
            if (eff && !eff_prev) eff_t_on = t_us;
            if (!eff && eff_prev) on_intervals.push_back({eff_t_on, t_us});
            eff_prev = eff;
            if (current() > max_current) max_current = current();
        }
        t_ms += 1.0;
        double d = t_ms - relay_t_change;
        if (relay_welded) relay_closed = true;
        else if (relay_cmd && d >= relay_operate_ms) relay_closed = true;
        else if (!relay_cmd && d >= relay_release_ms) relay_closed = false;
    }
};
