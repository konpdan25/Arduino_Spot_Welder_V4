# Datasheet Index and Verification Status

**How data were obtained.** The cloud environment's network policy blocked direct downloads from manufacturer sites
(Microchip, TI, ST, Infineon, Vishay, Littelfuse, Midas, DFRobot) during this work. Values therefore come from:

* **LIB** — the pinout of the official KiCad 7 symbol/footprint library (curated against datasheets by the KiCad library team), cross-checked against the well-known standard pinout of the part;
* **WEB** — web search snippets of the manufacturer datasheet or distributor listing (secondary source);
* **REF** — the reference design files;
* **MEM** — engineering knowledge of the datasheet, not re-read in this session.

Every item marked WEB or MEM must be re-checked against the PDF listed below before ordering or building.
PDFs are not stored in this repository (copyright); download them to this folder locally if wanted.

| Part | Use | Key data used | Source / confidence | Datasheet URL |
|---|---|---|---|---|
| Ritar RT1270 | welding source (not approved) | 12 V 7 Ah; Rint ≤ 32 mΩ (full, 25 °C); max discharge 70 A (5 s); F1/F2 FASTON | WEB (third-party copy fixer.com.ua; distributor: 30 mΩ, "350 A short circuit") — **LOW** | manufacturer site ritarpower.com (not reachable) |
| IRLZ44N (Infineon/IR) | weld switch ×6 | 55 V; RDS(on) 22 mΩ @10 V; IDM 160 A; EAS 210 mJ; RthJC 1.8 K/W (TO-220); G-D-S | WEB + LIB — MEDIUM | https://www.infineon.com/dgdl/irlz44npbf.pdf |
| IXFH20N50P3 | rejected | 500 V 20 A, RDS(on) ≈ 0.3 Ω | MEM | IXYS/Littelfuse |
| STP6NK60 | rejected | 600 V 6 A, RDS(on) ≈ 1 Ω | MEM | ST |
| TC4422 (CPA) | gate driver | 9 A, VDD 4.5–18 V, TTL/CMOS input, 300 mV hysteresis; PDIP: 1,8 VDD / 2 IN / 3 NC / 4,5 GND / 6,7 OUT | WEB + LIB — HIGH (pinout) | https://ww1.microchip.com/downloads/en/DeviceDoc/20001420F.pdf |
| TC4421 | rejected (inverting) | same family | WEB | same |
| LM393 | limiter + UVLO | 2–36 V, open collector, Vos ≤ 5 mV; DIP-8 standard pinout | LIB + MEM — HIGH (pinout) | https://www.ti.com/lit/ds/symlink/lm393.pdf |
| 74HCT14 | Schmitt inputs | VCC 4.5–5.5 V, standard 14-pin pinout | LIB — HIGH | https://assets.nexperia.com/documents/data-sheet/74HC_HCT14.pdf |
| L7805 / 7805 | +5V_AUX | TO-220 IN-GND-OUT, dropout ≈ 2 V | LIB + MEM — HIGH (stock part maker unknown) | https://www.st.com/resource/en/datasheet/l78.pdf |
| MCP1700-3302E/TO | +3V3 (purchase) | TO-92: 1 GND, 2 VIN, 3 VOUT; Vin ≤ 6 V; 1 µF caps | LIB + MEM — HIGH | https://ww1.microchip.com/downloads/en/DeviceDoc/20001826D.pdf |
| MCP9804 | board temperature | MSOP-8: SDA, SCL, ALERT, GND, A2, A1, A0, VDD; 2.7–5.5 V; addr 0x18 | LIB — HIGH (pinout); stock package UNKNOWN | https://ww1.microchip.com/downloads/en/DeviceDoc/22203C.pdf |
| MDOB128064WV-YBI (Midas) | OLED | SSD1306, I²C; pins 1 VCC, 2 GND, 3 SCL, 4 SDA; VCC 2.8–5.2 V (pin table) vs 3.3 V typ (electrical table) | WEB — MEDIUM (spec sheet internally inconsistent) | https://midasdisplays.com/wp-content/uploads/2024/12/MDOB128064WV-YBI.pdf |
| DFRobot DFR0868 | not used | **Beetle ESP32-C3** dev board (not a timer); GPIO 0–10, 20, 21; LED GPIO10; BOOT GPIO9; I²C default GPIO8/9 | WEB + Zephyr board files — MEDIUM | https://wiki.dfrobot.com/SKU_DFR0868_Beetle_ESP32_C3 |
| STPS3045CP | free-wheel diode | 45 V, 2×15 A, IFSM 220 A (10 ms), common cathode SOT-93 (A-K-A) | WEB (family datasheet) — MEDIUM; may be obsolete | https://www.st.com/resource/en/datasheet/stps3045c.pdf |
| SMBJ24CA(-H) | bus TVS | 24 V standoff, VBR 26.7 V min, VC 38.9 V, 600 W | MEM — MEDIUM | Littelfuse SMBJ series |
| SMBJ15A | input TVS (purchase) | 15 V standoff, VC 24.4 V | MEM — MEDIUM | Littelfuse SMBJ series |
| BZY97C15 | clamps | 15 V 1.5 W zener | MEM — MEDIUM; value in stock UNKNOWN | https://www.vishay.com/docs/85614/bzy97.pdf |
| 1N4148 | small signal | 100 V, IFRM 450 mA | MEM — HIGH | https://www.vishay.com/docs/81857/1n4148.pdf |
| 1N5822 | hold-up isolation (purchase) | 40 V 3 A Schottky | MEM — HIGH | https://www.vishay.com/docs/88526/1n5820.pdf |
| BC337 / BC547 | relay / buzzer driver | TO-92 C-B-E; 45 V; 800 mA / 100 mA | LIB + MEM — HIGH | onsemi bc337-d.pdf / bc546-d.pdf |
| 2N2222 | not used | TO-92 **E-B-C** (differs from BC337!) | MEM | — |
| PC817 | not used | DIP-4 optocoupler | MEM | — |
| DRV8872 / DRV8870 / DRV8816 / DRV8833 | not used | H-bridges (DRV8833 max 10.8 V) | MEM | ti.com |
| Arduino Nano V3 | MCU | pin numbering per KiCad `MCU_Module:Arduino_Nano_v3.x` / `Module:Arduino_Nano` | LIB — HIGH | https://docs.arduino.cc/hardware/nano |
| Relay K101 | isolation | **UNKNOWN part** — 12 V, ≈300 mA, "≈100 A" marking | — | identify from the relay label |
| IRFS7430 (reference V4) | reference only | 40 V, ≈0.75 mΩ, D²PAK-7 | REF + MEM | — |
| MCP1407 (reference V4) | reference only | 6 A non-inverting, SOIC-8 pinout as TC4422 family | REF | — |
