# SPDX-License-Identifier: GPL-3.0-or-later
"""
Generate the hierarchical KiCad schematic of DIY_SPOT_WELDER_V1 from design.py.

Output (relative to KiCad/):
  DIY_SPOT_WELDER_V1.kicad_sch                root sheet (01_SYSTEM_OVERVIEW)
  Hierarchical_Sheets/NN_*.kicad_sch          sub-sheets 02..10
  Libraries/DIY_SPOT_WELDER_V1.kicad_sym      project symbol library (flattened copies of KiCad symbols)

File format: KiCad 7 schematic format (version 20230121). KiCad 8/9/10 open it natively and
upgrade it when saved. The format was chosen so that the files can be checked in this
environment with KiCad 7.0.11 (kicad-cli). See README.md.
"""
import copy
import os
import uuid as uuidlib

from sexpr import Q, dumps, find, find1
from symlib import SymLib, pins as sym_pins, unit_count, body_bbox
import design as D

PROJECT = "DIY_SPOT_WELDER_V1"
LIBNAME = PROJECT
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATE = "2026-10-12"
REV = "A (PRELIMINARY)"
COMPANY = "DIY_SPOT_WELDER_V1 project - GPL-3.0-or-later"
GRID = 1.27
STUB = 2.54

_ns = uuidlib.UUID("6b1f7a2e-0d0e-4f39-9a4e-2f1c5e7d9a10")


def uid(*parts):
    """Deterministic UUID so regenerating does not churn the files."""
    return str(uuidlib.uuid5(_ns, "/".join(str(p) for p in parts)))


def snap(v):
    return round(round(v / GRID) * GRID, 4)


def fnt(size=1.27, hide=False, justify=None, bold=False):
    e = ["effects", ["font", ["size", size, size]] + (["bold"] if bold else [])]
    if justify:
        e.append(["justify"] + justify.split())
    if hide:
        e.append("hide")
    return e


SL = SymLib()

# ---------------------------------------------------------------------------
# Symbol library handling
# ---------------------------------------------------------------------------
_used_syms = {}


def lib_symbol(full):
    """full = 'Lib:Name' (KiCad library). Returns (local_name, flattened symbol)."""
    if full not in _used_syms:
        lib, name = full.split(":")
        s = SL.get(lib, name)
        _used_syms[full] = (name, s)
    return _used_syms[full]


def embedded(full):
    name, s = lib_symbol(full)
    e = copy.deepcopy(s)
    e[1] = Q(f"{LIBNAME}:{name}")
    return e


def write_project_library(path):
    syms = []
    names = set()
    for full, (name, s) in sorted(_used_syms.items(), key=lambda kv: kv[1][0]):
        if name in names:
            continue
        names.add(name)
        s2 = copy.deepcopy(s)
        # point default footprint to project library if it exists there
        syms.append(s2)
    tree = ["kicad_symbol_lib", ["version", 20220914], ["generator", "kicad_symbol_editor"]] + syms
    with open(path, "w", encoding="utf-8") as f:
        f.write(dumps(tree) + "\n")


# ---------------------------------------------------------------------------
# Instance building
# ---------------------------------------------------------------------------
ROTATE_90 = {"Device:R", "Device:C", "Device:C_Polarized", "Device:Fuse", "Device:Thermistor_NTC"}


def sym_rot(comp):
    return 90 if comp["sym"] in ROTATE_90 else 0


def xf(x, y, rot):
    """lib coords (y up) -> screen offset (y down), rotated CCW on screen by rot degrees"""
    sx, sy = x, -y
    if rot == 90:
        return (sy, -sx)
    return (sx, sy)


def xd(d, rot):
    if rot == 90:
        return (d[1], -d[0])
    return d


def outward(angle):
    a = int(round(angle)) % 360
    return {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[a]


def label_angle(d):
    return {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[d]


def instances():
    """Yield (comp, unit, sheet_no, pin_list) for every placed symbol unit."""
    for c in D.COMPONENTS:
        name, s = lib_symbol(c["sym"])
        nunits = unit_count(s)
        allpins = sym_pins(s)
        used_units = sorted({p["unit"] for p in allpins if p["number"] in c["pins"] and p["unit"] != 0} or {1})
        if not c["pins"]:
            used_units = [1]
        if nunits > 1:
            used_units = list(range(1, nunits + 1))
        for u in used_units:
            sheet = c.get("unit_sheets", {}).get(u, c["sheet"])
            plist = [p for p in allpins if p["unit"] in (0, u)]
            yield c, u, sheet, plist


def net_sheets():
    """Map net -> set of sheets it appears on (to choose global vs local labels)."""
    m = {}
    for c, u, sh, plist in instances():
        if plist is None:
            for n in c["pins"].values():
                m.setdefault(n, set()).add(sh)
            continue
        for p in plist:
            n = c["pins"].get(p["number"])
            if n:
                m.setdefault(n, set()).add(sh)
    return m


GLOBAL_ALWAYS = {"VBAT_IN", "VBAT_F", "VHOLD_LOGIC", "VHOLD_RELAY", "VDRV", "VRELAY_ARM", "+5V_AUX", "+5V_MCU", "+3V3",
                 "GATE_OUT", "DRAIN_BUS", "ELEC_POS", "P_BUS"}


class Sheet:
    def __init__(self, no, stem, title):
        self.no, self.stem, self.title = no, stem, title
        self.items = []
        self.lib_ids = set()
        self.width, self.height, self.paper = 420.0, 297.0, "A3"

    def add(self, x):
        self.items.append(x)


_pwr_counter = [0]


def pwr_ref():
    _pwr_counter[0] += 1
    return f"#PWR{_pwr_counter[0]:03d}"


def text_len(s, size=1.27):
    return len(s) * size * 0.85 + 2.0


def place_symbol(sheet, comp, unit, plist, X, Y, root_uuid, sheet_uuid, gl_nets):
    """Emit symbol + wires + labels for one unit at (X, Y). Returns nothing."""
    full = comp["sym"]
    name, s = lib_symbol(full)
    sheet.lib_ids.add(full)
    inst_uuid = uid("sym", comp["ref"], unit)
    path = f"/{root_uuid}" + (f"/{sheet_uuid}" if sheet_uuid else "")
    is_power = full.startswith("power:")
    rot = sym_rot(comp)
    bb = body_bbox(s, unit)
    c1 = xf(bb[0], bb[1], rot); c2 = xf(bb[2], bb[3], rot)
    top, bot = min(c1[1], c2[1]), max(c1[1], c2[1])
    props = []
    ref_y = snap(Y + top - 1.5)
    val_y = snap(Y + bot + 2.5)
    props.append(["property", Q("Reference"), Q(comp["ref"]), ["at", snap(X), ref_y, rot], fnt(hide=is_power)])
    props.append(["property", Q("Value"), Q(comp["value"]), ["at", snap(X), val_y, rot], fnt(hide=False)])
    fpv = comp["fp"]
    if fpv:
        fpv = f"{LIBNAME}:" + fpv.split(":", 1)[1]
    props.append(["property", Q("Footprint"), Q(fpv), ["at", snap(X), snap(val_y + 2.54), 0], fnt(hide=True)])
    props.append(["property", Q("Datasheet"), Q(comp.get("ds") or "~"), ["at", snap(X), snap(val_y + 5.08), 0], fnt(hide=True)])
    extra = [("Manufacturer", comp.get("mfr", "")), ("MPN", comp.get("mpn", "")), ("Status", comp.get("status", "")),
             ("Spec", comp.get("spec", "")), ("Description", comp.get("desc", "")), ("Notes", comp.get("notes", ""))]
    if not comp["on_board"] and not is_power:
        extra.append(("Board", "POWER_ASSEMBLY (off-board, excluded from PCB)"))
    k = 3
    for key, val in extra:
        if val:
            props.append(["property", Q(key), Q(val), ["at", snap(X), snap(val_y + 2.54 * k), 0], fnt(hide=True)])
            k += 1
    pin_nodes = []
    if plist is None:
        plist = sym_pins(s)
    for p in plist:
        pin_nodes.append(["pin", Q(p["number"]), ["uuid", uid("pin", comp["ref"], unit, p["number"])]])
    on_board = "yes" if comp["on_board"] else "no"
    in_bom = "no" if is_power else "yes"
    node = ["symbol", ["lib_id", Q(f"{LIBNAME}:{name}")], ["at", snap(X), snap(Y), rot], ["unit", unit],
            ["in_bom", in_bom], ["on_board", on_board], ["dnp", "yes" if comp.get("dnp") else "no"],
            ["uuid", inst_uuid]] + props + pin_nodes + [
        ["instances", ["project", Q(PROJECT), ["path", Q(path), ["reference", Q(comp["ref"])], ["unit", unit]]]]]
    sheet.add(node)
    # connections: group pins by location
    groups = {}
    for p in plist:
        key = (round(p["x"], 3), round(p["y"], 3))
        groups.setdefault(key, []).append(p)
    for (px, py), ps in groups.items():
        nets = {comp["pins"].get(p["number"], "__MISSING__") for p in ps if not (p["hidden"] and p["type"] == "no_connect")}
        if not nets:
            continue
        if "__MISSING__" in nets:
            raise SystemExit(f"{comp['ref']} unit {unit}: pin(s) {[p['number'] for p in ps]} have no net assignment in design.py")
        if len(nets) > 1:
            raise SystemExit(f"{comp['ref']}: stacked pins {[p['number'] for p in ps]} map to different nets {nets}")
        net = nets.pop()
        vis = [p for p in ps if not p["hidden"]] or ps
        ang = vis[0]["angle"]
        ox, oy = xf(px, py, rot)
        ex, ey = snap(X + ox), snap(Y + oy)
        if net is None:
            sheet.add(["no_connect", ["at", ex, ey], ["uuid", uid("nc", comp["ref"], unit, px, py)]])
            continue
        d = xd(outward(ang), rot)
        sx, sy = snap(ex + d[0] * STUB), snap(ey + d[1] * STUB)
        sheet.add(["wire", ["pts", ["xy", ex, ey], ["xy", sx, sy]], ["stroke", ["width", 0], ["type", "default"]],
                   ["uuid", uid("w", comp["ref"], unit, px, py)]])
        if net == "GND":
            ref = pwr_ref()
            lib_symbol("power:GND")
            sheet.lib_ids.add("power:GND")
            rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[d]
            sheet.add(["symbol", ["lib_id", Q(f"{LIBNAME}:GND")], ["at", sx, sy, rot], ["unit", 1],
                       ["in_bom", "no"], ["on_board", "yes"], ["dnp", "no"], ["uuid", uid("gnd", comp["ref"], unit, px, py)],
                       ["property", Q("Reference"), Q(ref), ["at", sx, sy, 0], fnt(hide=True)],
                       ["property", Q("Value"), Q("GND"), ["at", sx, snap(sy + 3.81), 0], fnt(hide=True)],
                       ["property", Q("Footprint"), Q(""), ["at", sx, sy, 0], fnt(hide=True)],
                       ["property", Q("Datasheet"), Q(""), ["at", sx, sy, 0], fnt(hide=True)],
                       ["pin", Q("1"), ["uuid", uid("gndpin", comp["ref"], unit, px, py)]],
                       ["instances", ["project", Q(PROJECT), ["path", Q(path), ["reference", Q(ref)], ["unit", 1]]]]])
            continue
        la = label_angle(d)
        just = {0: "left", 180: "right", 90: "left", 270: "right"}[la]
        if net in gl_nets:
            sheet.add(["global_label", Q(net), ["shape", "bidirectional"], ["at", sx, sy, la], ["fields_autoplaced"],
                       fnt(justify=just), ["uuid", uid("gl", comp["ref"], unit, px, py)],
                       ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", sx, sy, 0], fnt(size=1.0, hide=True)]])
        else:
            sheet.add(["label", Q(net), ["at", sx, sy, la], ["fields_autoplaced"],
                       fnt(justify=just + " bottom"), ["uuid", uid("lb", comp["ref"], unit, px, py)]])


def inst_extent(comp, unit, plist):
    name, s = lib_symbol(comp["sym"])
    rot = sym_rot(comp)
    x0, y0, x1, y1 = body_bbox(s, unit)
    c1 = xf(x0, y0, rot); c2 = xf(x1, y1, rot)
    left, right = min(c1[0], c2[0]), max(c1[0], c2[0])
    top, bottom = min(c1[1], c2[1]), max(c1[1], c2[1])
    if plist is None:
        return (-5, 5, -5, 5)
    for p in plist:
        n = comp["pins"].get(p["number"])
        if p["hidden"]:
            continue
        d = xd(outward(p["angle"]), rot)
        L = STUB + (text_len(n) if n and n != "GND" else 5.0)
        ex, ey = xf(p["x"], p["y"], rot)
        if d == (-1, 0): left = min(left, ex - L)
        if d == (1, 0): right = max(right, ex + L)
        if d == (0, -1): top = min(top, ey - L)
        if d == (0, 1): bottom = max(bottom, ey + L)
    top -= 3.5
    bottom += 4.5
    return (left, right, top, bottom)


def layout_sheet(sheet, insts, root_uuid, sheet_uuid, gl_nets):
    """Column flow: fill top-to-bottom, then next column. Try A3, A2, A1."""
    for paper, W, H in (("A3", 420.0, 297.0), ("A2", 594.0, 420.0), ("A1", 841.0, 594.0)):
        y0 = 55.0
        x, y, colw = 20.0, y0, 0.0
        pos, ok = [], True
        for (c, u, plist) in insts:
            l, r, t, b = inst_extent(c, u, plist)
            w, h = r - l + 8.0, b - t + 2.0
            if y + h > H - 40 and y > y0:
                x, y = x + colw, y0
                colw = 0.0
            pos.append((c, u, plist, x - l, y - t))
            y += h
            colw = max(colw, w)
            if x + w > W - 15:
                ok = False
                break
        if ok:
            break
    sheet.paper, sheet.width, sheet.height = paper, W, H
    for c, u, plist, X, Y in pos:
        place_symbol(sheet, c, u, plist, X, Y, root_uuid, sheet_uuid, gl_nets)


def title_block(title, sheet_no):
    return ["title_block", ["title", Q(f"{PROJECT} - {title}")], ["date", Q(DATE)], ["rev", Q(REV)],
            ["company", Q(COMPANY)],
            ["comment", 1, Q("PRELIMINARY - NOT VALIDATED - NOT FOR FABRICATION OR HIGH-CURRENT USE")],
            ["comment", 2, Q("Generated by KiCad/Generator/gen_schematic.py from design.py (single source)")],
            ["comment", 3, Q(f"Sheet {sheet_no:02d} of {len(D.SHEETS):02d}")],
            ["comment", 4, Q("Derived concepts from Arduino Spot Welder V4 (KaeptnBalu / Malectrics, GPL-3.0)")]]


SHEET_NOTES = {
    2: ["POWER INPUT: fused tap from P_BUS (F102 3 A at source + F1 T3.15A on board), TVS D3, inrush/limit R1,",
        "two diode-isolated hold-up banks: VHOLD_LOGIC (C1+C2 = 9 mF) and VHOLD_RELAY (C4+C5 = 14.7 mF).",
        "Reason: the RT1270 terminal voltage collapses to ~3 V during a weld (doc 03 section 3) - rails must not follow it.",
        "U2 7805 -> +5V_AUX (hardware references, HCT14, LEDs, buzzer). U6 MCP1700 -> +3V3 (OLED, MCP9804, I2C)."],
    3: ["MCU: Arduino Nano V3 in sockets. VIN <- VHOLD_LOGIC. Nano 5 V output (+5V_MCU) = ADC reference + NTC pull-up.",
        "D9 = GATE_CMD (Timer1 OC1A capable). All outputs are inputs (hi-Z) during reset/bootloader -> hardware pull-downs keep",
        "the weld OFF. The MCU is NOT the only means of ending a pulse (see sheet 09)."],
    4: ["GATE DRIVE: TC4422 (non-inverting) powered from VDRV (only present when E-STOP closed AND ARM on).",
        "POWER ASSEMBLY (off-board, 'exclude from board'): 6x IRLZ44N on copper busbars, 10R gate + 10k G-S per device,",
        "STPS3045CP free-wheel diode drain->P_BUS, 1000 uF + SMBJ24CA across P_BUS-SOURCE. Welding current NEVER flows on the PCB.",
        "Rating limited by MOSFET thermal stress: <=50 ms at ~300 A (doc 03 section 4). MOSFETs can FAIL SHORT: see sheet 05 + doc 04."],
    5: ["ISOLATION: K101 relay is closed before welding and opened only when no current flows (carry-only).",
        "Two-pole E-STOP (S102) and ARM (S103) chains remove relay-coil supply (pole A) and gate-driver supply (pole B) in hardware.",
        "F101 main fuse + S101 manual disconnect are the backstop for a shorted MOSFET. K101 ratings are UNKNOWN - provisional."],
    6: ["SENSING: five 33k/10k dividers (k = 4.30), 100 nF filters. During a pulse the firmware switches to the 1.1 V",
        "reference (4.6 mV/LSB at the input of the divider ~ 20 mV) to estimate V_DS and the battery sag.",
        "Current = V_DS / RDS(on) estimate (+-30 %), shown as 'EST.' only. No shunt in V1 (upgrade path in OPEN_ISSUES)."],
    7: ["UI: OLED on 3.3 V I2C (pull-ups to 3.3 V), EC11 encoder and ACK button through 74HCT14 Schmitt triggers with RC filters.",
        "Active buzzer via BC547, LEDs: FAULT (red), READY (green), ARMED (yellow, hardware on VDRV), 5V_AUX (green)."],
    8: ["TEMPERATURE: TH101 NTC on the drain bar (insulated) -> A6 (ratiometric). MCP9804 on board (I2C 0x18) for ambient/board.",
        "Firmware derates the maximum pulse with heatsink temperature and locks out at 60 C (latched)."],
    9: ["INTERLOCKS (independent of the MCU): GIN is a wired-AND node.",
        "U3A: pulse-length limiter. PL_CT charges from GATE_CMD through 68k/1uF; when it exceeds 0.6875 x 5 V the LM393 pulls GIN low.",
        "      Window 63-96 ms (Monte-Carlo, doc 03 sec. 8); firmware limit 50 ms. Reset through D8/R48 when GATE_CMD returns low.",
        "U3B: gate-drive UVLO. If VDRV < 8.0 V the LM393 pulls GIN low (prevents linear-mode operation of the MOSFETs).",
        "R45 22k pull-down: GIN low when the MCU is reset or unpowered. GATE_FB lets the firmware verify the effective command.",
        "Foot switch: pull-up + RC + Schmitt + firmware re-confirmation for the whole trigger delay (fixes reference finding)."],
    10: ["TEST POINTS for bench validation without the welding stage connected (see RELEASE_CHECKLIST.md).",
         "Mounting holes are isolated; use nylon spacers."],
}


def make_sheet_file(sheet, root_uuid, file_uuid, notes):
    libs = [embedded(f) for f in sorted(sheet.lib_ids)]
    # notes block
    y = 25.0
    for i, line in enumerate(notes):
        sheet.add(["text", Q(line), ["at", 20.0, snap(y + i * 3.5), 0], fnt(size=1.8 if i == 0 else 1.5, justify="left bottom", bold=(i == 0)),
                   ["uuid", uid("note", sheet.no, i)]])
    tree = ["kicad_sch", ["version", 20230121], ["generator", "eeschema"], ["uuid", file_uuid],
            ["paper", Q(sheet.paper)], title_block(sheet.title, sheet.no), ["lib_symbols"] + libs] + sheet.items
    if sheet.no == 1:
        tree.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
    return tree


def generate():
    root_uuid = uid("root-sheet")
    gl_nets = {n for n, shs in net_sheets().items() if n and (len(shs) > 1 or n in GLOBAL_ALWAYS)}
    gl_nets.discard("GND")
    sheets = {no: Sheet(no, stem, title) for no, stem, title in D.SHEETS}
    per_sheet = {}
    for c, u, sh, plist in instances():
        per_sheet.setdefault(sh, []).append((c, u, plist))
    os.makedirs(os.path.join(OUT, "Hierarchical_Sheets"), exist_ok=True)
    files = {}
    for no, stem, title in D.SHEETS[1:]:
        sh = sheets[no]
        sheet_uuid = uid("sheet-symbol", no)
        layout_sheet(sh, per_sheet.get(no, []), root_uuid, sheet_uuid, gl_nets)
        tree = make_sheet_file(sh, root_uuid, uid("sheet-file", no), SHEET_NOTES.get(no, []))
        files[f"Hierarchical_Sheets/{stem}.kicad_sch"] = tree
    # root sheet: sheet symbols + overview text
    root = sheets[1]
    root.paper = "A3"
    bx, by = 25.0, 150.0
    for i, (no, stem, title) in enumerate(D.SHEETS[1:]):
        col, row = i % 5, i // 5
        x, y = bx + col * 78.0, by + row * 45.0
        su = uid("sheet-symbol", no)
        root.add(["sheet", ["at", snap(x), snap(y)], ["size", 66.04, 30.48], ["fields_autoplaced"],
                  ["stroke", ["width", 0.1524], ["type", "solid"]], ["fill", ["color", 0, 0, 0, 0.0]],
                  ["uuid", su],
                  ["property", Q("Sheetname"), Q(stem), ["at", snap(x), snap(y - 0.7112), 0], fnt(justify="left bottom")],
                  ["property", Q("Sheetfile"), Q(f"Hierarchical_Sheets/{stem}.kicad_sch"), ["at", snap(x), snap(y + 31.0896), 0], fnt(justify="left top", hide=True)],
                  ["instances", ["project", Q(PROJECT), ["path", Q(f"/{root_uuid}"), ["page", Q(str(no))]]]]])
        root.add(["text", Q(title), ["at", snap(x + 2), snap(y + 15.24), 0], fnt(size=1.27, justify="left bottom"), ["uuid", uid("sheettitle", no)]])
    overview = [
        "DIY_SPOT_WELDER_V1 - SYSTEM OVERVIEW (Architecture C: MOSFET pulse switch + carry-only isolation relay + fuse + manual disconnect)",
        "",
        "  BT1 RT1270 (+) --F101 ANL--S101 DISCONNECT--+ P_BUS --K101 relay (carry-only)-- ELECTRODE+ ~~ workpiece ~~ ELECTRODE- --+ DRAIN_BUS",
        "                                              |                                                                      |",
        "                                              +--F102 3A--> J1 control board (hold-up banks, 7805, Nano, interlocks)   6x IRLZ44N",
        "                                              +--D101 STPS3045CP (free-wheel, cathode)  <--------- anodes ---------- DRAIN_BUS",
        "  BT1 (-) ==16 mm2== SOURCE bar = GND star point <-- control GND (J1.2, J3.2/J3.6) ------------------------------ sources",
        "",
        "  Safety layers that do NOT depend on the MCU:  F101 fuse | S101 disconnect | S102 E-STOP 2NC | S103 ARM 2NO | R45 default-off pull-down |",
        "                                                U3A pulse-length limiter (63-96 ms) | U3B gate-drive UVLO (8 V) | K101 opens when ARM chain opens.",
        "  Firmware layers: weld-enable state machine, latched faults, watchdog, stuck-on detection (battery sag / drain), thermal derating.",
        "",
        "  STATUS: PRELIMINARY. The welding source (RT1270) is NOT approved (estimated 200-390 A, 4x its datasheet max). K101 ratings unknown.",
        "  The control PCB contains no welding-current conductors. No manufacturing outputs are released. See OPEN_ISSUES.md / RELEASE_CHECKLIST.md.",
    ]
    for i, line in enumerate(overview):
        root.add(["text", Q(line), ["at", 20.0, snap(30 + i * 4.5), 0], fnt(size=1.6 if i else 2.2, justify="left bottom", bold=(i == 0)),
                  ["uuid", uid("ov", i)]])
    files["DIY_SPOT_WELDER_V1.kicad_sch"] = make_sheet_file(root, root_uuid, root_uuid, [])
    # strip unused lib_symbols on root (none)
    for rel, tree in files.items():
        with open(os.path.join(OUT, rel), "w", encoding="utf-8") as f:
            f.write(dumps(tree) + "\n")
    os.makedirs(os.path.join(OUT, "Libraries"), exist_ok=True)
    write_project_library(os.path.join(OUT, "Libraries", f"{LIBNAME}.kicad_sym"))
    return root_uuid, files


if __name__ == "__main__":
    ru, files = generate()
    for f in files:
        print("wrote", f)
