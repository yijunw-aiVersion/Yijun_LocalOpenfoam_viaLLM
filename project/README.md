# CFD Workflow Builder

Natural-language driven **2D cylinder flow** prototype using **OpenFOAM** (via Docker or local install).

**User guide (run from top to bottom):** [`../USER_GUIDANCE.md`](../USER_GUIDANCE.md)  
**Repo overview:** [`../README.md`](../README.md)

---

## Requirements

| Component | Version / notes |
|-----------|-----------------|
| Python | 3.11 (conda env `cfd-agent-test`) |
| OpenFOAM | **2412** — Docker image `opencfd/openfoam-default:2412` (recommended on macOS) |
| Docker | Colima + `docker-cli` (see below) |
| macOS extras | `qemu` via Homebrew when using Colima QEMU mode |

Solver pipeline: `blockMesh` → `snappyHexMesh` → `simpleFoam` → `foamToVTK`

---

## Agent architecture (CrewAI)

The pipeline uses **six stage agents** orchestrated by a **CrewAI Flow** (deterministic — no LLM API key required):

| Agent | Module | Responsibility |
|-------|--------|----------------|
| `parser_agent` | `agents/parser.py` | NL parsing |
| `physics_agent` | `agents/physics.py` | Parameter completion |
| `case_agent` | `agents/case.py` | OpenFOAM case generation |
| `simulation_agent` | `agents/simulation.py` | blockMesh → foamToVTK |
| `visualization_agent` | `agents/visualization.py` | PNG figures |
| `report_agent` | `agents/report.py` | JSON/MD reports + agent trace |

```
cli.py → workflow.py → crew/flow.py (CrewAI Flow)
                              ↓
                    agents/*.py (one agent per step)
                              ↓
              parser | physics | openfoam | postprocess (existing logic)
```

- **YAML roles:** `crew/config/agents.yaml`, `crew/config/tasks.yaml`
- **CrewAI tools:** `crew/tools.py` (wraps existing functions for future LLM mode)
- **Debug trace:** each run’s `run_report.md` includes an **Agent trace** section

Optional: `export CREWAI_STORAGE_DIR=../test/.crewai` for CrewAI cache on macOS.

---

## Environment setup

### 1. Create conda environment

```bash
cd Yijun_LocalOpenfoam_viaLLM/project
conda env create -f environment.yml
conda activate cfd-agent-test
```

`environment.yml` installs: Python 3.11, pydantic, jinja2, typer, pytest, matplotlib, pyvista, numpy, **crewai**.

### 2. Install Docker tooling (macOS, no local OpenFOAM)

```bash
conda activate cfd-agent-test
conda install -c conda-forge colima docker-cli -y
brew install qemu
```

### 3. Start Colima

Use **QEMU** on Apple Silicon (avoids macOS Virtualization entitlement issues):

```bash
colima start --cpu 4 --memory 8 --disk 40 --vm-type qemu --mount-type 9p
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock
```

Add the `export DOCKER_HOST=...` line to your shell profile if you use Colima regularly.

### 4. Pull OpenFOAM Docker image (first time)

```bash
docker pull opencfd/openfoam-default:2412
```

### 5. Verify installation

```bash
conda activate cfd-agent-test
cd Yijun_LocalOpenfoam_viaLLM/project

pytest tests/unit -v

export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock
docker run --rm opencfd/openfoam-default:2412 blockMesh -help | head -5
```

---

## Run the workflow

See [`../USER_GUIDANCE.md`](../USER_GUIDANCE.md) for prompts, result locations, and troubleshooting.

**Minimal end-to-end command:**

```bash
conda activate cfd-agent-test
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock

cd Yijun_LocalOpenfoam_viaLLM/project
export MPLCONFIGDIR=../test/.matplotlib
PYTHONPATH=src python -m cfd_workflow.cli --docker \
  "圆柱直径0.1米，雷诺数100，来流速度1米每秒。" \
  --output-dir ../test
```

**Or use the helper script:**

```bash
bash Yijun_LocalOpenfoam_viaLLM/project/scripts/run_docker_simulation.sh "YOUR PROMPT HERE"
```

---

## Where results go

Each run writes a timestamped directory under `--output-dir` (default: `../test/`):

```
test/run_YYYYMMDD_HHMMSS/
├── run_report.json
├── run_report.md
├── figures/velocity_field.png
├── figures/surface_pressure.png
└── case/          # OpenFOAM case + logs + VTK
```

Different prompts create **separate** `run_*` folders — nothing is overwritten.

---

## CLI reference

```bash
PYTHONPATH=src python -m cfd_workflow.cli [OPTIONS] "NATURAL LANGUAGE PROMPT"
```

| Option | Description |
|--------|-------------|
| `--docker` | Run OpenFOAM inside `opencfd/openfoam-default:2412` |
| `--output-dir PATH` | Output root (default: `../test`) |
| `--dry-run` | Parse + generate case only; skip solver and plots |

---

## Local OpenFOAM (optional)

If OpenFOAM is installed on your machine and on `PATH`, omit `--docker`:

```bash
source /usr/lib/openfoam/openfoam2412/etc/bashrc   # path varies by install
PYTHONPATH=src python -m cfd_workflow.cli \
  "圆柱直径0.1米，雷诺数100，来流速度1米每秒。" \
  --output-dir ../test
```

---

## Project layout

```
project/
├── src/cfd_workflow/
│   ├── cli.py                 # Typer CLI entry point
│   ├── workflow.py            # Delegates to CrewAI Flow
│   ├── agents/                # Stage agents (one per pipeline step)
│   ├── crew/                  # CrewAI Flow, tools, YAML config
│   ├── parser/                # Natural language parsing
│   ├── physics/               # Parameter completion
│   ├── openfoam/              # Case generator, local + Docker runners
│   └── postprocess/           # Velocity + Cp plots
├── templates/cylinder_2d/     # Jinja2 OpenFOAM templates
├── tests/unit/
├── scripts/
│   ├── run_docker_simulation.sh
│   ├── run_openfoam_docker.sh
│   └── setup_colima.sh
├── environment.yml
└── requirements.txt           # pip fallback (prefer conda env)
```

---

## Alternative: venv (parser/tests only)

OpenFOAM via Docker still recommended for full runs.

```bash
cd Yijun_LocalOpenfoam_viaLLM/project
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/unit -v
```
