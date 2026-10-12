# SPDX-License-Identifier: GPL-3.0-or-later
"""
DIY_SPOT_WELDER_V1 - single-source circuit description.

Schematic sheets, PCB netlist and BOM are generated from THIS file.
Edit here, then run `python3 generate_all.py`.

Conventions
  * Net names are global (GND, VHOLD_LOGIC, ...). Inter-sheet connections are global labels.
  * on_board=False marks parts of the external POWER ASSEMBLY (busbars, MOSFETs, relay, fuse,
    switches, battery). They are in the schematic for completeness but are NOT placed on the
    control PCB (KiCad symbol attribute "exclude from board").
  * status: STOCK | PURCHASE | UNVERIFIED | REJECTED (see BOM/MASTER_BOM.csv)
  * Pin numbers refer to the KiCad symbol pin numbers, which were checked against the device
    datasheet pinouts (see Documentation/Datasheets/DATASHEET_INDEX.md).
"""

SHEETS = [
    # (number, file stem, title)
    (1, "01_SYSTEM_OVERVIEW", "System overview"),
    (2, "02_POWER_INPUT_AND_PROTECTION", "Power input, protection, hold-up and regulators"),
    (3, "03_CONTROL_AND_TIMING", "Microcontroller (Arduino Nano) and timing"),
    (4, "04_SWITCHING_AND_GATE_DRIVE", "Gate driver and MOSFET power assembly (assembly = off-board)"),
    (5, "05_RELAY_CONTROL_AND_ISOLATION", "Isolation relay, main fuse, disconnect, ARM / E-STOP chain"),
    (6, "06_CURRENT_VOLTAGE_SENSING", "Voltage sensing (battery, drain, electrode, rails)"),
    (7, "07_OLED_AND_USER_INTERFACE", "OLED, encoder, buttons, buzzer, LEDs"),
    (8, "08_TEMPERATURE_MONITORING", "Heatsink NTC and board temperature sensor"),
    (9, "09_TRIGGER_AND_INTERLOCKS", "Trigger conditioning, hardware pulse limiter, gate-drive UVLO"),
    (10, "10_SERVICE_AND_TEST_POINTS", "Test points and mechanical"),
]

# ---------------------------------------------------------------------------
# Footprints (all copied into Libraries/DIY_SPOT_WELDER_V1.pretty by the generator)
# ---------------------------------------------------------------------------
FP = dict(
    R="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    R5W="Resistor_THT:R_Axial_Power_L20.0mm_W6.4mm_P25.40mm",
    C="Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    CFILM="Capacitor_THT:C_Rect_L7.2mm_W4.5mm_P5.00mm_FKS2_FKP2_MKS2_MKP2",
    CP5="Capacitor_THT:CP_Radial_D5.0mm_P2.00mm",
    CP16="Capacitor_THT:CP_Radial_D16.0mm_P7.50mm",
    CP18="Capacitor_THT:CP_Radial_D18.0mm_P7.50mm",
    CP22="Capacitor_THT:CP_Radial_D22.0mm_P10.00mm_SnapIn",
    D35="Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal",
    D41="Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
    D201="Diode_THT:D_DO-201AD_P15.24mm_Horizontal",
    SMB="Diode_SMD:D_SMB",
    DIP8="Package_DIP:DIP-8_W7.62mm_Socket",
    DIP14="Package_DIP:DIP-14_W7.62mm_Socket",
    TO220="Package_TO_SOT_THT:TO-220-3_Vertical",
    TO92="Package_TO_SOT_THT:TO-92_Inline_Wide",
    MSOP8="Package_SO:MSOP-8_3x3mm_P0.65mm",
    NANO="Module:Arduino_Nano",
    FUSE="Fuse:Fuseholder_Cylinder-5x20mm_Schurter_0031_8201_Horizontal_Open",
    TB2="TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
    KK2="Connector_Molex:Molex_KK-254_AE-6410-02A_1x02_P2.54mm_Vertical",
    KK4="Connector_Molex:Molex_KK-254_AE-6410-04A_1x04_P2.54mm_Vertical",
    KK6="Connector_Molex:Molex_KK-254_AE-6410-06A_1x06_P2.54mm_Vertical",
    SOCK4="Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical",
    SOCK5="Connector_PinSocket_2.54mm:PinSocket_1x05_P2.54mm_Vertical",
    LED3="LED_THT:LED_D3.0mm",
    BUZ="Buzzer_Beeper:Buzzer_12x9.5RM7.6",
    SW6="Button_Switch_THT:SW_PUSH_6mm",
    TP="TestPoint:TestPoint_Loop_D2.50mm_Drill1.0mm",
    MH="MountingHole:MountingHole_3.2mm_M3",
)

COMPONENTS = []


def part(ref, sym, value, fp, sheet, pins, status, desc, mfr="", mpn="", spec="", ds="", notes="",
         on_board=True, dnp=False, price=""):
    COMPONENTS.append(dict(ref=ref, sym=sym, value=value, fp=fp if on_board else "", sheet=sheet,
                           pins=pins, status=status, desc=desc, mfr=mfr, mpn=mpn, spec=spec, ds=ds,
                           notes=notes, on_board=on_board, dnp=dnp, price=price))


def R(ref, val, a, b, sheet, notes="", status="STOCK", spec="0.25 W 1 % metal film", fp=None, mpn="", price="0.02"):
    part(ref, "Device:R", val, fp or FP["R"], sheet, {"1": a, "2": b}, status,
         f"Resistor {val}", spec=spec, notes=notes, mpn=mpn, price=price)


def C(ref, val, a, b, sheet, notes="", status="UNVERIFIED", spec="50 V X7R ceramic, 5 mm pitch", fp=None, price="0.05"):
    part(ref, "Device:C", val, fp or FP["C"], sheet, {"1": a, "2": b}, status,
         f"Capacitor {val}", spec=spec, notes=notes or "Value must be confirmed in the ceramic stock; else PURCHASE", price=price)


def CP(ref, val, pos, neg, sheet, fp, status="STOCK", spec="25 V aluminium electrolytic", notes="", price=""):
    part(ref, "Device:C_Polarized", val, fp, sheet, {"1": pos, "2": neg}, status,
         f"Electrolytic capacitor {val}", spec=spec, notes=notes, price=price)


def TP(ref, net, sheet):
    part(ref, "Connector:TestPoint", net, FP["TP"], sheet, {"1": net}, "PURCHASE",
         f"Test point {net}", spec="wire loop, 1.0 mm drill", price="0.05")


S2, S3, S4, S5, S6, S7, S8, S9, S10 = (n for n, *_ in SHEETS[1:])

# ===========================================================================
# 02 POWER INPUT AND PROTECTION
# ===========================================================================
part("J1", "Connector:Screw_Terminal_01x02", "PWR_IN", FP["TB2"], S2,
     {"1": "VBAT_IN", "2": "GND"}, "PURCHASE", "Screw terminal 2-pole 5.08 mm, control supply input",
     spec="2-pole, 5.08 mm, >=10 A", notes="Pin1 = fused tap from P_BUS (F_TAP), Pin2 = GND from SOURCE bar star point", price="0.60")
part("F1", "Device:Fuse", "T3.15A", FP["FUSE"], S2, {"1": "VBAT_IN", "2": "VBAT_F"}, "PURCHASE",
     "Fuse 5x20 mm time-lag 3.15 A + PCB holder", spec="5x20 mm T3.15A 250 V; I2t >> 1.6 A2s inrush",
     notes="Board-level fuse; the tap wire itself is fused at the source end (F_TAP)", price="1.00")
part("D3", "Device:D_Zener", "SMBJ15A", FP["SMB"], S2, {"1": "VBAT_F", "2": "GND"}, "PURCHASE",
     "TVS unidirectional 15 V standoff, 600 W", mfr="Littelfuse", mpn="SMBJ15A",
     spec="VRWM 15 V, VBR 16.7-18.5 V, VC 24.4 V @ 24.6 A", ds="https://www.littelfuse.com/products/tvs-diodes/surface-mount/smbj",
     notes="SMBJ24CA (stock) is NOT used here: its clamp (38.9 V) exceeds the 25 V capacitor and 20 V TC4422 ratings", price="0.30")
R("R1", "1.5R 5W", "VBAT_F", "VTAP", S2, spec="5 W wirewound, 5 %", fp=FP["R5W"], status="PURCHASE",
  notes="Inrush / fault limiting into 24.7 mF hold-up banks (peak ~8.6 A, 2.4 J at connection)", price="0.50")
part("D1", "Diode:1N5822", "1N5822", FP["D201"], S2, {"1": "VHOLD_LOGIC", "2": "VTAP"}, "PURCHASE",
     "Schottky 3 A 40 V - logic/gate-drive hold-up isolation", mfr="various", mpn="1N5822",
     spec="3 A, 40 V, VF ~0.45 V @ 0.4 A", ds="https://www.vishay.com/docs/88526/1n5820.pdf",
     notes="Blocks reverse polarity and holds VHOLD_LOGIC while the battery collapses during a weld", price="0.20")
part("D2", "Diode:1N5822", "1N5822", FP["D201"], S2, {"1": "VHOLD_RELAY", "2": "VTAP"}, "PURCHASE",
     "Schottky 3 A 40 V - relay hold-up isolation", mfr="various", mpn="1N5822", spec="3 A, 40 V",
     ds="https://www.vishay.com/docs/88526/1n5820.pdf", price="0.20")
CP("C1", "6800uF", "VHOLD_LOGIC", "GND", S2, FP["CP18"], notes="Hold-up logic + gate drive. Footprint assumes 18 mm dia, 7.5 mm pitch - VERIFY physical part")
CP("C2", "2200uF", "VHOLD_LOGIC", "GND", S2, FP["CP16"], notes="Hold-up logic. Footprint assumes 16 mm, 7.5 mm pitch - VERIFY")
C("C3", "100nF", "VHOLD_LOGIC", "GND", S2)
CP("C4", "10000uF", "VHOLD_RELAY", "GND", S2, FP["CP22"], notes="Hold-up relay coil. Footprint assumes 22 mm dia, 10 mm pitch - VERIFY")
CP("C5", "4700uF", "VHOLD_RELAY", "GND", S2, FP["CP16"], notes="Hold-up relay coil. Footprint assumes 16 mm, 7.5 mm pitch - VERIFY")
part("U2", "Regulator_Linear:L7805", "7805", FP["TO220"], S2, {"1": "VHOLD_LOGIC", "2": "GND", "3": "+5V_AUX"},
     "STOCK", "Linear regulator 5 V 1 A (auxiliary 5 V: HCT14, comparator references, buzzer, LEDs, 3.3 V LDO)",
     mfr="ST / various", mpn="L7805CV (assumed)", spec="Vin 7-35 V, 1.5 A, TO-220",
     ds="https://www.st.com/resource/en/datasheet/l78.pdf", notes="Exact manufacturer of stock part unknown; TO-220 pinout IN-GND-OUT assumed (standard)")
C("C6", "330nF", "VHOLD_LOGIC", "GND", S2, notes="7805 input capacitor per datasheet")
C("C7", "100nF", "+5V_AUX", "GND", S2)
CP("C8", "10uF", "+5V_AUX", "GND", S2, FP["CP5"], status="PURCHASE", spec="25 V electrolytic 5 mm", price="0.05")
part("U6", "Regulator_Linear:MCP1700x-330xxTO", "MCP1700-3302E/TO", FP["TO92"], S2,
     {"1": "GND", "2": "+5V_AUX", "3": "+3V3"}, "PURCHASE", "LDO 3.3 V 250 mA for OLED, MCP9804 and I2C pull-ups",
     mfr="Microchip", mpn="MCP1700-3302E/TO", spec="Vin 2.3-6 V, 250 mA, TO-92 (1=GND 2=VIN 3=VOUT)",
     ds="https://ww1.microchip.com/downloads/en/DeviceDoc/20001826D.pdf", price="0.40")
C("C9", "1uF", "+5V_AUX", "GND", S2, notes="MCP1700 input (1 uF min per datasheet)")
C("C10", "1uF", "+3V3", "GND", S2, notes="MCP1700 output (1 uF min per datasheet)")
part("LED1", "Device:LED", "GREEN 5V_AUX", FP["LED3"], S2, {"1": "GND", "2": "LED1_A"}, "PURCHASE",
     "LED 3 mm green - auxiliary 5 V present", spec="3 mm, 20 mA max", price="0.05")
R("R2", "1k", "+5V_AUX", "LED1_A", S2)
for i, net in enumerate(("GND", "VBAT_IN", "VHOLD_LOGIC", "VHOLD_RELAY")):
    part(f"#FLG0{i+1}", "power:PWR_FLAG", "PWR_FLAG", "", S2, {"1": net}, "", "", on_board=False)

# ===========================================================================
# 03 CONTROL AND TIMING
# ===========================================================================
part("U1", "MCU_Module:Arduino_Nano_v3.x", "Arduino Nano V3 (ATmega328P)", FP["NANO"], S3, {
    "1": None, "2": None, "3": None, "28": None,          # TX, RX (USB only), RESET x2
    "4": "GND", "29": "GND",
    "5": "ENC_A", "6": "ENC_B", "7": "ENC_SW", "8": "FOOT_ACT", "9": "ACK_ACT",
    "10": "RELAY_EN", "11": "BUZZER_CMD", "12": "GATE_CMD", "13": "LED_FAULT_CMD",
    "14": "GATE_FB", "15": "ARM_A_N", "16": "LED_READY_CMD",
    "17": None,                                           # 3V3 (USB chip, not used)
    "18": "AREF", "19": "ADC_VBAT", "20": "ADC_VDRAIN", "21": "ADC_VELEC", "22": "ADC_VDRV",
    "23": "SDA", "24": "SCL", "25": "ADC_NTC", "26": "ADC_VHOLD",
    "27": "+5V_MCU", "30": "VHOLD_LOGIC"},
    "PURCHASE", "Arduino Nano V3 compatible module (ATmega328P, 16 MHz, Optiboot bootloader)",
    mfr="Arduino / compatible", mpn="A000005 (or compatible)", spec="5 V logic, VIN 7-12 V recommended",
    ds="https://docs.arduino.cc/hardware/nano", notes="Mounted in 2x15 female headers. Must run the 'new' Optiboot bootloader (watchdog-safe). Powered via VIN from VHOLD_LOGIC; its on-board 5 V (net +5V_MCU) is ADC reference and NTC pull-up supply.",
    price="5-22")
C("C11", "100nF", "AREF", "GND", S3, notes="AREF decoupling for the internal 1.1 V reference")
C("C12", "100nF", "VHOLD_LOGIC", "GND", S3)

# ===========================================================================
# 04 SWITCHING AND GATE DRIVE
# ===========================================================================
part("U4", "Driver_FET:TC4422", "TC4422CPA", FP["DIP8"], S4,
     {"1": "VDRV", "8": "VDRV", "2": "GIN", "3": None, "4": "GND", "5": "GND", "6": "GATE_DRV", "7": "GATE_DRV"},
     "STOCK", "9 A non-inverting low-side MOSFET driver, PDIP-8 (in socket)", mfr="Microchip", mpn="TC4422CPA",
     spec="VDD 4.5-18 V, 9 A peak, TTL/CMOS input (VIH 2.4 V), 300 mV hysteresis",
     ds="https://ww1.microchip.com/downloads/en/DeviceDoc/20001420F.pdf",
     notes="Non-inverting => input pull-down gives OFF by default. TC4421 (inverting) is REJECTED for this function.")
C("C13", "100nF", "VDRV", "GND", S4, notes="Place at U4 pins 1/8 - 4/5")
CP("C14", "47uF", "VDRV", "GND", S4, FP["CP5"], status="PURCHASE", spec="25 V low-ESR electrolytic", price="0.10",
   notes="Local reservoir for gate-charge pulses (~0.5 uC)")
R("R3", "2.2R", "GATE_DRV", "GATE_OUT", S4, notes="Common gate resistor: damps cable ringing, limits clamp current", status="PURCHASE")
R("R4", "10k", "GATE_OUT", "GND", S4, notes="Gate bus pull-down on control board")
part("D4", "Device:D_Zener", "BZY97C15", FP["D41"], S4, {"1": "GATE_OUT", "2": "GND"}, "UNVERIFIED",
     "Zener 15 V 1.5 W - gate bus clamp (IRLZ44N VGS max +-16 V)", mfr="Vishay", mpn="BZY97C15",
     spec="Vz 13.8-15.6 V, 1.5 W", ds="https://www.vishay.com/docs/85614/bzy97.pdf",
     notes="Confirm C15 value is in the BZY97 stock; otherwise purchase BZY97C15 or 1.5KE15A")
part("J3", "Connector_Generic:Conn_01x06", "GATE_SENSE", FP["KK6"], S4,
     {"1": "GATE_OUT", "2": "GND", "3": "DRAIN_BUS", "4": "ELEC_POS", "5": "NTC_HS", "6": "GND"},
     "PURCHASE", "Molex KK 254 1x6 header + housing: gate twisted pair, drain/electrode sense, heatsink NTC",
     mfr="Molex", mpn="22-27-2061 / 22-01-3067", spec="2.54 mm, 2.5 A", price="0.80",
     notes="Use twisted pairs: (1,2) gate/Kelvin-source, (3,6), (5,6). Max length 150 mm.")
part("#FLG06", "power:PWR_FLAG", "PWR_FLAG", "", S4, {"1": "VDRV"}, "", "", on_board=False)

# ---- off-board MOSFET power assembly ----
for i in range(1, 7):
    part(f"Q10{i}", "Transistor_FET:IRLZ44N", "IRLZ44N", "", S4,
         {"1": f"G10{i}", "2": "DRAIN_BUS", "3": "GND"}, "STOCK",
         "N-MOSFET 55 V logic-level TO-220 (weld switch, 6 in parallel)", mfr="Infineon (IR)", mpn="IRLZ44NPBF",
         spec="VDSS 55 V, RDS(on) <=22 mOhm @10 V, IDM 160 A, EAS 210 mJ, RthJC 1.8 K/W",
         ds="https://www.infineon.com/dgdl/irlz44npbf.pdf?fileId=5546d462533600a40153567206892720",
         notes="POWER ASSEMBLY: tab (drain) bolted/soldered to the drain copper bar; source legs to source bar. Verify genuine parts (counterfeit risk).",
         on_board=False)
    part(f"R10{i}", "Device:R", "10R", "", S4, {"1": "GATE_OUT", "2": f"G10{i}"}, "PURCHASE",
         "Gate resistor 10 R per MOSFET (anti-oscillation, current sharing of gate drive)", spec="0.6 W metal film",
         on_board=False, price="0.02")
    part(f"R11{i}", "Device:R", "10k", "", S4, {"1": f"G10{i}", "2": "GND"}, "STOCK",
         "Gate-source pull-down per MOSFET (off if gate wire breaks)", spec="0.25 W", on_board=False)
part("D101", "Device:D_Schottky_Dual_CommonCathode_AKA", "STPS3045CP", "", S4,
     {"1": "DRAIN_BUS", "2": "P_BUS", "3": "DRAIN_BUS"}, "STOCK",
     "Dual Schottky 2x15 A 45 V SOT-93 - free-wheel diode across the welding cables",
     mfr="STMicroelectronics", mpn="STPS3045CP", spec="VRRM 45 V, IF(AV) 2x15 A, IFSM 220 A (10 ms) per diode",
     ds="https://www.st.com/resource/en/datasheet/stps3045c.pdf",
     notes="POWER ASSEMBLY: anodes to drain bar, cathode (tab) to P_BUS. Clamps V_DS to V_P+VF at turn-off (SPICE: 16 V instead of avalanche).",
     on_board=False)
part("C101", "Device:C_Polarized", "1000uF", "", S4, {"1": "P_BUS", "2": "GND"}, "STOCK",
     "Bus capacitor 1000 uF 25 V at the assembly (absorbs battery-lead inductance energy)",
     spec="25 V electrolytic, low ESR preferred", on_board=False)
part("D102", "Device:D_TVS", "SMBJ24CA", "", S4, {"1": "P_BUS", "2": "GND"}, "STOCK",
     "Bidirectional TVS 24 V 600 W across the bus", mfr="Littelfuse / various", mpn="SMBJ24CA-H",
     spec="VRWM 24 V, VBR 26.7 V min, VC 38.9 V", ds="https://www.littelfuse.com/products/tvs-diodes/surface-mount/smbj",
     notes="Secondary clamp only; the 1000 uF capacitor takes the energy.", on_board=False)
part("TH101", "Device:Thermistor_NTC", "10k B3950", "", S4, {"1": "NTC_HS", "2": "GND"}, "UNVERIFIED",
     "NTC 10 k on the drain bar (electrically insulated!)", spec="10 k @25 C, B ~3950 (verify from stock)",
     notes="Drain bar is at electrode potential: bond the NTC with Kapton + thermal epoxy; never connect to the bar.",
     on_board=False)
part("E1", "Connector:Conn_01x01_Pin", "ELECTRODE+", "", S4, {"1": "ELEC_POS"}, "PURCHASE",
     "Positive welding cable + copper electrode (16 mm2, 0.5 m)", on_board=False)
part("E2", "Connector:Conn_01x01_Pin", "ELECTRODE-", "", S4, {"1": "DRAIN_BUS"}, "PURCHASE",
     "Negative welding cable + copper electrode (16 mm2, 0.5 m), bolted to the drain bar", on_board=False)

# ===========================================================================
# 05 RELAY CONTROL AND ISOLATION
# ===========================================================================
part("Q1", "Transistor_BJT:BC337", "BC337", FP["TO92"], S5, {"1": "RELAY_COIL_N", "2": "Q1_B", "3": "GND"}, "STOCK",
     "NPN 45 V 800 mA - relay coil low-side switch", mfr="various", mpn="BC337-40",
     spec="VCEO 45 V, IC 800 mA, TO-92 C-B-E", ds="https://www.onsemi.com/pdf/datasheet/bc337-d.pdf")
R("R5", "220R", "RELAY_EN", "Q1_B", S5, notes="Base drive ~19 mA from D7 (forced beta ~16 at 300 mA)")
R("R6", "10k", "Q1_B", "GND", S5, notes="Keeps Q1 off while the MCU is in reset (pins hi-Z)")
part("D5", "Diode:1N4148", "1N4148", FP["D35"], S5, {"1": "D5_K", "2": "RELAY_COIL_N"}, "STOCK",
     "Coil clamp diode (in series with D6 zener for fast release)", mfr="various", mpn="1N4148",
     spec="100 V, IFRM 450 mA", ds="https://www.vishay.com/docs/81857/1n4148.pdf")
part("D6", "Device:D_Zener", "BZY97C15", FP["D41"], S5, {"1": "D5_K", "2": "VRELAY_ARM"}, "UNVERIFIED",
     "Zener 15 V - coil clamp (V_CE peak ~ V_coil + 15.7 V < 45 V)", mfr="Vishay", mpn="BZY97C15",
     spec="1.5 W", ds="https://www.vishay.com/docs/85614/bzy97.pdf", notes="Confirm C15 value is in stock")
part("J4", "Connector:Screw_Terminal_01x02", "RELAY_COIL", FP["TB2"], S5, {"1": "VRELAY_ARM", "2": "RELAY_COIL_N"},
     "PURCHASE", "Screw terminal 2-pole 5.08 mm - relay coil", price="0.60")
part("J2", "Connector_Generic:Conn_01x04", "ARM_ESTOP", FP["KK4"], S5,
     {"1": "VHOLD_RELAY", "2": "VRELAY_ARM", "3": "VHOLD_LOGIC", "4": "VDRV"}, "PURCHASE",
     "Molex KK 1x4 - two-pole E-STOP + ARM series chain", mfr="Molex", mpn="22-27-2041 / 22-01-3047", price="0.60",
     notes="Pole A (1->2) feeds the relay coil, pole B (3->4) feeds the gate driver. Opening either pole removes gate drive and/or opens the relay independently of the MCU.")
part("LED2", "Device:LED", "YELLOW ARMED", FP["LED3"], S5, {"1": "GND", "2": "LED2_A"}, "PURCHASE",
     "LED 3 mm yellow - gate drive supply live (hardware indication)", price="0.05")
R("R7", "4.7k", "VDRV", "LED2_A", S5)
part("#FLG07", "power:PWR_FLAG", "PWR_FLAG", "", S5, {"1": "VRELAY_ARM"}, "", "", on_board=False)
# ---- off-board ----
part("BT1", "Device:Battery", "RITAR RT1270 12V 7Ah", "", S5, {"1": "BAT_POS", "2": "GND"}, "UNVERIFIED",
     "Welding source - 12 V VRLA 7 Ah (NOT APPROVED as welding source, see doc 03)", mfr="Ritar", mpn="RT1270",
     spec="Rint <=32 mOhm (DS3), max discharge 70 A / 5 s (DS3), FASTON terminals", on_board=False,
     notes="Battery - is connected to the SOURCE bar (=GND star point) with 16 mm2 cable.")
part("F101", "Device:Fuse", "ANL 150A", "", S5, {"1": "BAT_POS", "2": "BAT_FUSED"}, "PURCHASE",
     "Main fuse ANL/MIDI 150 A + holder, mounted within 150 mm of the battery +",
     spec="32 V DC, breaking capacity >= 2 kA; pre-arc I2t must be >= 5x weld-pulse I2t (doc 03)",
     notes="Rating PROVISIONAL - final choice needs the fuse I2t datasheet and the measured source current", on_board=False, price="10")
part("S101", "Switch:SW_SPST", "MAIN DISCONNECT", "", S5, {"1": "BAT_FUSED", "2": "P_BUS"}, "PURCHASE",
     "Battery isolator switch (manual emergency disconnect), >=300 A intermittent", on_board=False, price="10")
part("K101", "Relay:Relay_SPST-NO", "RELAY 12V ~100A (unknown)", "", S5,
     {"A1": "VRELAY_ARM", "A2": "RELAY_COIL_N", "13": "P_BUS", "14": "ELEC_POS"}, "UNVERIFIED",
     "Isolation relay (carry-only, never switched under weld current by design)",
     spec="12 V coil ~300 mA, contacts marked ~100 A; DC rating, make/break, drop-out voltage UNKNOWN",
     notes="May only be used after the tests in RELEASE_CHECKLIST.md (contact resistance, drop-out voltage, operate/release time). Replacement: rated DC contactor.",
     on_board=False)
part("F102", "Device:Fuse", "3A blade", "", S5, {"1": "P_BUS", "2": "VBAT_IN"}, "PURCHASE",
     "Inline blade fuse 3 A at the P_BUS tap (protects the thin supply wire)", on_board=False, price="2")
part("S102", "Switch:SW_DPST", "E-STOP 2NC", "", S5,
     {"1": "VHOLD_RELAY", "2": "ESTOP_A", "3": "VHOLD_LOGIC", "4": "ESTOP_B"}, "PURCHASE",
     "Emergency stop mushroom, 2 NC contacts (symbol drawn as generic DPST)", on_board=False, price="6")
part("S103", "Switch:SW_DPST", "ARM KEY 2NO", "", S5,
     {"1": "ESTOP_A", "2": "VRELAY_ARM", "3": "ESTOP_B", "4": "VDRV"}, "PURCHASE",
     "ARM key switch or guarded toggle, 2 NO contacts", on_board=False, price="6")

# ===========================================================================
# 06 CURRENT / VOLTAGE SENSING  (all dividers 33k/10k, k = 4.30)
# ===========================================================================
for n, (src, adc, cref) in enumerate((("VBAT_F", "ADC_VBAT", "C15"), ("DRAIN_BUS", "ADC_VDRAIN", "C16"),
                                       ("ELEC_POS", "ADC_VELEC", "C17"), ("VDRV", "ADC_VDRV", "C18"),
                                       ("VHOLD_LOGIC", "ADC_VHOLD", "C19"))):
    R(f"R{10+2*n}", "33k", src, adc, S6, notes=f"{adc} divider top")
    R(f"R{11+2*n}", "10k", adc, "GND", S6, notes=f"{adc} divider bottom")
    C(cref, "100nF", adc, "GND", S6, notes="ADC anti-alias / spike filter (tau 0.77 ms)")

# ===========================================================================
# 07 OLED AND USER INTERFACE
# ===========================================================================
part("J6", "Connector_Generic:Conn_01x04", "OLED", FP["SOCK4"], S7, {"1": "+3V3", "2": "GND", "3": "SCL", "4": "SDA"},
     "PURCHASE", "Female header 1x4 for MDOB128064WV-YBI (pin1 VCC, 2 GND, 3 SCL, 4 SDA)", price="0.20",
     notes="Display: Midas MDOB128064WV-YBI (STOCK), SSD1306 I2C 0x3C. Pin order per Midas spec (VCC,GND,SCL,SDA) - re-check on the physical module before power-up.")
R("R20", "4.7k", "+3V3", "SDA", S7, notes="I2C pull-up to 3.3 V (OLED/MCP9804 are 3.3 V parts). ATmega VIH = 3.0 V @ 5 V -> 0.3 V margin; firmware disables internal 5 V pull-ups.")
R("R21", "4.7k", "+3V3", "SCL", S7, notes="see R20")
part("J7", "Connector_Generic:Conn_01x05", "ENCODER", FP["SOCK5"], S7,
     {"1": "GND", "2": "+5V_AUX", "3": "ENC_SW_RAW", "4": "ENC_B_RAW", "5": "ENC_A_RAW"}, "PURCHASE",
     "Female header 1x5 for EC11 encoder module (GND, +, SW, DT, CLK)", price="0.20",
     notes="Encoder module pin order is UNVERIFIED - check the silk of the stock module and adapt the cable.")
part("SW1", "Switch:SW_Push", "ACK / RESET FAULT", FP["SW6"], S7, {"1": "ACK_RAW", "2": "GND"}, "STOCK",
     "Tactile switch 6x6 mm - fault acknowledge")
# Schmitt conditioning (74HCT14, inverting): RAW (active low) -> ACT (active high)
for unit_pins, raw, act, rpu, rs, cf, cval in (
        (("1", "2"), "ENC_A_RAW", "ENC_A", "R22", "R23", "C20", "10nF"),
        (("3", "4"), "ENC_B_RAW", "ENC_B", "R24", "R25", "C21", "10nF"),
        (("5", "6"), "ENC_SW_RAW", "ENC_SW", "R26", "R27", "C22", "100nF"),
        (("11", "10"), "ACK_RAW", "ACK_ACT", "R28", "R29", "C23", "100nF")):
    R(rpu, "10k", "+5V_AUX", raw, S7, notes=f"{raw} pull-up")
    R(rs, "1k", raw, raw + "_F", S7, notes="series / RC filter")
    C(cf, cval, raw + "_F", "GND", S7)
COMPONENTS.append(dict(ref="U5", sym="74xx:74HC14", value="74HCT14", fp=FP["DIP14"], sheet=S7,
                       pins={"1": "ENC_A_RAW_F", "2": "ENC_A", "3": "ENC_B_RAW_F", "4": "ENC_B",
                             "5": "ENC_SW_RAW_F", "6": "ENC_SW", "11": "ACK_RAW_F", "10": "ACK_ACT",
                             "9": "FOOT_RAW_F", "8": "FOOT_ACT", "13": "ARM_A_DIV", "12": "ARM_A_N",
                             "14": "+5V_AUX", "7": "GND"},
                       unit_sheets={1: S7, 2: S7, 3: S7, 5: S7, 4: S9, 6: S9, 7: S9},
                       status="STOCK", desc="Hex Schmitt-trigger inverter, HCT (TTL thresholds), PDIP-14 in socket",
                       mfr="Nexperia/TI (assumed)", mpn="74HCT14N", spec="VCC 4.5-5.5 V",
                       ds="https://assets.nexperia.com/documents/data-sheet/74HC_HCT14.pdf",
                       notes="Symbol 74xx:74HC14 used (identical pinout)", on_board=True, dnp=False, price=""))
part("BZ1", "Device:Buzzer", "BUZZER 5V", FP["BUZ"], S7, {"1": "+5V_AUX", "2": "BZ_N"}, "PURCHASE",
     "Active buzzer 5 V, 12 mm, 7.6 mm pitch", spec="<=30 mA", price="0.50")
part("Q2", "Transistor_BJT:BC547", "BC547", FP["TO92"], S7, {"1": "BZ_N", "2": "Q2_B", "3": "GND"}, "STOCK",
     "NPN buzzer driver", mfr="various", mpn="BC547B", spec="45 V 100 mA TO-92 C-B-E",
     ds="https://www.onsemi.com/pdf/datasheet/bc546-d.pdf")
R("R30", "1k", "BUZZER_CMD", "Q2_B", S7)
R("R31", "10k", "Q2_B", "GND", S7)
part("D7", "Diode:1N4148", "1N4148", FP["D35"], S7, {"1": "+5V_AUX", "2": "BZ_N"}, "STOCK",
     "Buzzer flyback diode", mpn="1N4148")
part("LED3", "Device:LED", "RED FAULT", FP["LED3"], S7, {"1": "GND", "2": "LED3_A"}, "PURCHASE", "LED 3 mm red - fault", price="0.05")
R("R32", "1k", "LED_FAULT_CMD", "LED3_A", S7)
part("LED4", "Device:LED", "GREEN READY", FP["LED3"], S7, {"1": "GND", "2": "LED4_A"}, "PURCHASE", "LED 3 mm green - ready", price="0.05")
R("R33", "1k", "LED_READY_CMD", "LED4_A", S7)

# ===========================================================================
# 08 TEMPERATURE MONITORING
# ===========================================================================
R("R34", "10k", "+5V_MCU", "ADC_NTC", S8, notes="NTC pull-up, ratiometric to the ADC reference")
R("R35", "1k", "NTC_HS", "ADC_NTC", S8, notes="series protection for the off-board NTC wire")
C("C24", "100nF", "ADC_NTC", "GND", S8)
part("U7", "Sensor_Temperature:MCP9804_MSOP", "MCP9804", FP["MSOP8"], S8,
     {"1": "SDA", "2": "SCL", "3": "TEMP_ALERT", "4": "GND", "5": "GND", "6": "GND", "7": "GND", "8": "+3V3"},
     "UNVERIFIED", "Digital temperature sensor +-0.25 C typ, I2C address 0x18 (board/ambient temperature)",
     mfr="Microchip", mpn="MCP9804-E/MS (package assumed)", spec="2.7-5.5 V, MSOP-8",
     ds="https://ww1.microchip.com/downloads/en/DeviceDoc/22203C.pdf",
     notes="Confirm the stock package (MSOP-8 vs DFN-8). Alert output routed to a test point for future hardware use.")
C("C25", "100nF", "+3V3", "GND", S8)
R("R36", "10k", "+3V3", "TEMP_ALERT", S8, notes="Alert is open-drain")

# ===========================================================================
# 09 TRIGGER AND INTERLOCKS
# ===========================================================================
part("J5", "Connector_Generic:Conn_01x02", "FOOT_SWITCH", FP["KK2"], S9, {"1": "FOOT_RAW", "2": "GND"}, "PURCHASE",
     "Molex KK 1x2 - foot switch (normally open)", price="0.40")
R("R40", "10k", "+5V_AUX", "FOOT_RAW", S9, notes="foot switch pull-up (open/broken cable = not pressed)")
R("R41", "1k", "FOOT_RAW", "FOOT_RAW_F", S9)
C("C26", "100nF", "FOOT_RAW_F", "GND", S9, notes="tau 0.1 ms + firmware 30 ms confirmation")
R("R42", "10k", "VRELAY_ARM", "ARM_A_DIV", S9, notes="ARM pole A sense divider (14.7 V -> 4.7 V)")
R("R43", "4.7k", "ARM_A_DIV", "GND", S9)
C("C27", "100nF", "ARM_A_DIV", "GND", S9)
C("C28", "100nF", "+5V_AUX", "GND", S9, notes="U5 decoupling")
# gate command path with wired-AND clamps
R("R44", "2.2k", "GATE_CMD", "GIN", S9, notes="MCU -> TC4422 input; LM393 outputs can override (wired-AND)")
R("R45", "22k", "GIN", "GND", S9, notes="Default-OFF pull-down: TC4422 input low while MCU is reset/unpowered")
R("R46", "10k", "GIN", "GATE_FB", S9, notes="Read-back of the effective gate command")
# pulse-length limiter
R("R47", "68k", "GATE_CMD", "PL_CT", S9, notes="Pulse limiter timing (window 63-96 ms, see doc 03)")
part("C29", "Device:C", "1uF film", FP["CFILM"], S9, {"1": "PL_CT", "2": "GND"}, "PURCHASE",
     "Timing capacitor 1 uF film +-10 % (no DC-bias loss)", mfr="WIMA / Kemet", mpn="MKS2 1uF 63V (or equiv.)",
     spec="63 V PET film, +-10 %, 5 mm", price="0.30")
R("R48", "4.7k", "PL_CT", "PL_DIS", S9, notes="discharge path (tau 4.7 ms)")
part("D8", "Diode:1N4148", "1N4148", FP["D35"], S9, {"1": "GATE_CMD", "2": "PL_DIS"}, "STOCK",
     "Limiter reset diode", mpn="1N4148")
R("R49", "10k", "+5V_AUX", "PL_VTH", S9, notes="Vth = 0.6875 x 5 V")
R("R50", "22k", "PL_VTH", "GND", S9)
# UVLO
R("R51", "22k", "VDRV", "UV_SENSE", S9, notes="UVLO trip at VDRV = 2.5 V x 3.2 = 8.0 V")
R("R52", "10k", "UV_SENSE", "GND", S9)
C("C30", "100nF", "UV_SENSE", "GND", S9)
R("R53", "10k", "+5V_AUX", "VREF_2V5", S9)
R("R54", "10k", "VREF_2V5", "GND", S9)
C("C31", "100nF", "VREF_2V5", "GND", S9)
COMPONENTS.append(dict(ref="U3", sym="Comparator:LM393", value="LM393", fp=FP["DIP8"], sheet=S9,
                       pins={"1": "GIN", "2": "PL_CT", "3": "PL_VTH",
                             "7": "GIN", "6": "VREF_2V5", "5": "UV_SENSE",
                             "8": "VHOLD_LOGIC", "4": "GND"},
                       unit_sheets={1: S9, 2: S9, 3: S9},
                       status="STOCK", desc="Dual comparator, open collector - A: hardware pulse-length limiter, B: gate-drive UVLO",
                       mfr="TI/ST (assumed)", mpn="LM393P (PDIP-8 assumed)", spec="2-36 V, Vos 5 mV max, sink 6 mA",
                       ds="https://www.ti.com/lit/ds/symlink/lm393.pdf",
                       notes="Package of stock part UNVERIFIED (PDIP-8 assumed). Outputs are wired-AND onto GIN.",
                       on_board=True, dnp=False, price=""))
C("C32", "100nF", "VHOLD_LOGIC", "GND", S9, notes="U3 decoupling")

# ===========================================================================
# 10 SERVICE AND TEST POINTS
# ===========================================================================
for i, net in enumerate(("GND", "GND", "GND", "VBAT_F", "VHOLD_LOGIC", "VHOLD_RELAY", "+5V_AUX", "+5V_MCU", "+3V3",
                         "VDRV", "GATE_CMD", "GIN", "GATE_OUT", "PL_CT", "UV_SENSE", "DRAIN_BUS", "TEMP_ALERT")):
    TP(f"TP{i+1}", net, S10)
for i in range(1, 5):
    part(f"H{i}", "Mechanical:MountingHole", "M3", FP["MH"], S10, {}, "PURCHASE",
         "Mounting hole M3, isolated (use nylon spacers)", price="0")


# ---------------------------------------------------------------------------
# Off-board mechanical / wiring items (BOM only)
# ---------------------------------------------------------------------------
BOM_EXTRA = [
    # ref, qty, desc, mfr, mpn, spec, pkg, status, price, ds, notes
    ("MECH1", 1, "Drain copper bar (MOSFET tabs + heatsink + negative cable lug)", "", "", "Cu 200x25x5 mm (provisional)", "busbar", "PURCHASE", "15", "", "Electrically at electrode potential: insulate from enclosure"),
    ("MECH2", 1, "Source copper bar (MOSFET source legs, battery-, control GND star point)", "", "", "Cu 200x15x3 mm (provisional)", "busbar", "PURCHASE", "10", "", "Single-point ground for control board"),
    ("MECH3", 1, "Heatsink for drain bar", "", "", "Rth <= 1.5 K/W (estimate for 26 W at 1 weld/2 s)", "", "PURCHASE", "10", "", "Thermal pad must not be needed: drain bar is the tab potential - heatsink then also at electrode potential; or use insulating pad >=1.5 kV"),
    ("CAB1", 2, "Welding cable 16 mm2 fine-stranded silicone, 0.5 m each, with lugs", "", "", "16 mm2 Cu", "", "PURCHASE", "12", "", "Keep both cables together/twisted to minimise loop inductance"),
    ("CAB2", 2, "Battery cable 16 mm2, 0.3 m each, ring lugs M6", "", "", "16 mm2 Cu", "", "PURCHASE", "6", "", "RT1270 has FASTON tabs - see doc 03 (not suitable for 300 A)"),
    ("CAB3", 1, "Signal cable set: 3 twisted pairs AWG24 (gate/Kelvin, drain sense, NTC), 0.15 m", "", "", "", "", "PURCHASE", "2", "", ""),
    ("ELEC1", 2, "Copper welding electrodes (solid Cu 10 mm2 or W/Cu tips)", "", "", "", "", "PURCHASE", "8", "", ""),
    ("ENCL1", 1, "Enclosure, non-conductive (or earthed metal with insulated busbars)", "", "", "", "", "PURCHASE", "20", "", ""),
    ("FOOT1", 1, "Foot switch, normally open, with 2-core cable", "", "", "", "", "PURCHASE", "8", "", ""),
    ("SOCK1", 2, "Female header 1x15 2.54 mm for Arduino Nano", "", "", "", "", "PURCHASE", "0.60", "", ""),
    ("SOCK2", 2, "IC socket DIP-8", "", "", "", "", "PURCHASE", "0.20", "", ""),
    ("SOCK3", 1, "IC socket DIP-14", "", "", "", "", "PURCHASE", "0.20", "", ""),
    ("DISP1", 1, "OLED 0.96 in 128x64 yellow/blue, SSD1306, I2C", "Midas", "MDOB128064WV-YBI", "VCC 2.8-5.2 V (pin table) / 3.3 V typ", "COB 4-pin", "STOCK", "", "https://midasdisplays.com/wp-content/uploads/2024/12/MDOB128064WV-YBI.pdf", "Spec sheet inconsistent on VCC range; powered from 3.3 V"),
    ("ENC1", 1, "EC11 rotary encoder module with push switch", "", "EC11 module", "", "module", "STOCK", "", "", "Pin order UNVERIFIED"),
]

# Inventory items evaluated but NOT used (BOM rows with status REJECTED / reserve)
BOM_NOT_USED = [
    ("X1", 1, "MOSFET 500 V 20 A TO-247", "IXYS", "IXFH20N50P3", "RDS(on) ~0.3 Ohm", "TO-247", "REJECTED", "", "", "RDS(on) >50x too high for weld switching (0.3 Ohm x 300 A = 90 V drop - impossible)"),
    ("X2", 1, "MOSFET 600 V 6 A TO-220", "ST", "STP6NK60", "RDS(on) ~1.2 Ohm", "TO-220", "REJECTED", "", "", "RDS(on) far too high; high-voltage part"),
    ("X3", 1, "MOSFET driver 9 A inverting", "Microchip", "TC4421CPA", "", "PDIP-8", "REJECTED", "", "", "Inverting: a pull-down on its input would turn the MOSFETs ON. Kept as spare only."),
    ("X4", 1, "H-bridge driver 3.6 A", "TI", "DRV8872", "6.5-45 V", "HSOP-8", "REJECTED", "", "https://www.ti.com/lit/ds/symlink/drv8872.pdf", "Relay coil needs no reversal; a BJT is simpler; H-bridge gives no safety advantage"),
    ("X5", 1, "Stepper/H-bridge driver", "TI", "DRV8816", "", "HTSSOP", "REJECTED", "", "https://www.ti.com/lit/ds/symlink/drv8816.pdf", "Not needed"),
    ("X6", 1, "Dual H-bridge 1.5 A", "TI", "DRV8833", "2.7-10.8 V", "HTSSOP", "REJECTED", "", "https://www.ti.com/lit/ds/symlink/drv8833.pdf", "Max 10.8 V supply < 12 V battery"),
    ("X7", 1, "H-bridge 3.6 A", "TI", "DRV8870", "6.5-45 V", "HSOP-8", "REJECTED", "", "https://www.ti.com/lit/ds/symlink/drv8870.pdf", "Not needed (see DRV8872)"),
    ("X8", 1, "Optocoupler", "Sharp/various", "PC817", "CTR 50-600 %", "DIP-4", "STOCK", "", "", "Not used in V1 (common ground is acceptable for a low-side switch); reserve for an isolated foot-switch input"),
    ("X9", 1, "NPN 2N2222", "various", "2N2222", "40 V 600 mA", "TO-92 (E-B-C!)", "STOCK", "", "", "Not used; note E-B-C pinout differs from BC337 (C-B-E)"),
    ("X10", 1, "Beetle ESP32-C3 board (NOT a timer module)", "DFRobot", "DFR0868", "ESP32-C3, 3.3 V I/O", "module", "STOCK", "", "https://wiki.dfrobot.com/SKU_DFR0868_Beetle_ESP32_C3", "Inventory described it as 'adjustable timer module' - it is an ESP32-C3 dev board. Alternative MCU (not selected: 3.3 V I/O, boot-time GPIO glitches, pinout not verified here)"),
    ("X11", 1, "Relay coil H-bridge concept", "", "", "", "", "REJECTED", "", "", "Relay as pulse switch rejected (timing 5-15 ms, bounce, arcing) - see doc 02"),
]
