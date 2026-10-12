// SPDX-License-Identifier: GPL-3.0-or-later
#ifdef ARDUINO
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "ui.h"
#include "hal.h"
#include "config.h"
#include "pgm_compat.h"
#define FS(p) ((const __FlashStringHelper *)(p))

static Adafruit_SSD1306 oled(128, 64, &Wire, -1);
static bool oled_ok = false;

enum Item : uint8_t { IT_MAIN, IT_PRE, IT_GAP, IT_TRIG, IT_MODE, IT_AUTO, IT_SOUND, IT_LOG, IT_EXIT, IT_COUNT };
static const char IN0[] PROGMEM = "Main pulse";
static const char IN1[] PROGMEM = "Pre-pulse";
static const char IN2[] PROGMEM = "Gap";
static const char IN3[] PROGMEM = "Trig delay";
static const char IN4[] PROGMEM = "Mode";
static const char IN5[] PROGMEM = "Auto delay";
static const char IN6[] PROGMEM = "Sound";
static const char IN7[] PROGMEM = "Fault log";
static const char IN8[] PROGMEM = "Save + exit";
static const char *const ITEM_NAME[IT_COUNT] PROGMEM = {IN0, IN1, IN2, IN3, IN4, IN5, IN6, IN7, IN8};
static bool in_menu = false, editing = false;
static uint8_t sel = 0, log_idx = 0;
static bool btn_prev = false;
static uint32_t last_draw = 0;

void ui_init() {
    oled_ok = oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
    Wire.setClock(400000);
    // The OLED and MCP9804 are 3.3 V parts with external 4.7k pull-ups to 3.3 V:
    // disable the ATmega internal pull-ups (to 5 V) that Wire.begin() enabled.
    digitalWrite(SDA, LOW);
    digitalWrite(SCL, LOW);
    if (!oled_ok) return;
    oled.clearDisplay();
    oled.setTextColor(SSD1306_WHITE);
    oled.setTextSize(1);
    oled.setCursor(0, 0);
    oled.println(F(FW_NAME));
    oled.println(F("fw " FW_VERSION));
    oled.println();
    oled.println(F("PRELIMINARY FIRMWARE"));
    oled.println(F("not validated"));
    oled.display();
}

static void edit(Settings &s, uint8_t item, int8_t d) {
    switch (item) {
    case IT_MAIN: s.main_ms = (uint16_t)(s.main_ms + d); break;
    case IT_PRE: s.pre_pct = (uint8_t)(s.pre_pct + d); break;
    case IT_GAP: s.gap_ms = (uint16_t)(s.gap_ms + d); break;
    case IT_TRIG: s.trigger_delay_ms = (uint16_t)(s.trigger_delay_ms + 50 * d); break;
    case IT_MODE: s.mode = s.mode == MODE_FOOT ? MODE_AUTO : MODE_FOOT; break;
    case IT_AUTO: s.auto_delay_ms = (uint16_t)(s.auto_delay_ms + 100 * d); break;
    case IT_SOUND: s.sound = !s.sound; break;
    case IT_LOG: log_idx = (uint8_t)((log_idx + d) & 15); break;
    }
    if ((int16_t)s.main_ms < 0) s.main_ms = 0;          // wrap-around guards before sanitize
    if (s.pre_pct > 200) s.pre_pct = 0;
    settings_sanitize(s);
}

static void value_str(const Settings &s, uint8_t item, char *b) {
    switch (item) {
    case IT_MAIN: sprintf_P(b, PSTR("%u ms"), s.main_ms); break;
    case IT_PRE: sprintf_P(b, PSTR("%u %%"), s.pre_pct); break;
    case IT_GAP: sprintf_P(b, PSTR("%u ms"), s.gap_ms); break;
    case IT_TRIG: sprintf_P(b, PSTR("%u ms"), s.trigger_delay_ms); break;
    case IT_MODE: strcpy_P(b, s.mode == MODE_AUTO ? PSTR("AUTO") : PSTR("FOOT")); break;
    case IT_AUTO: sprintf_P(b, PSTR("%u ms"), s.auto_delay_ms); break;
    case IT_SOUND: strcpy_P(b, s.sound ? PSTR("ON") : PSTR("OFF")); break;
    case IT_LOG: {
        uint8_t c; uint32_t w;
        if (hal::read_log(log_idx, c, w)) sprintf_P(b, PSTR("#%u %S"), log_idx, WeldCore::fault_name(c));
        else sprintf_P(b, PSTR("#%u -"), log_idx);
        break;
    }
    default: b[0] = 0;
    }
}

static void draw_main(WeldCore &core, const Inputs &in) {
    char b[24];
    const Settings &s = core.settings();
    oled.clearDisplay();
    oled.setTextSize(1);
    oled.setCursor(0, 0);
    if (core.state() == State::FAULT) {
        oled.print(F("FAULT: "));
        oled.println(FS(WeldCore::fault_name(core.fault())));
        oled.println(core.fault_clearable() ? F("fix cause, press ACK") : F("POWER OFF + INSPECT"));
    } else {
        oled.print(FS(WeldCore::state_name(core.state())));
        oled.print(s.mode == MODE_AUTO ? F("  AUTO") : F("  FOOT"));
        sprintf_P(b, PSTR("  W%lu"), (unsigned long)core.weld_count());
        oled.println(b);
    }
    oled.setTextSize(3);
    oled.setCursor(0, 18);
    sprintf_P(b, PSTR("%2u"), s.main_ms);
    oled.print(b);
    oled.setTextSize(1);
    oled.print(F("ms"));
    sprintf_P(b, PSTR(" pre%u%%"), s.pre_pct);
    oled.setCursor(66, 18); oled.print(b);
    sprintf_P(b, PSTR(" max%lums"), (unsigned long)(core.allowed_main_us() / 1000UL));
    oled.setCursor(66, 30); oled.print(b);
    oled.setCursor(0, 46);
    sprintf_P(b, PSTR("VB%2u.%uV T%3d.%uC"), in.vbat_mv / 1000, (in.vbat_mv % 1000) / 100, in.t_hs_dc / 10, abs(in.t_hs_dc % 10));
    oled.println(b);
    const WeldRecord &r = core.last();
    if (core.weld_count()) {
        sprintf_P(b, PSTR("last %u.%uV ~%uA EST"), r.vbat_min_mv / 1000, (r.vbat_min_mv % 1000) / 100, r.i_est_a);
        oled.print(b);
    }
    oled.display();
}

static void draw_menu(WeldCore &core) {
    char b[24];
    oled.clearDisplay();
    oled.setTextSize(1);
    uint8_t first = sel > 4 ? sel - 4 : 0;
    for (uint8_t i = 0; i < 5 && first + i < IT_COUNT; i++) {
        uint8_t it = first + i;
        oled.setCursor(0, i * 12);
        oled.print(it == sel ? (editing ? '*' : '>') : ' ');
        oled.print(FS(pgm_read_ptr(&ITEM_NAME[it])));
        value_str(core.settings(), it, b);
        oled.setCursor(72, i * 12);
        oled.print(b);
    }
    oled.display();
}

bool ui_task(WeldCore &core, const Inputs &in, uint32_t now) {
    bool save = false;
    if (core.timing_critical()) return false;          // never block during tests / trigger / pulse
    int8_t d = hal::encoder_take();
    bool btn = hal::encoder_button();
    bool click = btn && !btn_prev;
    btn_prev = btn;
    bool can_edit = core.state() == State::DISARMED || core.state() == State::READY || core.state() == State::FAULT;
    if (!in_menu) {
        if (d && can_edit) { Settings s = core.settings(); edit(s, IT_MAIN, d); core.set_settings(s); }
        if (click && can_edit) { in_menu = true; sel = 0; editing = false; }
    } else {
        if (!can_edit) { in_menu = false; editing = false; }
        else if (editing) {
            if (d) { Settings s = core.settings(); edit(s, sel, d); core.set_settings(s); }
            if (click) editing = false;
        } else {
            if (d) sel = (uint8_t)((sel + IT_COUNT + d) % IT_COUNT);
            if (click) {
                if (sel == IT_EXIT) { in_menu = false; save = true; }
                else editing = true;
            }
        }
    }
    if (oled_ok && now - last_draw >= 150) {
        last_draw = now;
        if (in_menu) draw_menu(core); else draw_main(core, in);
    }
    return save;
}
#endif  // ARDUINO
