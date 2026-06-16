# CFD 自然语言仿真工作流 — 项目规划

> 基于 `problem_description.md` 的产品原型实施计划。  
> 代码与运行环境位于 `Yijun_LocalTest/project/`。

---

## 1. 项目概述

### 1.1 目标

构建一个可运行的产品原型，使用户通过**自然语言**描述圆柱绕流参数，系统自动：

1. 解析并补全仿真参数（直径/半径、雷诺数、来流速度、流体类型等）
2. 生成完整 OpenFOAM 算例
3. 执行仿真并监控进度/收敛
4. 输出稳态流速场与圆柱表面压力场可视化结果

### 1.2 产品形态

| 层级 | 选择 | 理由 |
|------|------|------|
| 核心引擎 | Python 包 | 便于单元测试、模块化、CLI/Web 共用 |
| 交互入口 | CLI（主） + Streamlit Web（可选） | CLI 便于 CI/评测；Web 便于演示 |
| CFD 后端 | OpenFOAM（本地 subprocess） | 题目明确要求 OpenFOAM |
| NL 解析 | 规则 + 正则 + 单位换算（主）；LLM 可选增强 | 规则解析可 deterministic 单测；LLM 作 fallback |

### 1.3 物理与求解器选型（原型默认）

| 项目 | 默认值 | 说明 |
|------|--------|------|
| 维度 | 2D（`empty` 前后平面） | 网格简单、算得快，符合面试原型 |
| 雷诺数范围 | 40–500（层流） | 覆盖题目示例 Re=100/150/200 |
| 求解器 | `pimpleFoam`（瞬态层流）或 `simpleFoam`（稳态） | Re<200 可用层流；原型优先 `simpleFoam` 求稳态场以加快演示 |
| 网格 | `blockMesh` + 圆柱 `snappyHexMesh` 或纯 `blockMesh` 近似 | 首版用结构化 `blockMesh` + 圆柱障碍（snappyHexMesh 作为 Step 5 增强） |
| 流体 | 空气（ν≈1.5e-5 m²/s）/ 水（ν≈1e-6 m²/s） | 由用户指定或默认空气 |

**参数关系**（用于补全缺失量）：

```
Re = U * D / ν
D  = 2 * R
ν  = μ / ρ
```

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Input (NL / CLI / Web)                  │
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: NL Parser          → ParsedParams (diameter, Re, U, …) │
│  Step 2: Param Validator    → CompleteParams + follow-up prompts│
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: Case Generator     → OpenFOAM case directory (templates)│
│  Step 3b: Setup Review      → case config summary for user     │
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: Simulation Runner  → blockMesh → solver → postProcess │
│          Progress Monitor   → stream log, residuals, convergence│
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: Post-processor      → velocity field PNG, Cp curve PNG  │
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
                         outputs/ (figures, logs, case)
```

### 2.1 目录结构（`project/`）

```
project/
├── pyproject.toml              # 依赖与 pytest 配置
├── requirements.txt            # 可 pip install -r
├── README.md                   # 环境、OpenFOAM 版本、运行说明
├── src/
│   └── cfd_workflow/
│       ├── __init__.py
│       ├── models.py             # Pydantic 数据模型
│       ├── parser/
│       │   ├── __init__.py
│       │   ├── nl_parser.py      # 自然语言解析
│       │   └── units.py          # 单位识别与换算
│       ├── physics/
│       │   ├── __init__.py
│       │   └── parameters.py     # Re/U/D 互推、流体物性
│       ├── openfoam/
│       │   ├── __init__.py
│       │   ├── case_generator.py # Jinja2 渲染算例
│       │   ├── runner.py         # subprocess 调用 OpenFOAM
│       │   └── monitor.py        # 日志/残差监控
│       ├── postprocess/
│       │   ├── __init__.py
│       │   └── visualize.py      # matplotlib 出图
│       └── cli.py                # 命令行入口
├── templates/
│   └── cylinder_2d/              # OpenFOAM 模板 (Jinja2)
│       ├── system/
│       ├── constant/
│       └── 0/
├── tests/
│   ├── unit/
│   │   test_units.py
│   │   test_nl_parser.py
│   │   test_parameters.py
│   │   test_case_generator.py
│   │   test_monitor.py
│   │   └── test_visualize.py
│   └── integration/
│       └── test_end_to_end.py    # 需 OpenFOAM 环境
├── outputs/                      # 仿真结果（gitignore）
└── runs/                         # 生成的算例（gitignore）
```

---

## 3. 分步实施计划

每个 Step 遵循：**写单元测试 → 实现 → 测试通过 → 进入下一步**。

---

### Step 0 — 项目脚手架与环境

**目标**：初始化 Python 项目、配置测试框架、确认 OpenFOAM 可用。

**任务**：
- 创建 `project/` 目录结构与 `pyproject.toml`
- 配置 `pytest`, `pytest-cov`
- 编写 `scripts/check_openfoam.sh` 检测 `blockMesh`, `simpleFoam` 等命令
- 编写 `README.md` 环境说明（OpenFOAM v2312/v2406 等）

**需安装库**（Python）：

| 库 | 用途 |
|----|------|
| `pytest` | 单元测试框架 |
| `pytest-cov` | 覆盖率 |
| `pydantic` | 参数模型与校验 |
| `jinja2` | OpenFOAM 模板渲染 |

**系统依赖**（非 pip）：

| 依赖 | 用途 |
|------|------|
| OpenFOAM (≥ v2212) | CFD 求解 |
| `bash` / `subprocess` | 调用 OpenFOAM 工具链 |

**安装命令**：

```bash
cd Yijun_LocalTest/project
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# OpenFOAM: source /opt/openfoam*/etc/bashrc  (路径因安装方式而异)
```

**验收**：`pytest tests/unit -q` 可运行（即使全 skip）；`blockMesh -help` 有输出。

---

### Step 1 — 自然语言参数解析 (`parser/`)

**目标**：从中文/中英混合语句中提取 `diameter|radius`, `Re`, `velocity`, `fluid`。

**需实现函数**（及对应单测）：

| 函数 | 说明 |
|------|------|
| `parse_length(text) -> Quantity` | 识别米/厘米/毫米/m/cm/mm |
| `parse_reynolds(text) -> float | None` | "雷诺数100", "Re=100" |
| `parse_velocity(text) -> Quantity` | "流速2m/s", "来流速度1米每秒" |
| `parse_fluid(text) -> FluidType` | "空气", "水", "air", "water" |
| `parse_nl_input(text) -> ParsedParams` | 组合解析，返回结构化对象 |

**需安装库**：

| 库 | 用途 |
|----|------|
| `regex` 或标准库 `re` | 模式匹配 |
| `pint`（可选） | 物理量与单位换算；也可自写轻量 `units.py` |

**测试用例**（`tests/unit/test_nl_parser.py`）应覆盖 `problem_description.md` 中全部 4 条示例 plus 边界情况。

**验收**：4 条示例输入解析字段正确；缺失字段为 `None` 而非误解析。

---

### Step 2 — 参数校验与补全 (`physics/parameters.py`)

**目标**：将解析结果变为可仿真的完整参数集；缺信息时生成追问文案。

**需实现函数**：

| 函数 | 说明 |
|------|------|
| `fluid_properties(fluid) -> nu, rho` | 空气/水默认物性 |
| `complete_parameters(parsed) -> CompleteParams` | 用 Re/U/D 两两求第三个 |
| `validate_parameters(params) -> list[str]` | 返回错误列表 |
| `missing_fields_prompt(parsed) -> str | None` | 追问用户文案 |

**需安装库**：

| 库 | 用途 |
|----|------|
| `pydantic` | `CompleteParams` 模型 |
| `numpy` | 数值计算（可选，标准库 `math` 亦可） |

**测试要点**：
- 只给 Re + U → 自动算 D
- 只给直径 + Re → 自动算 U
- 直径 vs 半径表述一致
- Re 与 U/D 不一致时报 warning 或以 Re 为准（策略写进文档）

**验收**：所有纯逻辑单测通过，无 OpenFOAM 依赖。

---

### Step 3 — OpenFOAM 算例生成 (`openfoam/case_generator.py`)

**目标**：根据 `CompleteParams` 渲染 `templates/cylinder_2d/` 到 `runs/<run_id>/`。

**需实现函数**：

| 函数 | 说明 |
|------|------|
| `compute_domain_size(D, Re)` | 计算域大小、入口/出口位置 |
| `compute_nu_from_params(params)` | ν 写入 `transportProperties` |
| `render_case(params, output_dir)` | Jinja2 渲染全部文件 |
| `validate_case(output_dir)` | 检查必要文件存在 |

**生成文件清单**：
- `system/blockMeshDict`, `controlDict`, `fvSchemes`, `fvSolution`
- `constant/transportProperties`, `turbulenceProperties`（laminar）
- `0/U`, `0/p`
- `Allrun` 脚本

**需安装库**：

| 库 | 用途 |
|----|------|
| `jinja2` | 模板渲染 |
| `pathlib`（标准库） | 路径管理 |

**测试策略**：
- **单元测试**：mock 参数 → 渲染到 tmpdir → 断言文件存在、关键数值（如 `nu`, `U` inlet）正确
- 不调用 OpenFOAM

**验收**：给定 Re=100, D=0.1m, U=1m/s，生成的 `0/U` 与 `transportProperties` 数值一致。

---

### Step 4 — 仿真执行与进度监控 (`openfoam/runner.py`, `monitor.py`)

**状态**：✅ 已实现（2026-06-15）

**目标**： subprocess 调用 OpenFOAM；实时解析日志显示进度与收敛。

**需实现函数**：

| 函数 | 说明 | 状态 |
|------|------|------|
| `find_openfoam_env()` | 检测 OpenFOAM 环境变量/路径 | ✅ `runner.py` |
| `run_command(cmd, cwd, on_line)` | 流式执行并回调每一行日志 | ✅ `runner.py` |
| `run_simulation(case_dir, …)` | blockMesh → snappyHexMesh → simpleFoam → foamToVTK | ✅ `runner.py` |
| `parse_residuals(log_text)` | 提取最后若干步残差 | ✅ `monitor.py` |
| `is_converged(residuals, tol)` | 判断是否收敛 | ✅ `monitor.py` |
| `update_progress_from_line(…)` | 从日志行更新迭代/残差 | ✅ `monitor.py` |
| `format_progress_summary(…)` | CLI 单行进度输出 | ✅ `monitor.py` |
| `SimulationProgress` | dataclass：当前步、迭代、残差、状态 | ✅ `monitor.py` |

**Docker 路径**：`docker_runner.py` 改为逐步骤启动容器并流式输出（不再批量脚本），simpleFoam 阶段同样解析进度。

**对应 Agent**：`simulation_agent` 写入 `simulation_progress`、`converged`、`residuals` 到 report。

---

### Step 3b — 算例配置审查 (`agents/setup_review.py`, `build_case_config`)

**状态**：✅ 已实现（2026-06-15）— 对应 `problem_description.md` §2

**目标**：在求解前向用户展示完整算例配置摘要。

**流程位置**：`case_agent` → **`setup_review_agent`** → `simulation_agent`

**输出**：
- CLI：`=== OpenFOAM case configuration ===` 块（几何、网格、边界、流体、求解器）
- Report：`case_setup` JSON 字段 + Markdown `## Case setup` 节
- Dry-run：审查完成后设 `dry_run_complete`，跳过仿真

**需实现函数**：

| 函数 | 说明 |
|------|------|
| `build_case_config(params, max_iterations)` | 结构化算例摘要（几何/网格/BC/求解器） |
| `format_case_setup_lines(config)` | 人类可读 CLI 行列表 |

**验收**：dry-run 与 full run 均在 CLI 和 `run_report.md` 中可见算例配置摘要。

---

### Step 3c — 2D / 3D 维度支持（2026-06-15）

**状态**：✅ 已实现

**行为**：
- **2D（默认）**：`frontAndBack` + `empty`，z 方向 1 层单元（伪 2D）
- **3D**：有限长度圆柱，span 沿 z，`zMin`/`zMax` 为 slip 远场边界
- NL 解析：`三维`/`3D`、`柱长`/`跨度`、`N倍直径`；CLI：`--dimension 2d|3d`、`--span L`
- 3D 默认 **L = 10×D**；`setup_review` 输出 L/D 与 runtime 警告

**模板**：`templates/cylinder_2d/` 与 `templates/cylinder_3d/`

---

### Step 5 — 后处理与可视化 (`postprocess/visualize.py`)

**目标**：生成题目要求的两类图：

1. **稳态流速场** — 速度大小云图（整个计算域）
2. **圆柱表面压力场** — Cp 曲线或表面压力分布

**需实现函数**：

| 函数 | 说明 |
|------|------|
| `read_openfoam_field(case_dir, time, field)` | 读取 U/p（VTK 或 numpy） |
| `export_vtk(case_dir)` | 调用 `foamToVTK` 或 Python 读 mesh |
| `plot_velocity_magnitude(...)` | 流速云图 → PNG |
| `plot_surface_cp(...)` | 圆柱表面 Cp → PNG |
| `generate_report(case_dir, out_dir)` | 汇总输出 |

**需安装库**：

| 库 | 用途 |
|----|------|
| `matplotlib` | 2D 云图、曲线 |
| `numpy` | 数组运算 |
| `vtk` 或 `pyvista` | 读取 OpenFOAM/VTK 网格与场 |
| `foamlib` | 读写 OpenFOAM case（推荐，简化 mesh/field 读取） |

**安装命令**：

```bash
pip install matplotlib numpy pyvista foamlib
```

**测试策略**：
- **单元测试**：用小型 synthetic grid / fixture VTK 验证绘图函数不报错且输出文件存在
- 图像 snapshot 测试可选（不强求）

**验收**：`outputs/` 下生成 `velocity_field.png` 与 `surface_pressure.png`。

---

### Step 6 — CLI 与端到端编排 (`cli.py`)

**目标**：一条命令跑通全流程；支持交互式追问缺失参数。

**需实现**：

```bash
python -m cfd_workflow.cli run "圆柱直径0.1米，雷诺数100，来流速度1米每秒。"
python -m cfd_workflow.cli run --interactive
python -m cfd_workflow.cli run --dry-run  # 只解析+生成算例，不求解
```

**需安装库**：

| 库 | 用途 |
|----|------|
| `typer` 或 `click` | CLI 框架 |
| `rich` | 输出美化 |

**端到端检查清单**（对照 `problem_description.md`）：

- [ ] 4 条示例 NL 均能正确解析
- [x] 自动生成 OpenFOAM 算例（blockMesh + snappyHexMesh + 边界条件 + simpleFoam）
- [x] 算例配置摘要展示（setup_review_agent / case_setup）
- [x] 自动执行仿真并流式显示进度（迭代 + 残差）
- [x] 检测收敛（或达到 maxIter）
- [x] 输出流速场与表面压力可视化
- [ ] README 含 OpenFOAM 版本与运行说明

---

## 4. 测试策略（Test-First）

### 4.1 原则

1. **先写测试，再写实现** — 每个 Step 从 `tests/unit/test_*.py` 开始
2. **纯逻辑与 OpenFOAM 分离** — 单元测试不依赖 OpenFOAM；集成测试单独标记
3. **使用题目示例作为 golden tests** — 4 条 NL 示例为 parser 回归测试

### 4.2 pytest 配置（`pyproject.toml`）

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "openfoam: tests requiring OpenFOAM installation",
    "slow: long-running simulation tests",
}
pythonpath = ["src"]
```

### Conda 环境（推荐）

项目提供 `project/environment.yml`，环境名为 **`cfd-agent-test`**：

```bash
cd Yijun_LocalTest/project
conda env create -f environment.yml
conda activate cfd-agent-test
pytest tests/unit -v
```

# Phase B — 算例生成
pytest tests/unit/test_case_generator.py -v

# Phase C — 集成（需 OpenFOAM）
pytest tests/integration -v -m openfoam

# Phase D — 手动/CI 全流程
python -m cfd_workflow.cli run "圆柱直径0.1米，雷诺数100，来流速度1米每秒。"
```

### 4.4 各模块单测文件与覆盖目标

| 测试文件 | 覆盖函数 | 最少用例数 |
|----------|----------|------------|
| `test_units.py` | 长度/速度单位换算 | 8 |
| `test_nl_parser.py` | 4 条官方示例 + 半径/别名 | 12 |
| `test_parameters.py` | 参数补全、流体物性 | 10 |
| `test_case_generator.py` | 模板渲染、关键数值 | 6 |
| `test_monitor.py` | 残差解析、收敛判断 | 6 |
| `test_visualize.py` | 绘图输出文件存在 | 4 |

---

## 5. 依赖汇总

### 5.1 Python（`requirements.txt` / `pyproject.toml`）

```
# Core
pydantic>=2.0
jinja2>=3.1
numpy>=1.24
typer>=0.9
rich>=13.0

# Post-processing
matplotlib>=3.7
pyvista>=0.43
foamlib>=0.4

# Dev / Test
pytest>=7.4
pytest-cov>=4.1
```

### 5.2 系统

- **OpenFOAM** v2212 / v2312 / v2406（README 中固定一个主推版本）
- C++ 运行库（OpenFOAM 自带）
- 可选：**ParaView**（调试可视化，非必须）

---

## 6. 实施时间线（建议）

| 天数 | 内容 |
|------|------|
| Day 1 | Step 0 + Step 1 + Step 2 + 全部 unit tests |
| Day 2 | Step 3 模板与 case generator |
| Day 3 | Step 4 runner + 小网格集成测试 |
| Day 4 | Step 5 后处理 + Step 6 CLI |
| Day 5 | 端到端验证、README、示例输出、Web 可选 |
| Day 6–7 | 鲁棒性、更多 NL 表述、性能与文档 polish |

---

## 7. 风险与缓解

| 风险 | 缓解 |
|------|------|
| OpenFOAM 未安装或版本不一致 | `check_openfoam.sh` + README 明确版本；CI skip integration |
| 圆柱 snappyHexMesh 网格失败 | 首版用 cylinder 近似几何（blockMesh + cellSet）或预置网格 |
| 仿真时间过长 | 粗网格 + simpleFoam 稳态 + 限制 maxIter |
| NL 表述多样 | 规则解析 + 单元测试持续扩充；可选 LLM fallback |
| 后处理读 mesh 复杂 | 优先 `foamToVTK` + pyvista；foamlib 作备选 |

---

## 8. 下一步行动

1. ✅ 完成本 `planning.md`
2. ⬜ 创建 `project/` 脚手架（Step 0）
3. ⬜ 编写 Step 1–2 单元测试并实现 parser + physics
4. ⬜ 依次完成 Step 3–6，每步测试通过后推进
5. ⬜ 运行端到端流程并对照第 6 节检查清单

---
