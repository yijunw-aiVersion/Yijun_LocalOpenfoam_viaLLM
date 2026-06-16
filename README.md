# Natural Language → OpenFOAM CFD Workflow

End-to-end **2D and 3D cylinder flow** prototype: parse a natural-language prompt, generate an OpenFOAM case, run the solver (Docker or local), and produce velocity / surface-pressure figures.

Orchestration uses **CrewAI Flow** with **seven stage agents** (deterministic — no LLM API key required for the default pipeline).

---

## Repository layout

```
Yijun_LocalOpenfoam_viaLLM/
├── README.md                 ← this file (structure + quick run)
├── USER_GUIDANCE.md          ← full setup, prompts, troubleshooting
├── nl-cfd-solver             ← repo-root CLI wrapper (optional)
├── problem_description.md    ← original project requirements
├── project/                  ← Python package + OpenFOAM templates
│   ├── src/cfd_workflow/
│   │   ├── cli.py            # CLI entry point
│   │   ├── workflow.py       # delegates to CrewAI Flow
│   │   ├── agents/           # one agent per pipeline step
│   │   ├── crew/             # Flow, tools, YAML agent config
│   │   ├── parser/           # NL parsing
│   │   ├── physics/          # parameter completion
│   │   ├── openfoam/         # case gen + local/Docker runners
│   │   └── postprocess/      # visualization
│   ├── templates/cylinder_2d/  # Jinja2 OpenFOAM templates (2D)
│   ├── templates/cylinder_3d/  # Jinja2 OpenFOAM templates (3D)
│   ├── scripts/              # Colima + Docker helpers
│   ├── tests/unit/
│   ├── environment.yml
│   └── requirements.txt
├── test/                     ← runtime outputs (gitignored run_* folders)
│   └── README.md
└── user_log/                 ← local development notes
```

### Agent pipeline

```
prompt → parser_agent → physics_agent → case_agent → setup_review_agent
      → simulation_agent → visualization_agent → report_agent
```

Each run writes `test/run_YYYYMMDD_HHMMSS/` with `case/`, `figures/`, and `run_report.md` (includes **case setup**, **simulation progress**, and **agent trace**).

---

## Quick run

### 1. One-time setup

#### macOS (validated)

```bash
cd project
conda env create -f environment.yml
conda activate cfd-agent-test
pip install -e .                                    # installs `nl-cfd-solver` CLI
conda install -c conda-forge colima docker-cli -y   # macOS Docker
brew install qemu                                   # Colima QEMU mode

colima start --cpu 4 --memory 8 --disk 40 --vm-type qemu --mount-type 9p
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock
docker pull opencfd/openfoam-default:2412
```

#### Windows (not validated)

> **Note:** The maintainer develops on macOS only. The steps below mirror the macOS flow using **Docker Desktop** instead of Colima; they have **not been tested on Windows**. If something fails, open an issue or see [USER_GUIDANCE.md](USER_GUIDANCE.md).

```powershell
# 1. Conda environment (Anaconda Prompt or PowerShell after `conda init`)
cd project
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

Verify on Windows:

```powershell
conda activate cfd-agent-test
nl-cfd-solver --help
docker ps
docker run --rm opencfd/openfoam-default:2412 blockMesh -help
```

On Windows you do **not** need `DOCKER_HOST` (Docker Desktop sets that up). The helper script `project/scripts/run_docker_simulation.sh` is bash-only — use the manual run commands below (PowerShell) or Git Bash / WSL.

### 2. Run a simulation

**Recommended CLI:** `nl-cfd-solver` (after `pip install -e .` in `project/`). From the repo root you can also use `./nl-cfd-solver`.

**2D example (macOS / Linux / Git Bash):**

```bash
conda activate cfd-agent-test
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock   # macOS Colima only
export CREWAI_STORAGE_DIR=../test/.crewai
export MPLCONFIGDIR=../test/.matplotlib

nl-cfd-solver --docker \
  "圆柱直径0.1米，雷诺数100，来流速度1米每秒。" \
  --max-iterations 200 \
  --output-dir test
```

**3D example (coarse mesh, auto-selected for 3D):**

```bash
nl-cfd-solver --docker \
  "三维，圆柱直径0.1米，雷诺数100，来流速度1米每秒。" \
  --span 0.5 \
  --max-iterations 200 \
  --output-dir test/3d_coarse_run
```

**Windows (PowerShell):**

```powershell
conda activate cfd-agent-test
$env:CREWAI_STORAGE_DIR = "..\test\.crewai"
$env:MPLCONFIGDIR = "..\test\.matplotlib"
nl-cfd-solver --docker `
  "圆柱直径0.1米，雷诺数100，来流速度1米每秒。" `
  --max-iterations 200 `
  --output-dir ..\test
```

Use `--max-iterations N` for longer runs. The solver **stops early** when U and p residuals fall below `--residual-tol` (default `1e-5`).

**Or use the helper script (macOS / bash only):**

```bash
bash project/scripts/run_docker_simulation.sh "YOUR PROMPT HERE"
```

**Fallback** (without installing the CLI entry point):

```bash
cd project
PYTHONPATH=src python -m cfd_workflow.cli --docker "YOUR PROMPT" --output-dir ../test
```

### 3. Check results

The CLI prints the run directory. Open:

- `test/run_*/figures/velocity_field.png` — 2D field, or **z=0 mid-plane slice** for 3D
- `test/run_*/figures/surface_pressure.png` — cylinder Cp (mid-span for 3D)
- `test/run_*/run_report.md` — status, case setup, convergence, agent trace
- `test/run_*/case/VTK/` — ParaView / interactive 3D view

```bash
ls -td test/run_* | head -1
```

---

## 2D vs 3D (at a glance)

| | 2D (default) | 3D |
|---|--------------|-----|
| **Prompt hint** | omit dimension, or `--dimension 2d` | `三维` / `3D` in prompt, or `--dimension 3d` |
| **Span** | n/a (single z-cell, empty BC) | `--span L` or default `10×` diameter |
| **Mesh** | fine background grid | **coarse by default** (use `--fine-mesh` for finer) |
| **Figures** | full x–y plane | velocity at **z=0**; Cp at mid-span |

See [USER_GUIDANCE.md](USER_GUIDANCE.md) for more prompts and CLI options.

---

## Tests

```bash
conda activate cfd-agent-test
cd project
pytest tests/unit -v
```

---

## More documentation

| Doc | Contents |
|-----|----------|
| [USER_GUIDANCE.md](USER_GUIDANCE.md) | Environment, CLI options, 2D/3D prompts, troubleshooting |
| [project/README.md](project/README.md) | Package details, agent architecture, dependencies |
| [test/README.md](test/README.md) | Output folder conventions |
| [problem_description.md](problem_description.md) | Interview / product requirements |

---

## Requirements summary

| Component | Version |
|-----------|---------|
| Python | 3.11 |
| OpenFOAM | 2412 (`opencfd/openfoam-default:2412` via Docker) |
| Orchestration | CrewAI Flow + stage agents |
| Solver | `blockMesh` → `snappyHexMesh` → `simpleFoam` → `foamToVTK` |
| Default iterations | 200 (`--max-iterations` to change) |
| Convergence | Early stop when residuals ≤ `1e-5` (`--residual-tol`) |
