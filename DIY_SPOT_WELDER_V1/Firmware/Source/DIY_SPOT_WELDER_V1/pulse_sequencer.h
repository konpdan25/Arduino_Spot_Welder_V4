// SPDX-License-Identifier: GPL-3.0-or-later
// DIY_SPOT_WELDER_V1 - pulse plan validation and step sequencer (hardware independent)
#pragma once
#include <stdint.h>

struct PulsePlan {
    uint32_t pre_us;    // 0 = single pulse
    uint32_t gap_us;
    uint32_t main_us;
};

// Build a plan from user settings and apply HARD limits + thermal derating.
// main_ms: requested main pulse (ms), pre_pct: pre-pulse % of main, gap_ms: inter-pulse gap (ms)
// max_main_us: current allowed maximum (derated with heatsink temperature)
PulsePlan make_plan(uint16_t main_ms, uint8_t pre_pct, uint16_t gap_ms, uint32_t max_main_us);

// true if the plan respects every compile-time hard limit
bool plan_valid(const PulsePlan &p);

inline uint32_t plan_on_us(const PulsePlan &p) { return p.pre_us + p.main_us; }
inline uint32_t plan_total_us(const PulsePlan &p) { return p.pre_us + (p.pre_us ? p.gap_us : 0) + p.main_us; }

// Step sequencer driven by a one-shot timer (Timer1 compare ISR on the AVR, simulated on the host).
//   start():    returns false (and keeps the gate OFF) if the plan is invalid.
//               On success *gate = true and *next_us = duration of the first ON interval.
//   on_timer(): called when the programmed interval expired. Sets *gate and *next_us.
//               Returns false when the sequence is finished (gate already OFF).
//   abort():    immediately ends the sequence (gate OFF).
class PulseSequencer {
public:
    bool start(const PulsePlan &p, bool *gate, uint32_t *next_us);
    bool on_timer(bool *gate, uint32_t *next_us);
    void abort() { step_ = 0; active_ = false; }
    bool active() const { return active_; }
    uint8_t step() const { return step_; }
private:
    PulsePlan plan_ = {0, 0, 0};
    uint8_t step_ = 0;          // 0 idle, 1 pre ON, 2 gap OFF, 3 main ON
    volatile bool active_ = false;
};
