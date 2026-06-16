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

You can group runs in subfolders, e.g. `test/3d_coarse_run/run_.../`, by passing `--output-dir test/3d_coarse_run`.

---

## What’s inside each run

| Path | Contents |
|------|----------|
| `run_report.json` | Status, parsed parameters, log paths, figure paths |
| `run_report.md` | Case setup, simulation progress, agent trace |
| `figures/velocity_field.png` | Velocity magnitude (2D plane, or **3D z=0 slice**) |
| `figures/surface_pressure.png` | Cylinder surface Cp vs angle (mid-span for 3D) |
| `case/` | Generated OpenFOAM case |
| `case/log.*` | Solver step logs |
| `case/VTK/` | VTK output for ParaView / post-processing |

---

## Find the latest successful run

```bash
ls -td run_* */run_* 2>/dev/null | head -1
grep -l '"status": "completed"' run_*/run_report.json */run_*/run_report.json 2>/dev/null | tail -1
```

Open figures:

```bash
open "$(ls -td run_*/figures/velocity_field.png */run_*/figures/velocity_field.png 2>/dev/null | head -1)"
```

---

## Run a new case (different input)

```bash
conda activate cfd-agent-test
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock

export MPLCONFIGDIR=../test/.matplotlib
nl-cfd-solver --docker \
  "YOUR NEW PROMPT HERE" \
  --output-dir ../test
```

A **new** `run_*` folder appears alongside previous runs.

**3D example:**

```bash
nl-cfd-solver --docker \
  "三维，圆柱直径0.1米，雷诺数100，来流速度1米每秒。" \
  --span 0.5 \
  --output-dir ../test/3d_coarse_run
```

---

## Example completed run

**Prompt:** 圆柱直径0.1米，雷诺数100，来流速度1米每秒。

**Directory:** `run_20260612_231827/`

| Stage | Result |
|-------|--------|
| NL parse | D=0.1 m, Re=100, U=1 m/s, 2D |
| Case generation | ✅ |
| blockMesh → foamToVTK | ✅ (Docker) |
| Figures | ✅ |

---

## Other folders

| Item | Purpose |
|------|---------|
| `.matplotlib/` | Matplotlib cache (set via `MPLCONFIGDIR`) |
| `.crewai/` | CrewAI cache (optional; set via `CREWAI_STORAGE_DIR`) |
| `3d_coarse_run/` etc. | Optional grouped output from `--output-dir` |
| `stl_check/` | STL generation smoke test (if present) |
