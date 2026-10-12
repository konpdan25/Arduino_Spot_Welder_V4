# Open Issues — DIY_SPOT_WELDER_V1

Priority: **B** = blocks any battery-connected high-current test · **H** = high · **M** = medium · **L** = low.

| ID | Pri | Issue | What is needed | Owner / next action |
|---|---|---|---|---|
| OI-01 | B | Welding source: **user decision 2026-10-12: proceed with the RT1270.** Estimate remains 200–390 A (≈ 4× its 70 A / 5 s datasheet maximum), terminal ≈ 3 V during a weld, FASTON tabs unsuitable for 300 A | Before any weld: measure pulse resistance (M1); replace FASTON push-on contacts by bolted/soldered tab adapters and check their temperature rise; start with short pulses (≤ 10 ms) on loose nickel; ventilated area; watch for case swelling/heating. Weld quality on 0.15 mm Ni is not guaranteed (≈ 12× less weld power than a car battery) | User (decided) / measurement M1 open |
| OI-02 | B | K101 relay unknown (type, DC carry/break rating, latching or monostable, drop-out voltage, operate/release times) | Read the label / part number; measure coil resistance; check whether it stays switched without coil power (latching → reject) | User |
| OI-03 | B | Main fuse F101 rating provisional (ANL 150 A) | Fuse datasheet: pre-arc I²t ≥ 5 × 9.8 kA²s and time-current curve at 300–400 A | Engineering |
| OI-04 | B | IRLZ44N authenticity / matching | Buy from an authorised distributor or measure RDS(on) of each device at 10 A, V_GS 10 V (reject outliers > 25 mΩ) | User |
| OI-05 | B | Power assembly mechanics (busbars, heatsink, insulation, lugs) only sketched | Mechanical drawing, thermal check (Rth ≤ 1.5 K/W), insulation review | Engineering |
| OI-06 | H | One PCB connection unrouted (ENC_SW_RAW, J7.3 → R27) after autorouting | Route manually in KiCad 10, re-run DRC | Engineering |
| OI-07 | H | Autorouted PCB quality (long parallel traces, fragmented GND pours) | Manual clean-up of power and gate routing per doc 05 §1.1 | Engineering |
| OI-08 | H | KiCad 10 ERC and DRC have not been run (only KiCad 7 tools available in the cloud environment) | Run the commands in README §Validation on Windows/KiCad 10, commit reports to `Reports/ERC` and `Reports/DRC` | User |
| OI-09 | H | Files are in KiCad 7 format (opened and upgraded by KiCad 10) | Open in KiCad 10, save, commit the upgraded files | User |
| OI-10 | H | Stock component values/packages unconfirmed: ceramic capacitor values, resistor values other than 10 k, BZY97C15, LM393/74HCT14 package (DIP assumed), MCP9804 package (MSOP-8 assumed), electrolytic dimensions | Inventory check → update `KiCad/Generator/design.py` statuses/footprints → regenerate | User |
| OI-11 | H | TC4422 output (gate bus) not monitored by firmware | Optional: divider from GATE_OUT to a free input (needs a pin; e.g. move LED_READY to the OLED) | Engineering |
| OI-12 | M | Encoder module pin order unverified (J7) | Compare with module silkscreen | User |
| OI-13 | M | OLED supply range inconsistent in Midas spec (2.8–5.2 V vs 3.3 V) | Run at 3.3 V as designed; confirm with the PDF | User |
| OI-14 | M | NTC B value unknown | Calibrate at 2 temperatures, update `ntc_dc()` | User |
| OI-15 | M | Current is only estimated from V_DS (± 30 %) | Optional shunt (e.g. 75 mV/500 A) + amplifier in V2 | Engineering |
| OI-16 | M | 3D model path variable rewritten to `${KICAD10_3DMODEL_DIR}` (name not verified) | If 3D models are missing, define the variable in KiCad → Preferences → Configure Paths | User |
| OI-17 | M | I²C pull-ups to 3.3 V give only 0.3 V margin above ATmega V_IH (3.0 V at 5 V) | Verify on hardware; fallback: BSS138 level shifter | Engineering |
| OI-18 | L | Firmware RAM: 553 B static + 1024 B OLED buffer → ≈ 470 B left for stack | Monitor; option: page-mode display driver | Engineering |
| OI-19 | L | STPS3045CP possibly obsolete | Note replacement options in BOM | — |
| OI-20 | L | Schematic drawn by generator (label-based connections) | Optional manual beautification in KiCad 10 (does not change connectivity) | — |

Closed items are moved to `DEVELOPMENT_LOG.md` with the date and evidence.
