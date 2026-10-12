# KiCad project — DIY_SPOT_WELDER_V1

* Open `DIY_SPOT_WELDER_V1.kicad_pro` in **KiCad 10** (Windows 11).
* The files use the **KiCad 7 file format** (schematic `20230121`, PCB `20221018`), because only KiCad 7 tools were available for checking in the cloud environment. KiCad 10 opens these files natively; **save once in KiCad 10** to upgrade them, then commit.
* Libraries are self-contained: `Libraries/DIY_SPOT_WELDER_V1.kicad_sym` and `Libraries/DIY_SPOT_WELDER_V1.pretty`, referenced through the project tables `sym-lib-table` and `fp-lib-table` (`${KIPRJMOD}`). Nothing is needed from the global libraries.
* 3D models point to `${KICAD10_3DMODEL_DIR}` (variable name unverified; OI-16).
* `Generator/` regenerates the schematic, netlist checks and preliminary PCB from `Generator/design.py`. Once you edit the PCB by hand, stop using the PCB stages of `generate_all.py`.
* Schematic style: generated, so connections are made with net labels at the pin stubs (electrically explicit, checked by netlist parity). You can tidy it in KiCad without changing connectivity.
* Off-board power-assembly symbols carry *exclude from board* (`on_board no`). Do not remove that flag, or "Update PCB" will try to place the MOSFETs, relay and fuse on the control board.
