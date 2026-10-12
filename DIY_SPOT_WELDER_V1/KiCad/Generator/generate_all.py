#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Regenerate the complete KiCad project of DIY_SPOT_WELDER_V1 and the validation reports.

Requirements (Linux): KiCad 7.0.x (kicad-cli + pcbnew Python), Java 17+, xvfb-run,
Freerouting 1.9.0 jar (env FREEROUTING_JAR). Without Freerouting the board is left unrouted.

    python3 generate_all.py            # everything
    python3 generate_all.py --no-route # skip autorouting

WARNING: regenerating the PCB discards manual layout edits. Once the board is edited by hand in
KiCad 10, stop using the PCB stages of this script (schematic stages remain usable).
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KDIR = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(KDIR, ".."))
REP = os.path.join(ROOT, "Reports")
TMP = os.environ.get("GEN_TMP", "/tmp/diy_spot_welder_gen")
JAR = os.environ.get("FREEROUTING_JAR", "/tmp/claude-0/fr/freerouting.jar")


def run(cmd, **kw):
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, cwd=kw.pop("cwd", HERE), **kw)
    return r.returncode


def main():
    os.makedirs(TMP, exist_ok=True)
    py = sys.executable
    assert run([py, "gen_schematic.py"]) == 0
    assert run([py, "gen_project.py"]) == 0
    net = os.path.join(TMP, "DIY_SPOT_WELDER_V1.net")
    assert run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net,
                "DIY_SPOT_WELDER_V1.kicad_sch"], cwd=KDIR) == 0
    shutil.copy(net, os.path.join(REP, "Validation", "DIY_SPOT_WELDER_V1_kicad7_export.net"))
    rc = run([py, "check_schematic.py", net, os.path.join(REP, "ERC", "SCHEMATIC_CONNECTIVITY_CHECK.txt")])
    if rc:
        print("schematic check FAILED - stopping")
        return rc
    run(["kicad-cli", "sch", "export", "pdf", "-o", os.path.join(REP, "Validation", "DIY_SPOT_WELDER_V1_schematic.pdf"),
         "DIY_SPOT_WELDER_V1.kicad_sch"], cwd=KDIR)
    if run([py, "gen_pcb.py", "place"]) != 0:
        print("placement overflow - stopping")
        return 2
    if "--no-route" not in sys.argv and os.path.exists(JAR) and shutil.which("xvfb-run"):
        dsn, ses = os.path.join(TMP, "board.dsn"), os.path.join(TMP, "board.ses")
        run([py, "gen_pcb.py", "dsn", dsn])
        if os.path.exists(ses):
            os.remove(ses)
        with open(os.path.join(REP, "Validation", "FREEROUTING_LOG.txt"), "w") as log:
            run(["xvfb-run", "-a", "java", "-jar", JAR, "-de", dsn, "-do", ses, "-mp", "40"], cwd=TMP,
                stdout=log, stderr=subprocess.STDOUT)
        if os.path.exists(ses):
            run([py, "gen_pcb.py", "import", ses])
    run([py, "gen_pcb.py", "drc", os.path.join(REP, "DRC", "DRC_REPORT_KiCad7.txt")])
    return 0


if __name__ == "__main__":
    sys.exit(main())
