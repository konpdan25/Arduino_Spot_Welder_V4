// SPDX-License-Identifier: GPL-3.0-or-later
// DIY_SPOT_WELDER_V1 - OLED (SSD1306 128x64, I2C 0x3C) + encoder user interface
#pragma once
#include "weld_core.h"

void ui_init();
// Non-blocking as far as possible; never renders while core.timing_critical().
// Returns true if settings were changed and should be saved.
bool ui_task(WeldCore &core, const Inputs &in, uint32_t now);
