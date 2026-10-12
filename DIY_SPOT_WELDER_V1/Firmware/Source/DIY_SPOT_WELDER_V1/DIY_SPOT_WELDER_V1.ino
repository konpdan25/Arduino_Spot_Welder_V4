// SPDX-License-Identifier: GPL-3.0-or-later
/*
 * DIY_SPOT_WELDER_V1 firmware (PRELIMINARY - NOT VALIDATED ON HARDWARE)
 *
 * Target: Arduino Nano V3 (ATmega328P 16 MHz) with the Optiboot ("new") bootloader.
 * Libraries: Adafruit SSD1306 (>= 2.5.7), Adafruit GFX (>= 1.11.5), Adafruit BusIO, Wire, EEPROM.
 *
 * Structure
 *   weld_core.*        weld-enable state machine, supervision, latched faults (host-testable)
 *   pulse_sequencer.*  pulse plan limits and step sequencer (host-testable)
 *   hal_avr.cpp        pins, Timer1 pulse ISR, ADC, watchdog, EEPROM, buzzer, encoder
 *   ui.*               OLED + encoder menu
 *
 * The weld output defaults to OFF during reset, boot, programming and on every fault. Hardware
 * protections (pull-down, RC pulse limiter, UVLO, E-STOP/ARM chain, fuse) do not depend on this code.
 *
 * Copyright (C) 2026 DIY_SPOT_WELDER_V1 contributors. Licensed under the GNU GPL v3.0 or later.
 * Inspired by the Arduino Spot Welder V4 (C) Marc Schoenfleisch / Malectrics, GPL-3.0.
 */
#include "config.h"
#include "hal.h"
#include "weld_core.h"
#include "ui.h"

static WeldCore core;
static Settings settings;
static uint32_t saved_welds = 0;

void setup() {
    hal::init();                                   // gate LOW + relay OFF first
    uint32_t welds = 0;
    hal::load(settings, welds);
    core.set_weld_count(welds);
    saved_welds = welds;
    ui_init();
    core.begin(settings, hal::reset_flags(), hal::now_ms());
}

void loop() {
    hal::wdt_kick();
    Inputs in;
    hal::read_inputs(in);
    in.now_ms = hal::now_ms();
    in.seq_active = hal::pulse_active();
    in.activity = hal::encoder_button();
    Outputs out;
    core.step(in, out);
    hal::apply(out);
    if (out.new_fault != F_NONE) hal::log_fault(out.new_fault, core.weld_count());
    if (out.weld_done && core.weld_count() - saved_welds >= 10) {   // limit EEPROM wear
        saved_welds = core.weld_count();
        hal::save(core.settings(), saved_welds);
    }
    if (ui_task(core, in, in.now_ms)) {
        saved_welds = core.weld_count();
        hal::save(core.settings(), saved_welds);
    }
}
