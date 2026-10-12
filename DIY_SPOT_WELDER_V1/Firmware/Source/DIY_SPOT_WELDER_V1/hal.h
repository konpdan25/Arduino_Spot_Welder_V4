// SPDX-License-Identifier: GPL-3.0-or-later
// DIY_SPOT_WELDER_V1 - hardware abstraction layer.
// hal_avr.cpp implements it for the Arduino Nano; Firmware/Tests/sim_hal.* implements it on the
// host so the weld logic can be exercised without the welding stage.
#pragma once
#include <stdint.h>
#include "weld_core.h"

namespace hal {

void     init();                      // pins safe (gate LOW, relay OFF) FIRST, then peripherals
uint8_t  reset_flags();               // ResetFlags bitmask captured at start-up
uint32_t now_ms();
void     read_inputs(Inputs &in);     // fills everything except seq_active/now/activity
void     apply(const Outputs &out);   // relay, LEDs, buzzer, gate test, pulse start/abort
bool     pulse_active();
void     wdt_kick();

int8_t   encoder_take();              // detents since last call (+ = clockwise)
bool     encoder_button();            // debounced level

bool     load(Settings &s, uint32_t &welds);
void     save(const Settings &s, uint32_t welds);
void     log_fault(uint8_t code, uint32_t welds);
bool     read_log(uint8_t idx, uint8_t &code, uint32_t &welds);   // idx 0 = newest

}  // namespace hal
