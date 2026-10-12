// SPDX-License-Identifier: GPL-3.0-or-later
// DIY_SPOT_WELDER_V1 firmware - configuration (pins, limits, thresholds)
//
// Concepts (double pulse, contact-triggered pulse) follow the Arduino Spot Welder V4 by
// Marc Schoenfleisch / Malectrics (GPL-3.0). This file is new code.
#pragma once
#include <stdint.h>

#define FW_NAME     "DIY_SPOT_WELDER_V1"
#define FW_VERSION  "0.1.0-prelim"

// ---------------------------------------------------------------------------
// Pin map (Arduino Nano, see KiCad sheet 03). All inputs from 74HCT14 are ACTIVE HIGH
// except ARM_A_N (low = relay pole of the ARM chain closed).
// ---------------------------------------------------------------------------
#define PIN_ENC_A        2   // INT0
#define PIN_ENC_B        3   // INT1
#define PIN_ENC_SW       4
#define PIN_FOOT         5
#define PIN_ACK          6
#define PIN_RELAY_EN     7
#define PIN_BUZZER       8
#define PIN_GATE_CMD     9   // PB1 / OC1A - weld pulse command (hardware pull-down R45)
#define PIN_LED_FAULT    10
#define PIN_GATE_FB      11  // effective TC4422 input (after wired-AND limiter/UVLO)
#define PIN_ARM_A_N      12
#define PIN_LED_READY    13
#define PIN_ADC_VBAT     A0
#define PIN_ADC_VDRAIN   A1
#define PIN_ADC_VELEC    A2
#define PIN_ADC_VDRV     A3
#define PIN_ADC_NTC      A6
#define PIN_ADC_VHOLD    A7

// ---------------------------------------------------------------------------
// Analog scaling: 33k/10k dividers -> k = 4.3, ADC ref = AVCC (Nano 5 V)
// ---------------------------------------------------------------------------
#define ADC_DIVIDER_NUM   43     // k = 43/10
#define ADC_DIVIDER_DEN   10
#define ADC_VREF_MV       5000   // calibrate per board (cal factor in settings)

// ---------------------------------------------------------------------------
// Pulse limits. HARD limits are compile-time and cannot be exceeded from the menu.
// Hardware limiter window: 63..96 ms per ON interval (doc 03 section 8).
// MOSFET thermal limit: ~53 ms at ~300 A, Tcase 50 C (doc 03 section 4).
// ---------------------------------------------------------------------------
#define HARD_MAX_MAIN_US      50000UL   // 50 ms
#define HARD_MIN_MAIN_US      1000UL    // 1 ms
#define HARD_MAX_PRE_PCT      30        // pre-pulse <= 30 % of main
#define HARD_MAX_TOTAL_ON_US  65000UL   // pre + main
#define HARD_MIN_GAP_US       2000UL    // gap >= 2 ms (limiter capacitor partly discharges)
#define HARD_MAX_GAP_US       50000UL
#define SEQ_GUARD_MS          20        // extra time before the core declares a sequencer fault

// ---------------------------------------------------------------------------
// Trigger
// ---------------------------------------------------------------------------
#define DEBOUNCE_MS              30
#define MIN_TRIGGER_DELAY_MS     150     // foot switch must be held this long (continuously)
#define MAX_TRIGGER_DELAY_MS     2000
#define MIN_AUTO_DELAY_MS        500     // contact must persist this long in AUTO mode
#define MAX_AUTO_DELAY_MS        5000
#define RETRIGGER_DELAY_MS       500
#define DUTY_FACTOR              20      // minimum interval = 20 x total ON time (5 % duty)

// ---------------------------------------------------------------------------
// Supervision thresholds (millivolts / deci-degC)
// ---------------------------------------------------------------------------
#define VBAT_UV_MV          11500   // below: undervoltage (RT1270 rested 12.6-12.9 V)
#define VBAT_OV_MV          14800   // above: overvoltage (charger connected?) - TC4422 VDD / VGS margin
#define VBAT_PRESENT_MV     5000    // above: P_BUS considered live
#define VDRV_OK_MV          9000    // firmware threshold (hardware UVLO trips at 8.0 V)
#define VHOLD_OK_MV         9500
#define VELEC_CLOSED_FRAC   80      // relay closed if VELEC >= 80 % of VBAT
#define VELEC_OPEN_MV       1500    // relay open if VELEC <= 1.5 V
#define CONTACT_FRAC        50      // AUTO: electrodes on workpiece if VDRAIN >= 50 % VBAT
#define STUCK_SAG_MV        1500    // idle VBAT drop vs. filtered value -> current is flowing
#define T_HS_DERATE_START_DC 400    // 40.0 C start derating
#define T_HS_LIMIT_DC        600    // 60.0 C lockout (latched)
#define T_HS_RESUME_DC       500    // 50.0 C may acknowledge
#define T_HS_MIN_VALID_DC   -300    // NTC open/short detection
#define T_HS_MAX_VALID_DC    1500
#define DERATED_MIN_MAIN_US  20000UL // at T_HS_LIMIT

// ---------------------------------------------------------------------------
// Self-test of the hardware pulse limiter during ARMING (relay OPEN -> no current possible)
// ---------------------------------------------------------------------------
#define LIMTEST_FB_RISE_MS   3       // GATE_FB must follow GATE_CMD within 3 ms
#define LIMTEST_MIN_MS       50      // limiter must not trip earlier (would truncate welds)
#define LIMTEST_MAX_MS       120     // ...and must trip before this
#define LIMTEST_RECOVER_MS   60      // let the timing capacitor discharge
#define RELAY_SETTLE_MS      80      // relay operate + bounce (unknown relay: measure!)

#define WDT_TIMEOUT_CODE     WDTO_250MS
#define STANDBY_MS           300000UL  // 5 min inactivity -> disarm relay
