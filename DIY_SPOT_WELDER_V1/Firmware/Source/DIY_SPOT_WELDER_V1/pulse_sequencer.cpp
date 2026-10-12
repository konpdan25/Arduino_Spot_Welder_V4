// SPDX-License-Identifier: GPL-3.0-or-later
#include "pulse_sequencer.h"
#include "config.h"

static uint32_t clamp_u32(uint32_t v, uint32_t lo, uint32_t hi) { return v < lo ? lo : (v > hi ? hi : v); }

PulsePlan make_plan(uint16_t main_ms, uint8_t pre_pct, uint16_t gap_ms, uint32_t max_main_us) {
    PulsePlan p;
    uint32_t lim = max_main_us < HARD_MAX_MAIN_US ? max_main_us : HARD_MAX_MAIN_US;
    if (lim < HARD_MIN_MAIN_US) lim = HARD_MIN_MAIN_US;
    p.main_us = clamp_u32((uint32_t)main_ms * 1000UL, HARD_MIN_MAIN_US, lim);
    if (pre_pct > HARD_MAX_PRE_PCT) pre_pct = HARD_MAX_PRE_PCT;
    p.pre_us = p.main_us * pre_pct / 100UL;
    if (p.pre_us > 0 && p.pre_us < 500UL) p.pre_us = 0;           // < 0.5 ms pre-pulse is meaningless
    if (p.pre_us + p.main_us > HARD_MAX_TOTAL_ON_US) p.pre_us = HARD_MAX_TOTAL_ON_US - p.main_us;
    p.gap_us = p.pre_us ? clamp_u32((uint32_t)gap_ms * 1000UL, HARD_MIN_GAP_US, HARD_MAX_GAP_US) : 0;
    return p;
}

bool plan_valid(const PulsePlan &p) {
    if (p.main_us < HARD_MIN_MAIN_US || p.main_us > HARD_MAX_MAIN_US) return false;
    if (p.pre_us > p.main_us * HARD_MAX_PRE_PCT / 100UL) return false;
    if (p.pre_us + p.main_us > HARD_MAX_TOTAL_ON_US) return false;
    if (p.pre_us && (p.gap_us < HARD_MIN_GAP_US || p.gap_us > HARD_MAX_GAP_US)) return false;
    return true;
}

bool PulseSequencer::start(const PulsePlan &p, bool *gate, uint32_t *next_us) {
    *gate = false;
    *next_us = 0;
    if (active_ || !plan_valid(p)) return false;
    plan_ = p;
    if (p.pre_us) { step_ = 1; *next_us = p.pre_us; }
    else          { step_ = 3; *next_us = p.main_us; }
    active_ = true;
    *gate = true;
    return true;
}

bool PulseSequencer::on_timer(bool *gate, uint32_t *next_us) {
    *gate = false;
    *next_us = 0;
    if (!active_) return false;
    switch (step_) {
    case 1:  step_ = 2; *next_us = plan_.gap_us; return true;              // gap (gate OFF)
    case 2:  step_ = 3; *gate = true; *next_us = plan_.main_us; return true; // main ON
    default: step_ = 0; active_ = false; return false;                   // finished
    }
}
