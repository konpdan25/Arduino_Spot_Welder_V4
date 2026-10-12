# SPDX-License-Identifier: GPL-3.0-or-later
"""
Generate the PRELIMINARY control PCB (DIY_SPOT_WELDER_V1.kicad_pcb) with the KiCad 7 pcbnew API.

Stages:
  place   - create board outline, load footprints from the project library, assign nets, place by zones
  dsn     - export Specctra DSN for Freerouting
  import  - import the Freerouting session (.ses), add GND pours on both layers, fill, save
  drc     - write KiCad DRC report (pcbnew.WriteDRCReport)

Welding current does NOT flow on this PCB. Power-assembly parts (on_board=False) are not placed.
The board is a 2-layer, 1.6 mm, 35 um copper control board.
"""
import os
import sys

import pcbnew

import design as D
from gen_schematic import uid, LIBNAME

HERE = os.path.dirname(os.path.abspath(__file__))
KDIR = os.path.normpath(os.path.join(HERE, ".."))
PCB = os.path.join(KDIR, "DIY_SPOT_WELDER_V1.kicad_pcb")
FPLIB = os.path.join(KDIR, "Libraries", f"{LIBNAME}.pretty")

OX, OY = 50.0, 50.0           # board origin in KiCad coordinates (mm)
BW, BH = 190.0, 140.0         # board size (mm)

mm = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


# fixed placements: ref -> (x, y, rotation_deg)
FIXED = {
    "H1": (4, 4, 0), "H2": (BW - 4, 4, 0), "H3": (4, BH - 4, 0), "H4": (BW - 4, BH - 4, 0),
    "J1": (6, 20, 90),
    "J3": (BW - 5, 22, 270), "J2": (BW - 5, 52, 270), "J4": (BW - 7, 78, 90),
    "U1": (96, 54, 90),
    "J6": (76, BH - 5, 90), "J7": (106, BH - 5, 90), "J5": (128, BH - 5, 0),
    "SW1": (136, BH - 12, 0), "BZ1": (150, BH - 18, 0),
}

# packing zones: name -> (x0, y0, x1, y1), list of sheets / explicit refs
ZONES = [
    ("POWER", (12, 9, 58, BH - 22), [2]),
    ("GATE_RELAY", (140, 9, BW - 14, 104), [4, 5]),
    ("INTERLOCK", (62, 9, 136, 42), [9, 8]),
    ("SENSE", (62, 66, 136, 92), [6, 3]),
    ("UI", (62, 94, 136, BH - 12), [7]),
    ("TESTPOINTS", (12, BH - 20, 58, BH - 2), [10]),
]


def load_fp(fpid):
    name = fpid.split(":", 1)[1]
    fp = pcbnew.FootprintLoad(FPLIB, name)
    if fp is None:
        raise SystemExit(f"footprint {name} not found in {FPLIB}")
    fp.SetFPID(pcbnew.LIB_ID(LIBNAME, name))
    return fp


def unit1_sheet(c):
    return c.get("unit_sheets", {}).get(1, c["sheet"])


def bbox_mm(fp):
    bb = fp.GetBoundingBox(False, False)
    return pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()), bb


def stage_place():
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(mm(1.6))
    board.SetCopperLayerCount(2)
    # outline
    corners = [(0, 0), (BW, 0), (BW, BH), (0, BH)]
    for i in range(4):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(P(*corners[i]))
        seg.SetEnd(P(*corners[(i + 1) % 4]))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        board.Add(seg)
    # nets
    nets = {}
    for c in D.COMPONENTS:
        if c["on_board"]:
            for n in c["pins"].values():
                if n and n not in nets:
                    ni = pcbnew.NETINFO_ITEM(board, n)
                    board.Add(ni)
                    nets[n] = ni
    fps = {}
    for c in D.COMPONENTS:
        if not c["on_board"] or not c["fp"]:
            continue
        fp = load_fp(c["fp"])
        fp.SetReference(c["ref"])
        fp.SetValue(c["value"])
        if c["ref"].startswith("H"):
            fp.Reference().SetVisible(False)
        sheet_uuid = uid("sheet-symbol", unit1_sheet(c))
        fp.SetPath(pcbnew.KIID_PATH(f"/{sheet_uuid}/{uid('sym', c['ref'], 1)}"))
        for pad in fp.Pads():
            num = pad.GetNumber()
            n = c["pins"].get(num)
            if n:
                pad.SetNet(nets[n])
        board.Add(fp)
        fps[c["ref"]] = (fp, c)
    # fixed
    for ref, (x, y, r) in FIXED.items():
        fp = fps[ref][0]
        fp.SetOrientationDegrees(r)
        fp.SetPosition(P(x, y))
        # center the bbox on the requested point
        w, h, bb = bbox_mm(fp)
        cx, cy = pcbnew.ToMM(bb.GetCenter().x) - OX, pcbnew.ToMM(bb.GetCenter().y) - OY
        fp.Move(pcbnew.VECTOR2I(mm(x - cx), mm(y - cy)))
    placed = set(FIXED)
    # zone packing (shelf algorithm)
    overflow = []
    for zname, (x0, y0, x1, y1), sheets in ZONES:
        members = [(ref, fp, c) for ref, (fp, c) in fps.items() if ref not in placed and unit1_sheet(c) in sheets]
        members.sort(key=lambda t: -bbox_mm(t[1])[1])
        x, y, shelf = x0, y0, 0.0
        for ref, fp, c in members:
            w, h, bb = bbox_mm(fp)
            if w > h * 1.6 and h < 6 and (x1 - x0) < w:     # very wide part in a narrow zone: rotate
                fp.SetOrientationDegrees(90)
                w, h, bb = bbox_mm(fp)
            gap = 1.2
            if x + w > x1:
                x, y = x0, y + shelf + gap
                shelf = 0.0
            if y + h > y1:
                overflow.append((zname, ref))
            cx, cy = pcbnew.ToMM(bb.GetCenter().x) - OX, pcbnew.ToMM(bb.GetCenter().y) - OY
            fp.Move(pcbnew.VECTOR2I(mm(x + w / 2 - cx), mm(y + h / 2 - cy)))
            x += w + gap
            shelf = max(shelf, h)
            placed.add(ref)
    missing = set(fps) - placed
    # silkscreen notes
    for i, line in enumerate(("DIY_SPOT_WELDER_V1  CONTROL PCB  rev A",
                              "PRELIMINARY - NOT VALIDATED - NOT FOR FABRICATION",
                              "NO WELDING CURRENT ON THIS BOARD")):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(line)
        t.SetPosition(P(14, 100 + i * 2.6))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(1.5), mm(1.5)))
        t.SetTextThickness(mm(0.2))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        board.Add(t)
    board.Save(PCB)
    # pcbnew.BOARD().Save() rewrites the .kicad_pro with defaults -> restore the project settings
    import gen_project
    gen_project.write_project()
    print(f"placed {len(placed)} footprints, overflow={overflow}, unplaced={sorted(missing)}")
    return 0 if not overflow and not missing else 2


def stage_dsn(dsn):
    board = pcbnew.LoadBoard(PCB)
    ok = pcbnew.ExportSpecctraDSN(board, dsn)
    print("DSN export", ok, dsn)


def add_zone(board, layer, net):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet(net))
    m = 0.6
    pts = [(m, m), (BW - m, m), (BW - m, BH - m), (m, BH - m)]
    ol = z.Outline()
    ol.NewOutline()
    for x, y in pts:
        ol.Append(mm(OX + x), mm(OY + y))
    z.SetLocalClearance(mm(0.4))
    z.SetMinThickness(mm(0.3))
    z.SetThermalReliefGap(mm(0.5))
    z.SetThermalReliefSpokeWidth(mm(0.6))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIsFilled(False)
    board.Add(z)
    return z


def import_ses(board, ses):
    """Minimal Specctra session importer (wires + vias). pcbnew.ImportSpecctraSES() needs the GUI board in KiCad 7."""
    import re as _re
    from sexpr import parse as _parse, find as _find, find1 as _find1
    t = _parse(open(ses).read())[0]
    routes = _find1(t, "routes")
    res = _find1(routes, "resolution")
    scale = 1.0 / (float(res[2]) * 1000.0)          # units -> mm  (um * res)
    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    ntrk = nvia = 0
    for net in _find(_find1(routes, "network_out"), "net"):
        ni = board.FindNet(str(net[1]))
        for w in _find(net, "wire"):
            path = _find1(w, "path")
            lay = layers[str(path[1])]
            width = float(path[2]) * scale
            co = [float(v) for v in path[3:]]
            pts = [(co[i] * scale, -co[i + 1] * scale) for i in range(0, len(co), 2)]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                tr = pcbnew.PCB_TRACK(board)
                tr.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
                tr.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
                tr.SetWidth(mm(width))
                tr.SetLayer(lay)
                tr.SetNet(ni)
                board.Add(tr)
                ntrk += 1
        for v in _find(net, "via"):
            m = _re.search(r"_(\d+):(\d+)_um", str(v[1]))
            dia, drill = (float(m.group(1)) / 1000, float(m.group(2)) / 1000) if m else (0.8, 0.4)
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(mm(float(v[2]) * scale), mm(-float(v[3]) * scale)))
            via.SetWidth(mm(dia))
            via.SetDrill(mm(drill))
            via.SetNet(ni)
            board.Add(via)
            nvia += 1
    return ntrk, nvia


def stage_import(ses):
    board = pcbnew.LoadBoard(PCB)
    for t in list(board.GetTracks()):
        board.Remove(t)
    for z in list(board.Zones()):
        board.Remove(z)
    print("SES import: tracks, vias =", import_ses(board, ses))
    add_zone(board, pcbnew.F_Cu, "GND")
    add_zone(board, pcbnew.B_Cu, "GND")
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.Save(PCB)


def stage_drc(report):
    board = pcbnew.LoadBoard(PCB)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    ok = pcbnew.WriteDRCReport(board, report, pcbnew.EDA_UNITS_MILLIMETRES, True)
    print("DRC report written", ok, report)


if __name__ == "__main__":
    st = sys.argv[1]
    if st == "place":
        sys.exit(stage_place())
    if st == "dsn":
        stage_dsn(sys.argv[2])
    if st == "import":
        stage_import(sys.argv[2])
    if st == "drc":
        stage_drc(sys.argv[2])
