# Vendored ngspice

This directory holds a **vendored copy of the ngspice circuit engine** so the
SpiceGUI installer is self-contained and no system ngspice is required.

## Source

- Engine: **ngspice 47** from the system install at
  `C:\Program Files\Spice64` (the "Spice64" Windows port).
- License: **Modified BSD** (see `../licenses/NGSPICE-LICENSE.txt` in the
  repo, which is bundled into the PyInstaller distribution by `SpiceGUI.spec`).

## Provenance & verification

The vendored files below are committed so the installer is self-contained. To
verify them later — e.g. if the original download link goes stale — compare the
recorded values against a fresh copy of the same files.

### ngspice engine (sha256)

ngspice 47, byte-identical to the official ngspice-47 release. Verify with
(`sha256sum -c` reads the entries as relative to `ngspice/`):

```bash
cd ngspice && sha256sum -c SHASUMS256.txt
```

| Path | SHA-256 |
| --- | --- |
| `ngspice/bin/ngspice.exe` | `fa4f083058c1799d9f6da7ae2a99e3034b7bb92d056095de7d2df59e6f627d49` |
| `ngspice/bin/libomp140.x86_64.dll` | `644c49149f8a5d9275a83e9331a0adbd14620f930190e985d30b842107123597` |
| `ngspice/bin/samplerate.dll` | `2e24802f94b584173de7358a5f26d3147226f417dcebeb69bee98994022483ce` |
| `ngspice/bin/sndfile.dll` | `4e3bd2de8e1485110eaebef8e1239471f73d608773831c323bf528e05645655e` |

### vc_redist.x64.exe (signature + version)

Microsoft Visual C++ 2015-2022 Redistributable (x64) v14.44.35211. A SHA-256
only proves "this exact file"; for vc_redist the authoritative check is the
Microsoft Authenticode signature:

- **SignatureStatus:** `Valid`
- **Signer:** `CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US`
- **File version:** `14.44.35211.0` (`Get-AuthenticodeSignature ../vc_redist/vc_redist.x64.exe`)

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
