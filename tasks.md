# Review fixes — branch: 829-epic-windows-installer

## Item 1: Commit spinit so the committed lib/ models actually load ✅
- `ngspice/share/ngspice/scripts/spinit` written with the real Spice64 content
- Verified empirically: ngspice auto-loads it from the bundled prefix; without it
  the engine prints "can't find the initialization file spinit"
- Bundled automatically: SpiceGUI.spec copies the whole `ngspice/` tree via `datas`,
  so `share/` lands in `_internal\ngspice\share\ngspice\scripts\` inside the bundle
- NO `--share`/`--sysconfdir` needed in the runner (and `--share` BREAKS it on
  Windows: "Permission denied"). Standard `../lib/ngspice` resolution is correct
  because ngspice chdir's to `<prefix>/share/ngspice` before loading spinit.
- `*.osdi` still needs `osdi_enabled` (spinit leaves it off by default); `*.cm`
  codemodels load when `xspice_enabled` is set.
- 7 ngspice integration tests pass with the bundled binary.

## Item 2: SHASUMS256.txt ✅
- All `lib/ngspice/*` (`*.osdi`, `*.cm`, `*.vpi`) + bin DLLs + vc_redist hashes

## Item 3 (non-blocking): Fix VC++ check ✅
- `IsVCRedistInstalled` only checks `Installed=1`; older 14.x runtime passes → our 14.44 not installed
- Simplest: always run vc_redist (exits harmlessly if newer already present)

## Item 4 (nit): README/spec nit on bundling location ✅
- SpiceGUI.spec + ngspice/README.md previously said models land "next to the app
  executable"; corrected to `_internal\ngspice\` (PyInstaller --onedir)
- Removed the stale "intentionally not bundled" row for `share/ngspice/scripts/`
  (it IS bundled now), and documented why.
