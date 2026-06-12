# Test run outputs

This folder stores **one timestamped directory per workflow run**. Nothing here is overwritten when you try a new prompt.

**Full user guide:** [`../USER_GUIDANCE.md`](../USER_GUIDANCE.md)

---

## How runs are named

```
run_YYYYMMDD_HHMMSS/
```

Example: `run_20260612_231827/` = run started 2026-06-12 at 23:18:27 UTC.

The CLI prints the exact path when finished:

```text
Run directory: /path/to/Yijun_LocalOpenfoam_viaLLM/test/run_20260612_231827
```

---

## What’s inside each run

| Path | Contents |
|------|----------|
| `run_report.json` | Status, parsed parameters, log paths, figure paths |
| `run_report.md` | Short human-readable summary |
| `figures/velocity_field.png` | Velocity magnitude (2D slice) |
| `figures/surface_pressure.png` | Cylinder surface Cp vs angle |
| `case/` | Generated OpenFOAM case |
| `case/log.*` | Solver step logs |
| `case/VTK/` | VTK output for ParaView / post-processing |

---

## Find the latest successful run

```bash
ls -td run_* | head -1
grep -l '"status": "completed"' run_*/run_report.json | tail -1
```

Open figures:

```bash
open "$(ls -td run_*/figures/velocity_field.png | head -1)"
open "$(ls -td run_*/figures/surface_pressure.png | head -1)"
```

---

## Run a new case (different input)

```bash
conda activate cfd-agent-test
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock

cd Yijun_LocalOpenfoam_viaLLM/project
export MPLCONFIGDIR=../test/.matplotlib
PYTHONPATH=src python -m cfd_workflow.cli --docker \
  "YOUR NEW PROMPT HERE" \
  --output-dir ../test
```

A **new** `run_*` folder appears alongside previous runs.

---

## Example completed run

**Prompt:** 圆柱直径0.1米，雷诺数100，来流速度1米每秒。

**Directory:** `run_20260612_231827/`

| Stage | Result |
|-------|--------|
| NL parse | D=0.1 m, Re=100, U=1 m/s |
| Case generation | ✅ |
| blockMesh → foamToVTK | ✅ (Docker) |
| Figures | ✅ |

---

## Other folders

| Item | Purpose |
|------|---------|
| `.matplotlib/` | Matplotlib cache (set via `MPLCONFIGDIR`) |
| `stl_check/` | STL generation smoke test (if present) |
