// SPDX-License-Identifier: GPL-3.0-or-later
// DIY_SPOT_WELDER_V1 - HAL for Arduino Nano (ATmega328P @ 16 MHz, Optiboot bootloader)
#ifdef ARDUINO
#include <Arduino.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <EEPROM.h>
#include <math.h>
#include "hal.h"
#include "config.h"

// ---------------------------------------------------------------------------------------------
// Reset cause. Optiboot passes MCUSR in r2 and clears MCUSR; read r2 before the C runtime runs.
// The watchdog must be disabled early: after a WDT reset it stays enabled at 15 ms.
// ---------------------------------------------------------------------------------------------
uint8_t g_r2_flags __attribute__((section(".noinit")));
uint8_t g_mcusr __attribute__((section(".noinit")));
void hal_init0(void) __attribute__((naked, used, section(".init0")));
void hal_init0(void) { __asm__ __volatile__("sts %0, r2\n" : "=m"(g_r2_flags) :); }
void hal_init3(void) __attribute__((naked, used, section(".init3")));
void hal_init3(void) {
    g_mcusr = MCUSR;
    MCUSR = 0;
    wdt_disable();
    // Gate command LOW and output before anything else (R45 already holds it low).
    PORTB &= ~_BV(PB1);
    DDRB |= _BV(DDB1);
}

#define GATE_ON()  (PORTB |= _BV(PB1))
#define GATE_OFF() (PORTB &= ~_BV(PB1))
#define GATE_IS_ON() ((PORTB & _BV(PB1)) != 0)

static PulseSequencer seq;
static volatile int8_t enc_count = 0;
static uint8_t s_reset = 0;

// ---------------------------------------------------------------------------------------------
// Timer1: CTC, prescaler 64 -> 4 us per tick, max interval 262 ms. Gate edges are set in the
// compare ISR (latency ~2-5 us; no other ISR runs long in this firmware).
// ---------------------------------------------------------------------------------------------
static inline uint16_t us_to_ticks(uint32_t us) {
    uint32_t t = us / 4UL;
    if (t < 2) t = 2;
    if (t > 65535UL) t = 65535UL;
    return (uint16_t)(t - 1);
}

ISR(TIMER1_COMPA_vect) {
    bool gate;
    uint32_t next;
    bool more = seq.on_timer(&gate, &next);
    if (gate) GATE_ON(); else GATE_OFF();
    if (more) {
        OCR1A = us_to_ticks(next);
    } else {
        TIMSK1 &= ~_BV(OCIE1A);
        TCCR1B = 0;
    }
}

static bool pulse_start(const PulsePlan &p) {
    bool gate;
    uint32_t first;
    uint8_t sreg = SREG;
    cli();
    bool ok = seq.start(p, &gate, &first);
    if (ok) {
        TCCR1A = 0;
        TCCR1B = 0;
        TCNT1 = 0;
        OCR1A = us_to_ticks(first);
        TIFR1 = _BV(OCF1A);
        TIMSK1 |= _BV(OCIE1A);
        GATE_ON();
        TCCR1B = _BV(WGM12) | _BV(CS11) | _BV(CS10);
    } else {
        GATE_OFF();
    }
    SREG = sreg;
    return ok;
}

static void pulse_abort() {
    uint8_t sreg = SREG;
    cli();
    GATE_OFF();
    TIMSK1 &= ~_BV(OCIE1A);
    TCCR1B = 0;
    seq.abort();
    SREG = sreg;
}

// ---------------------------------------------------------------------------------------------
// Encoder (signals inverted and filtered by 74HCT14 + RC). INT0 on A, direction from B.
// ---------------------------------------------------------------------------------------------
static void enc_isr() {
    static uint32_t last = 0;
    uint32_t t = micros();
    if (t - last < 2000) return;
    last = t;
    enc_count += digitalRead(PIN_ENC_B) ? -1 : 1;
}

// ---------------------------------------------------------------------------------------------
// Buzzer (active buzzer, non-blocking pattern)
// ---------------------------------------------------------------------------------------------
static uint8_t buz_pattern = 0, buz_step = 0;
static uint32_t buz_t = 0;
static const uint16_t PAT_SHORT[] = {60, 0};
static const uint16_t PAT_WELD[] = {30, 0};
static const uint16_t PAT_READY[] = {80, 80, 80, 0};
static const uint16_t PAT_FAULT[] = {400, 200, 400, 200, 400, 0};

static const uint16_t *pattern(uint8_t p) {
    switch (p) {
    case BEEP_SHORT: return PAT_SHORT;
    case BEEP_WELD: return PAT_WELD;
    case BEEP_READY: return PAT_READY;
    case BEEP_FAULT: return PAT_FAULT;
    default: return 0;
    }
}

static void buzzer_task(uint32_t now) {
    const uint16_t *p = pattern(buz_pattern);
    if (!p) { digitalWrite(PIN_BUZZER, LOW); return; }
    if (p[buz_step] == 0) { buz_pattern = 0; digitalWrite(PIN_BUZZER, LOW); return; }
    digitalWrite(PIN_BUZZER, (buz_step & 1) ? LOW : HIGH);
    if (now - buz_t >= p[buz_step]) { buz_step++; buz_t = now; }
}

// ---------------------------------------------------------------------------------------------
// Analog
// ---------------------------------------------------------------------------------------------
static uint16_t adc_mv(uint8_t pin) {
    uint32_t a = analogRead(pin);
    return (uint16_t)(a * (uint32_t)ADC_VREF_MV * ADC_DIVIDER_NUM / (ADC_DIVIDER_DEN * 1024UL));
}

static int16_t ntc_dc() {
    // NTC 10k (B 3950, UNVERIFIED part) to GND via 1k series, 10k pull-up to the ADC reference.
    int a = analogRead(PIN_ADC_NTC);
    if (a <= 5) return -1000;          // short -> invalid
    if (a >= 1018) return 2000;        // open  -> invalid
    float r = 10000.0f * a / (1023.0f - a) - 1000.0f;   // minus series resistor
    if (r < 10.0f) return 2000;
    float t = 1.0f / (1.0f / 298.15f + logf(r / 10000.0f) / 3950.0f) - 273.15f;
    return (int16_t)lroundf(t * 10.0f);
}

namespace hal {

void init() {
    // 1) safe outputs first
    pinMode(PIN_GATE_CMD, OUTPUT); digitalWrite(PIN_GATE_CMD, LOW);
    pinMode(PIN_RELAY_EN, OUTPUT); digitalWrite(PIN_RELAY_EN, LOW);
    pinMode(PIN_BUZZER, OUTPUT);   digitalWrite(PIN_BUZZER, LOW);
    pinMode(PIN_LED_FAULT, OUTPUT); digitalWrite(PIN_LED_FAULT, HIGH);   // lamp test
    pinMode(PIN_LED_READY, OUTPUT); digitalWrite(PIN_LED_READY, HIGH);
    // 2) inputs (external pull-ups / Schmitt triggers on the board)
    pinMode(PIN_ENC_A, INPUT); pinMode(PIN_ENC_B, INPUT); pinMode(PIN_ENC_SW, INPUT);
    pinMode(PIN_FOOT, INPUT); pinMode(PIN_ACK, INPUT); pinMode(PIN_GATE_FB, INPUT); pinMode(PIN_ARM_A_N, INPUT);
    analogReference(DEFAULT);
    s_reset = 0;
    uint8_t f = g_mcusr ? g_mcusr : g_r2_flags;
    if (f & _BV(WDRF)) s_reset |= RST_WDT;
    if (f & _BV(BORF)) s_reset |= RST_BOR;
    if (f & _BV(EXTRF)) s_reset |= RST_EXT;
    if (f & _BV(PORF)) s_reset |= RST_POR;
    attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), enc_isr, RISING);
    wdt_enable(WDTO_1S);      // generous during display start-up, tightened in wdt_kick()
}

uint8_t reset_flags() { return s_reset; }
uint32_t now_ms() { return millis(); }

void read_inputs(Inputs &in) {
    in.vbat_mv = adc_mv(PIN_ADC_VBAT);
    in.vdrain_mv = adc_mv(PIN_ADC_VDRAIN);
    in.velec_mv = adc_mv(PIN_ADC_VELEC);
    in.vdrv_mv = adc_mv(PIN_ADC_VDRV);
    in.vhold_mv = adc_mv(PIN_ADC_VHOLD);
    in.t_hs_dc = ntc_dc();
    in.foot = digitalRead(PIN_FOOT);
    in.ack = digitalRead(PIN_ACK);
    in.arm_a = !digitalRead(PIN_ARM_A_N);
    in.gate_cmd = GATE_IS_ON();
    in.gate_fb = digitalRead(PIN_GATE_FB);
}

void apply(const Outputs &o) {
    if (o.abort_pulse) pulse_abort();
    if (o.start_pulse && o.relay) pulse_start(o.plan);
    if (!seq.active()) {
        if (o.gate_test && !o.relay) GATE_ON();    // self-tests only with the relay commanded open
        else GATE_OFF();
    }
    digitalWrite(PIN_RELAY_EN, o.relay ? HIGH : LOW);
    digitalWrite(PIN_LED_FAULT, o.led_fault ? HIGH : LOW);
    digitalWrite(PIN_LED_READY, o.led_ready ? HIGH : LOW);
    uint32_t now = millis();
    if (o.beep) { buz_pattern = o.beep; buz_step = 0; buz_t = now; }
    buzzer_task(now);
}

bool pulse_active() { return seq.active(); }

void wdt_kick() {
    static bool tight = false;
    if (!tight) { wdt_enable(WDT_TIMEOUT_CODE); tight = true; }
    wdt_reset();
}

int8_t encoder_take() {
    uint8_t sreg = SREG; cli();
    int8_t c = enc_count; enc_count = 0;
    SREG = sreg;
    return c;
}

bool encoder_button() { return digitalRead(PIN_ENC_SW); }

// ---------------------------------------------------------------------------------------------
// EEPROM: [0..3] magic, [4] layout version, [8..] Settings, then CRC8; [40..43] weld count;
// [63] log head; [64..143] fault log 16 x {code, welds(4)}
// ---------------------------------------------------------------------------------------------
static const uint32_t EE_MAGIC = 0x31575344UL;   // "DSW1"
static const uint8_t EE_VER = 1;

static uint8_t crc8(const uint8_t *d, uint8_t n) {
    uint8_t c = 0;
    while (n--) { c ^= *d++; for (uint8_t i = 0; i < 8; i++) c = (c & 0x80) ? (uint8_t)((c << 1) ^ 0x07) : (uint8_t)(c << 1); }
    return c;
}

bool load(Settings &s, uint32_t &welds) {
    uint32_t magic; EEPROM.get(0, magic);
    uint8_t ver = EEPROM.read(4);
    EEPROM.get(8, s);
    uint8_t crc = EEPROM.read(8 + sizeof(Settings));
    EEPROM.get(40, welds);
    bool ok = magic == EE_MAGIC && ver == EE_VER && crc == crc8((const uint8_t *)&s, sizeof(Settings));
    if (!ok) { settings_default(s); welds = 0; return false; }
    settings_sanitize(s);
    return true;
}

void save(const Settings &s, uint32_t welds) {
    EEPROM.put(0, EE_MAGIC);
    EEPROM.update(4, EE_VER);
    EEPROM.put(8, s);
    EEPROM.update(8 + sizeof(Settings), crc8((const uint8_t *)&s, sizeof(Settings)));
    EEPROM.put(40, welds);
}

void log_fault(uint8_t code, uint32_t welds) {
    uint8_t head = (EEPROM.read(63) + 1) & 15;
    EEPROM.update(64 + head * 5, code);
    EEPROM.put(65 + head * 5, welds);
    EEPROM.update(63, head);
}

bool read_log(uint8_t idx, uint8_t &code, uint32_t &welds) {
    uint8_t head = EEPROM.read(63) & 15;
    uint8_t i = (head - idx) & 15;
    code = EEPROM.read(64 + i * 5);
    EEPROM.get(65 + i * 5, welds);
    return code != 0 && code != 0xFF;
}

}  // namespace hal
#endif  // ARDUINO
