# Natural Language → OpenFOAM CFD Workflow

End-to-end **2D cylinder flow** prototype: parse a natural-language prompt, generate an OpenFOAM case, run the solver (Docker or local), and produce velocity / surface-pressure figures.

Orchestration uses **CrewAI Flow** with **six stage agents** (deterministic — no LLM API key required for the default pipeline).

---

## Repository layout

```
Yijun_LocalOpenfoam_viaLLM/
├── README.md                 ← this file (structure + quick run)
├── USER_GUIDANCE.md          ← full setup, prompts, troubleshooting
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
│   ├── templates/cylinder_2d/  # Jinja2 OpenFOAM templates
│   ├── scripts/              # Colima + Docker helpers
│   ├── tests/unit/
│   ├── environment.yml
│   └── requirements.txt
└── test/                     ← runtime outputs (gitignored run_* folders)
    └── README.md
```

### Agent pipeline

```
prompt → parser_agent → physics_agent → case_agent
      → simulation_agent → visualization_agent → report_agent
```

Each run writes `test/run_YYYYMMDD_HHMMSS/` with `case/`, `figures/`, and `run_report.md` (includes **Agent trace** for debugging).

---

## Quick run

### 1. One-time setup

```bash
cd project
conda env create -f environment.yml
conda activate cfd-agent-test
conda install -c conda-forge colima docker-cli -y   # macOS Docker
brew install qemu                                   # Colima QEMU mode

colima start --cpu 4 --memory 8 --disk 40 --vm-type qemu --mount-type 9p
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock
docker pull opencfd/openfoam-default:2412
```

### 2. Run a simulation

```bash
conda activate cfd-agent-test
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock
export CREWAI_STORAGE_DIR=../test/.crewai
export MPLCONFIGDIR=../test/.matplotlib

cd project
PYTHONPATH=src python -m cfd_workflow.cli --docker \
  "圆柱直径0.1米，雷诺数100，来流速度1米每秒。" \
  --output-dir ../test
```

**Or use the helper script:**

```bash
bash project/scripts/run_docker_simulation.sh "YOUR PROMPT HERE"
```

### 3. Check results

The CLI prints the run directory. Open:

- `test/run_*/figures/velocity_field.png`
- `test/run_*/figures/surface_pressure.png`
- `test/run_*/run_report.md` — status + agent trace

```bash
ls -td test/run_* | head -1
```

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
| [USER_GUIDANCE.md](USER_GUIDANCE.md) | Environment, CLI options, example prompts, debugging |
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
