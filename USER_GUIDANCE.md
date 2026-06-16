# User Guide — Natural Language CFD Workflow

This guide explains how to run the **2D and 3D** cylinder-flow workflow from scratch, try **different natural-language inputs**, and **find your results**.

**Project code:** `Yijun_LocalOpenfoam_viaLLM/project/`  
**Default output folder:** `Yijun_LocalOpenfoam_viaLLM/test/`  
**Recommended CLI:** `nl-cfd-solver` (installed by `pip install -e .` in `project/`)

---

## Quick answer: where are my results?

Every run creates a **new timestamped folder** under the output directory (default: `test/`):

```
Yijun_LocalOpenfoam_viaLLM/test/
└── run_YYYYMMDD_HHMMSS/          ← one folder per run (never overwritten)
    ├── run_report.json           ← machine-readable summary (status, params, paths)
    ├── run_report.md             ← human-readable summary
    ├── figures/
    │   ├── velocity_field.png    ← velocity magnitude (2D or 3D z=0 slice)
    │   └── surface_pressure.png  ← cylinder surface Cp curve
    └── case/                     ← full OpenFOAM case
        ├── system/               ← blockMeshDict, controlDict, …
        ├── 0/                    ← initial U, p
        ├── constant/             ← transportProperties, cylinder.stl
        ├── VTK/                  ← ParaView / pyvista data (after foamToVTK)
        ├── log.blockMesh
        ├── log.snappyHexMesh
        ├── log.simpleFoam
        └── log.foamToVTK
```

After the CLI finishes, it prints:

```text
Status: completed
Run directory: .../test/run_20260612_231827
Dimension: 2d
Converged: True
Final residuals: U=9.12e-06, p=3.45e-06
Figure velocity_field: .../figures/velocity_field.png
Figure surface_pressure: .../figures/surface_pressure.png
```

**Different user input → different folder.**  
Example: run with Re=200 today and Re=100 tomorrow — you get `run_20260612_120000/` and `run_20260613_090000/` side by side. Compare them by opening each run’s `run_report.md` or `figures/`.

To find the **latest** run:

```bash
ls -td Yijun_LocalOpenfoam_viaLLM/test/run_* | head -1
```

---

## One-time setup (first time only)

Follow [`project/README.md`](project/README.md) for full details.

### macOS (validated)

```bash
# 1. Conda environment + CLI
cd Yijun_LocalOpenfoam_viaLLM/project
conda env create -f environment.yml
conda activate cfd-agent-test
pip install -e .                              # installs `nl-cfd-solver`

# 2. Docker tools (no local OpenFOAM install needed)
conda install -n cfd-agent-test -c conda-forge colima docker-cli -y
brew install qemu

# 3. Start Colima (QEMU mode — works on Apple Silicon without extra entitlements)
colima start --cpu 4 --memory 8 --disk 40 --vm-type qemu --mount-type 9p
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock

# 4. Pull OpenFOAM image (first run only; ~2 GB)
docker pull opencfd/openfoam-default:2412
```

Verify:

```bash
conda activate cfd-agent-test
nl-cfd-solver --help
docker ps
```

### Windows (not validated)

> **Note:** The maintainer develops on macOS only. The steps below mirror the macOS flow using **Docker Desktop** instead of Colima; they have **not been tested on Windows**.

```powershell
# 1. Conda environment + CLI (Anaconda Prompt or PowerShell after `conda init`)
cd Yijun_LocalOpenfoam_viaLLM\project
conda env create -f environment.yml
conda activate cfd-agent-test
pip install -e .

# 2. Docker Desktop for Windows (replaces Colima on macOS)
#    https://docs.docker.com/desktop/setup/install/windows-install/
#    Use the WSL 2 backend when prompted; start Docker Desktop and wait until it is running.

# 3. Optional: docker CLI via conda if `docker` is not on PATH
conda install -c conda-forge docker-cli -y

# 4. Pull OpenFOAM image (first run only; ~2 GB)
docker pull opencfd/openfoam-default:2412
```

Verify:

```powershell
conda activate cfd-agent-test
nl-cfd-solver --help
docker ps
```

On Windows you do **not** need `DOCKER_HOST`. Helper scripts under `project/scripts/` are bash-only — use PowerShell commands below or Git Bash / WSL.

After pulling code changes, refresh the CLI:

```bash
cd Yijun_LocalOpenfoam_viaLLM/project
pip install -e .
```

---

## Run end-to-end (recommended)

Use **`nl-cfd-solver`** from anywhere after setup (or `./nl-cfd-solver` from the repo root).

### Option A — helper script (macOS / bash only)

```bash
conda activate cfd-agent-test
bash Yijun_LocalOpenfoam_viaLLM/project/scripts/run_docker_simulation.sh \
  "我想模拟一个直径5厘米的圆柱，流速2m/s，雷诺数200。"
```

The script starts Colima if needed, pulls the Docker image, runs the workflow, and prints where output went. On Windows, use Option B (PowerShell) instead.

### Option B — manual commands (full control)

**2D — macOS / Linux / Git Bash:**

```bash
conda activate cfd-agent-test
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock   # macOS Colima only
export MPLCONFIGDIR=../test/.matplotlib
mkdir -p "$MPLCONFIGDIR"

nl-cfd-solver --docker \
  "圆柱直径0.1米，雷诺数100，来流速度1米每秒。" \
  --output-dir ../test
```

**3D (coarse mesh, good for first test) — macOS / Linux / Git Bash:**

```bash
nl-cfd-solver --docker \
  "三维，圆柱直径0.1米，雷诺数100，来流速度1米每秒。" \
  --span 0.5 \
  --max-iterations 200 \
  --output-dir ../test/3d_coarse_run
```

**Windows (PowerShell):**

```powershell
conda activate cfd-agent-test
$env:MPLCONFIGDIR = "..\test\.matplotlib"
New-Item -ItemType Directory -Force -Path $env:MPLCONFIGDIR | Out-Null
nl-cfd-solver --docker `
  "圆柱直径0.1米，雷诺数100，来流速度1米每秒。" `
  --output-dir ..\test
```

Change the quoted string to any supported prompt. Change `--output-dir` if you want results elsewhere.

**Fallback** (without `nl-cfd-solver` on PATH):

```bash
cd Yijun_LocalOpenfoam_viaLLM/project
PYTHONPATH=src python -m cfd_workflow.cli --docker "YOUR PROMPT" --output-dir ../test
```

---

## 2D vs 3D

| | 2D (default) | 3D |
|---|--------------|-----|
| **How to request** | Normal prompt (no dimension keyword) | Include `三维` or `3D` in the prompt, or pass `--dimension 3d` |
| **Cylinder span** | n/a | `--span L` in meters, or default **10× diameter** |
| **Mesh** | Standard background grid | **Coarse mesh by default** (faster); add `--fine-mesh` for finer 3D |
| **Runtime** | Shorter | Longer — especially with `--fine-mesh` or large span |
| **Velocity figure** | Full x–y plane | **z=0 mid-plane slice** (domain centered on z=0) |
| **Cp figure** | Full cylinder perimeter | Points near **mid-span** (z≈0) |
| **Interactive 3D** | n/a | Open `case/VTK/` in ParaView |

**Tip:** For a first 3D test, use a short span (`--span 0.5`) and the default coarse mesh. Increase `--max-iterations` if residuals in `run_report.md` have not reached `--residual-tol` (default `1e-5`).

---

## Example prompts

### 2D

| Prompt | Expected parse |
|--------|----------------|
| `圆柱直径0.1米，雷诺数100，来流速度1米每秒。` | D=0.1 m, Re=100, U=1 m/s, air, 2D |
| `我想模拟一个直径5厘米的圆柱，流速2m/s，雷诺数200。` | D=0.05 m, Re=200, U=2 m/s, 2D |
| `圆柱半径0.05m，Re=150，U=1.5m/s，流体是水。` | D=0.1 m, Re=150, U=1.5 m/s, water, 2D |
| `模拟空气绕过直径10cm的圆柱，速度3m/s。` | D=0.1 m, U=3 m/s, air (Re computed if needed), 2D |

### 3D

| Prompt | Expected parse |
|--------|----------------|
| `三维，圆柱直径0.1米，雷诺数100，来流速度1米每秒。` | 3D, D=0.1 m, Re=100, U=1 m/s, span=1.0 m (10×D) |
| `3D cylinder D=0.1m Re=100 U=1m/s span=0.5m` | 3D, span=0.5 m (English keywords also work) |
| `三维，柱长0.5米，直径0.1米，雷诺数100，来流1m/s` | 3D, span=0.5 m from 柱长 |

If required parameters are missing, the run stops early and `run_report.md` lists what to add.

Use `--dry-run` to check parsed dimension and case setup without running the solver:

```bash
nl-cfd-solver --dry-run \
  "三维，圆柱直径0.1米，雷诺数100，来流速度1米每秒。" \
  --span 0.5 \
  --output-dir ../test
```

---

## CLI options

```bash
nl-cfd-solver [OPTIONS] "YOUR PROMPT HERE"
```

| Option | Default | Purpose |
|--------|---------|---------|
| `--output-dir PATH` | `../test` | Root folder for timestamped `run_*` directories |
| `--docker` | off | Run OpenFOAM in Docker (use this on macOS/Windows without local OpenFOAM) |
| `--dry-run` | off | Parse + generate OpenFOAM case only; skip solver and plots |
| `--max-iterations N` | `200` | `simpleFoam` outer iterations (`controlDict` `endTime`) |
| `--residual-tol X` | `1e-5` | Stop early when U and p residuals ≤ X |
| `--dimension {2d,3d}` | infer from prompt | Override 2D/3D (omit to let the parser decide; defaults to 2D if unclear) |
| `--span L` | `10×` diameter (3D only) | Cylinder length along z in meters |
| `--coarse-mesh` | auto for 3D | Force coarse background mesh |
| `--fine-mesh` | off | Finer 3D mesh (slower; disables auto-coarse) |

**Longer simulation:**

```bash
nl-cfd-solver --docker --max-iterations 500 \
  "圆柱直径0.1米，雷诺数100，来流速度1米每秒。" \
  --output-dir ../test
```

**Parse / case only (no simulation):**

```bash
nl-cfd-solver --dry-run \
  "圆柱直径0.1米，雷诺数100，来流速度1米每秒。" \
  --output-dir ../test
```

Inspect generated files under `test/run_*/case/` without waiting for the solver.

---

## What to open after a successful run

| What you want | Where to look |
|---------------|---------------|
| Did it succeed? | `run_report.md` → **Status: completed** |
| Parsed parameters (2D/3D, span) | `run_report.json` → `"parameters"` or CLI summary lines |
| Case setup summary | `run_report.md` → **Case setup** (geometry, mesh, BCs, solver) |
| Convergence | `run_report.md` → **Simulation progress**; CLI prints `Converged` and `Final residuals` |
| Velocity plot | `figures/velocity_field.png` (3D: titled “z=0 mid-plane”) |
| Surface pressure (Cp) | `figures/surface_pressure.png` |
| Solver log | `case/log.simpleFoam` (last lines) |
| Mesh / snappy log | `case/log.blockMesh`, `case/log.snappyHexMesh` |
| 3D view in ParaView | `case/VTK/case_<iteration>/` (folder name matches final iteration) |
| **Per-agent debug trace** | `run_report.md` → **Agent trace** (status + timing per agent) |

### Viewing 3D results

1. **Quick look (automatic):** open `figures/velocity_field.png` — this is a **z=0 mid-plane** slice through the 3D domain (same view you would use for a 2D comparison).
2. **Full 3D (ParaView):** open `case/VTK/case_<N>.vtm` or the time folder under `case/VTK/`; slice, clip, or add streamlines interactively.
3. **Cp curve:** `surface_pressure.png` uses cylinder surface points near mid-span (z≈0).

---

## Debugging a single agent

Each pipeline step is owned by one agent under `project/src/cfd_workflow/agents/`:

| Agent | File | When it fails |
|-------|------|----------------|
| `parser_agent` | `agents/parser.py` | Missing diameter / Re / velocity in prompt |
| `physics_agent` | `agents/physics.py` | Invalid parameter combinations |
| `case_agent` | `agents/case.py` | Template or STL generation issues |
| `setup_review_agent` | `agents/setup_review.py` | Case config summary (informational) |
| `simulation_agent` | `agents/simulation.py` | OpenFOAM / Docker errors — check `case/log.*` |
| `visualization_agent` | `agents/visualization.py` | VTK path or pyvista issues |
| `report_agent` | `agents/report.py` | Report write issues |

Run only parse + case generation (skip solver) to isolate parser/case agents:

```bash
nl-cfd-solver --dry-run "YOUR PROMPT" --output-dir ../test
```

During a full run, the CLI streams **simulation progress** (iteration, residuals) from `simulation_agent`.

---

## Re-run an existing case (without re-parsing)

If you already have a generated case and only want to re-solve in Docker:

**macOS / bash:**

```bash
conda activate cfd-agent-test
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock

bash Yijun_LocalOpenfoam_viaLLM/project/scripts/run_openfoam_docker.sh \
  Yijun_LocalOpenfoam_viaLLM/test/run_20260612_231827/case
```

**Windows (PowerShell):** run the same `docker run` logic manually or use Git Bash / WSL with the script above. Ensure Docker Desktop is running; no `DOCKER_HOST` export needed.

Re-generate figures only (after VTK exists):

```bash
conda activate cfd-agent-test
cd Yijun_LocalOpenfoam_viaLLM/project
export MPLCONFIGDIR=../test/.matplotlib
PYTHONPATH=src python -c "
from pathlib import Path
from cfd_workflow.models import SimulationDimension
from cfd_workflow.postprocess.visualize import generate_report
case = Path('../test/run_20260612_231827/case')
out = Path('../test/run_20260612_231827/figures')
print(generate_report(case, out, u_inf=1.0, rho=1.225, dimension=SimulationDimension.TWO_D))
"
```

For 3D runs, pass `dimension=SimulationDimension.THREE_D`.

---

## Run unit tests

```bash
conda activate cfd-agent-test
cd Yijun_LocalOpenfoam_viaLLM/project
pytest tests/unit -v
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `nl-cfd-solver: command not found` | `cd project && pip install -e .` or use `./nl-cfd-solver` from repo root |
| `OpenFOAM not installed` / `blocked` | Add `--docker` or install OpenFOAM locally |
| `Docker CLI not found` | macOS: `conda install -c conda-forge colima docker-cli`; Windows: install [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) or `conda install -c conda-forge docker-cli` |
| Colima / Docker errors on macOS | Use QEMU: `colima start --vm-type qemu --mount-type 9p` and install `brew install qemu` |
| Docker errors on Windows (not validated) | Ensure Docker Desktop is running with WSL 2 backend; share the project drive in Docker Desktop **Settings → Resources → File sharing** if volume mounts fail |
| `bash: /opt/openfoam2412/etc/bashrc` in logs | Harmless Docker image warning; ignore if steps succeed |
| 3D prompt shows 2D in dry-run | Do not pass `--dimension 2d` unless you mean 2D; include `三维`/`3D` in the prompt or use `--dimension 3d` |
| Run completes but `Converged: False` | Increase `--max-iterations` or relax `--residual-tol`; check `run_report.md` final residuals |
| 3D run very slow | Default coarse mesh is intentional; avoid `--fine-mesh` until 2D/3D pipeline is validated |
| `simulation_failed` | Open the log file named in the CLI **Issue:** line (e.g. `case/log.blockMesh`) |
| `postprocess_failed` | Check `case/VTK/` exists; see `case/log.foamToVTK` |
| Matplotlib cache errors | Set `export MPLCONFIGDIR=../test/.matplotlib` |

---

## Related docs

- [`project/README.md`](project/README.md) — environment, dependencies, OpenFOAM version, CLI reference
- [`test/README.md`](test/README.md) — output folder conventions
- [`development_log.md`](development_log.md) — build history and design decisions
- [`problem_description.md`](problem_description.md) — original requirements
