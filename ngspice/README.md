# Vendored ngspice

This directory holds a **vendored copy of the ngspice circuit engine** so the
SpiceGUI installer is self-contained and no system ngspice is required.

## Source

- Engine: **ngspice 47** from the system install at
  `C:\Program Files\Spice64` (the "Spice64" Windows port).
- License: **Modified BSD** (see `../../../licenses/NGSPICE-LICENSE.txt` in the
  repo, which is bundled into the PyInstaller distribution by `SpiceGUI.spec`).

## Layout (mirrors a normal ngspice install prefix)

```
ngspice/
├── bin/
│   ├── ngspice.exe              # core engine (batch mode: ngspice -b netlist -o out)
│   ├── libomp140.x86_64.dll     # OpenMP parallelism (runtime dep of the engine)
│   ├── samplerate.dll           # audio resampling   ── runtime deps
│   └── sndfile.dll              # audio file I/O     ── runtime deps
└── lib/
    └── ngspice/                 # transistor / model definitions loaded at runtime
        ├── *.osdi               # BSIM4/BSIMBulk/PSP/HICUM/EKV/etc. device models
        ├── *.cm                 # analog/digital/time-varying component macros
        └── *.vpi                # VPI (verilog-AMS) entry points
```

The `bin/` and `lib/` tree is placed by `SpiceGUI.spec` (via `datas`) next to
the app executable, so the runtime path resolution in
`app/simulation/ngspice_config.py` finds `ngspice/bin/ngspice.exe`.

## What is intentionally *not* bundled

| File / dir | Reason |
| --- | --- |
| `ngspice_con.exe` (7.3 MB) | Interactive console front-end; the runner uses batch mode. |
| `docs/` (PDF + text) | Reference docs, not needed at runtime. |
| `share/ngspice/scripts/` | tclspice console scripts, interactive only. |

## Verification

The bundled binary is behavior-equivalent to the system ngspice: it resolves
its DLLs from its own directory (works from any working directory), and the app's
integration tests pass against it:

```bash
PATH=ngspice/bin:$PATH make test   # or: uv run pytest app/tests/integration/
```

> Note: MOSFET/BJT `nmos`/`pnpm` lookups need an inline `.model` directive in the
> netlist — `app/simulation/netlist_generator.py` emits these (`model.py`), so the
> bundled engine's built-in generic models suffice for the app's default
> components. The `.osdi` model library provides the advanced device models for
> user-defined / SPICE-style models.

## Regenerating

Re-copy from a fresh ngspice/Spice64 install, then re-add this README. Do not
commit a different ngspice major version without updating the plan and testing
the integration suite.
