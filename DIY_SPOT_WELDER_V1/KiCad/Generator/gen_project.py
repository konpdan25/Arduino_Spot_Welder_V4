# SPDX-License-Identifier: GPL-3.0-or-later
"""Write .kicad_pro, sym-lib-table, fp-lib-table and copy footprints into the project library."""
import json
import os
import re
import shutil

import design as D
from gen_schematic import uid, PROJECT, LIBNAME

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FP_SRC = os.environ.get("KICAD7_FOOTPRINT_DIR", "/usr/share/kicad/footprints")

# Net classes (control PCB). Welding current never flows on this PCB.
NETCLASSES = [
    dict(name="Default", clearance=0.2, track_width=0.25, via_diameter=0.8, via_drill=0.4, nets=[]),
    dict(name="Power", clearance=0.2, track_width=0.8, via_diameter=1.2, via_drill=0.6,
         nets=["GND", "VBAT_IN", "VBAT_F", "VTAP", "VHOLD_LOGIC", "VHOLD_RELAY", "VRELAY_ARM", "RELAY_COIL_N", "VDRV", "+5V_AUX"]),
    dict(name="Gate", clearance=0.25, track_width=0.6, via_diameter=1.0, via_drill=0.5,
         nets=["GATE_DRV", "GATE_OUT"]),
    dict(name="Sense", clearance=0.25, track_width=0.3, via_diameter=0.8, via_drill=0.4,
         nets=["DRAIN_BUS", "ELEC_POS", "NTC_HS"]),
]


def write_project():
    nc = []
    for c in NETCLASSES:
        nc.append({
            "bus_width": 12, "clearance": c["clearance"], "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
            "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "name": c["name"], "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
            "track_width": c["track_width"], "via_diameter": c["via_diameter"], "via_drill": c["via_drill"], "wire_width": 6})
    assignments = {}
    for c in NETCLASSES[1:]:
        for n in c["nets"]:
            assignments[n] = c["name"]
    sheets = [[uid("root-sheet"), ""]] + [[uid("sheet-symbol", no), stem] for no, stem, _ in D.SHEETS[1:]]
    pro = {
        "board": {
            "3dviewports": [],
            "design_settings": {
                "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.5,
                             "copper_text_size_v": 1.5, "copper_text_thickness": 0.3, "silk_line_width": 0.15,
                             "silk_text_size_h": 1.0, "silk_text_size_v": 1.0, "silk_text_thickness": 0.15},
                "rules": {"min_clearance": 0.2, "min_track_width": 0.25, "min_via_diameter": 0.6,
                          "min_through_hole_diameter": 0.3, "min_hole_to_hole": 0.25, "min_copper_edge_clearance": 0.5,
                          "min_hole_clearance": 0.25, "min_silk_clearance": 0.0, "solder_mask_to_copper_clearance": 0.0},
                "track_widths": [0.0, 0.3, 0.5, 0.8, 1.0, 1.5],
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.8, "drill": 0.4}, {"diameter": 1.2, "drill": 0.6}],
            },
            "layer_presets": [], "viewports": []},
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "erc": {"erc_exclusions": [], "meta": {"version": 0}, "pin_map": [], "rule_severities": {}},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 1},
        "net_settings": {"classes": nc, "meta": {"version": 3}, "net_colors": None,
                         "netclass_assignments": None,
                         "netclass_patterns": [{"netclass": v, "pattern": "^" + k.replace("+", "\\+") + "$"} for k, v in assignments.items()]},
        "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
        "schematic": {"annotate_start_num": 0, "drawing": {"default_line_thickness": 6.0, "default_text_size": 50.0,
                                                           "intersheets_ref_show": False, "label_size_ratio": 0.375,
                                                           "pin_symbol_size": 25.0, "text_offset_ratio": 0.15},
                      "legacy_lib_dir": "", "legacy_lib_list": [], "meta": {"version": 1},
                      "page_layout_descr_file": "", "plot_directory": "", "spice_adjust_passive_values": False,
                      "spice_external_command": "spice \"%I\"", "subpart_first_id": 65, "subpart_id_separator": 0},
        "sheets": sheets,
        "text_variables": {"PROJECT_STATUS": "PRELIMINARY - NOT VALIDATED"},
    }
    with open(os.path.join(OUT, f"{PROJECT}.kicad_pro"), "w") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")
    with open(os.path.join(OUT, "sym-lib-table"), "w") as f:
        f.write(f'(sym_lib_table\n  (lib (name "{LIBNAME}")(type "KiCad")(uri "${{KIPRJMOD}}/Libraries/{LIBNAME}.kicad_sym")'
                f'(options "")(descr "Project symbols (flattened copies of KiCad 7 library symbols)"))\n)\n')
    with open(os.path.join(OUT, "fp-lib-table"), "w") as f:
        f.write(f'(fp_lib_table\n  (lib (name "{LIBNAME}")(type "KiCad")(uri "${{KIPRJMOD}}/Libraries/{LIBNAME}.pretty")'
                f'(options "")(descr "Project footprints (copies of KiCad 7 library footprints)"))\n)\n')


def copy_footprints():
    dst = os.path.join(OUT, "Libraries", f"{LIBNAME}.pretty")
    os.makedirs(dst, exist_ok=True)
    used = sorted({c["fp"] for c in D.COMPONENTS if c["fp"]})
    for fp in used:
        lib, name = fp.split(":", 1)
        src = os.path.join(FP_SRC, lib + ".pretty", name + ".kicad_mod")
        text = open(src, encoding="utf-8").read()
        # 3D model paths: KiCad 10 installs its models under ${KICAD10_3DMODEL_DIR} (UNVERIFIED variable name;
        # if models do not show, set this path variable in Preferences > Configure Paths).
        text = text.replace("${KICAD7_3DMODEL_DIR}", "${KICAD10_3DMODEL_DIR}")
        with open(os.path.join(dst, name + ".kicad_mod"), "w", encoding="utf-8") as f:
            f.write(text)
    return used


if __name__ == "__main__":
    write_project()
    for u in copy_footprints():
        print("footprint", u)
