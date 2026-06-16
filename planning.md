# CFD 自然语言仿真工作流 — 项目规划

> 基于 `problem_description.md` 的产品原型实施计划。  
> 代码与运行环境位于 **`Yijun_LocalOpenfoam_viaLLM/project/`**（仓库根目录下的 `project/`）。

**相关文档（运行与维护）：**

| 文档 | 用途 |
|------|------|
| [`README.md`](README.md) | 仓库结构 + 快速运行 |
| [`USER_GUIDANCE.md`](USER_GUIDANCE.md) | 完整用户指南（安装 / 快速参考 / 2D·3D / 层流说明） |
| [`project/README.md`](project/README.md) | 包细节、Agent 架构、CLI 参考 |
| [`problem_description.md`](problem_description.md) | 原始需求 |

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
| 维度 | **2D 默认**；可选 **3D 有限长圆柱** | 2D：`empty` 前后平面；3D：span 沿 z，`zMin`/`zMax` slip |
| 雷诺数范围 | **40–1000（层流原型）** | 题目示例 Re=100/150/200；Re≳1000 仅作演示，非湍流物理 |
| 求解器 | **`simpleFoam` + `simulationType laminar`（固定）** | **不**根据 Re 自动切换湍流模型或 `pimpleFoam` |
| 网格 | `blockMesh` + `snappyHexMesh` | 3D 默认 **粗网格**（20×14×nz）；`--fine-mesh` 可选 |
| 流体 | 空气（ν≈1.5e-5 m²/s）/ 水（ν≈1e-6 m²/s） | 由用户指定或默认空气 |
| 收敛 | 残差 early-stop | 默认 `--residual-tol 1e-5`（U、p 初始残差） |

**Re 的作用（当前实现）**：补全 U / ν、写入 `transportProperties`、报告与校验；**不**改变求解器或湍流模型。Re > 10⁶ 校验拒绝。详见 `USER_GUIDANCE.md` → Solver and Reynolds number。

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

### 2.1 目录结构（`project/`）— 当前

```
project/
├── pyproject.toml              # 依赖 + nl-cfd-solver 入口点
├── environment.yml             # conda 环境 cfd-agent-test
├── README.md
├── src/cfd_workflow/
│   ├── cli.py                  # Typer CLI（nl-cfd-solver）
│   ├── workflow.py             # 委托 CrewAI Flow
│   ├── models.py
│   ├── agents/                 # 7 个 stage agents
│   ├── crew/                   # Flow, tools, YAML
│   ├── parser/
│   ├── physics/
│   ├── openfoam/               # case_generator, runner, docker_runner, monitor
│   └── postprocess/visualize.py
├── templates/
│   ├── cylinder_2d/
│   └── cylinder_3d/
├── tests/unit/
├── scripts/                    # Colima / Docker 辅助脚本
└── ...

仓库根目录：
├── nl-cfd-solver               # 可选 wrapper
├── test/                       # 运行输出 run_*（gitignore）
├── README.md, USER_GUIDANCE.md, planning.md
```

**编排**：CrewAI Flow，7 agents — `parser` → `physics` → `case` → **`setup_review`** → `simulation` → `visualization` → `report`（deterministic，默认无需 LLM API key）。

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

**Early-stop（2026-06-15）**：U、p 初始残差 ≤ `--residual-tol`（默认 `1e-5`）时终止 `simpleFoam`；CLI/report 输出 `converged`、`stopped_early`、`final residuals`。

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

### Step 3c — 2D / 3D 维度支持

**状态**：✅ 已实现（2026-06-15/16）

**行为**：
- **2D（默认）**：`frontAndBack` + `empty`，z 方向 1 层单元（伪 2D）
- **3D**：有限长度圆柱，span 沿 z，`zMin`/`zMax` 为 slip 远场边界；域中心 **z=0**
- NL 解析：`三维`/`3D`、`柱长`/`跨度`、`N倍直径`；CLI：`--dimension 2d|3d`（**默认 None**，从 prompt 推断，避免覆盖 NL 中的「三维」）
- 3D 默认 **L = 10×D**；`setup_review` 输出 L/D 与 runtime 警告
- **3D 粗网格（默认）**：background 约 20×14×5，snappy levels (1,2)，`maxGlobalCells` 120000；`--fine-mesh` 禁用 auto-coarse
- **3D 可视化**：流速 **z=0 中平面 slice**；Cp 取 mid-span 表面点；VTK 仍导出至 `case/VTK/` 供 ParaView

**模板**：`templates/cylinder_2d/` 与 `templates/cylinder_3d/`

**验收**：Docker 粗网格 3D 端到端跑通（例：`test/3d_coarse_run/run_*`）。

---

### Step 5 — 后处理与可视化 (`postprocess/visualize.py`)

**状态**：✅ 已实现（2026-06-15/16）

**目标**：生成题目要求的两类图：

1. **稳态流速场** — 速度大小云图（2D 全域；3D 为 z=0 中平面）
2. **圆柱表面压力场** — Cp 曲线（3D 为 mid-span）

| 函数 | 说明 | 状态 |
|------|------|------|
| `plot_velocity_magnitude(...)` | pyvista 读 VTK；3D 时 `slice` at z=0 | ✅ |
| `plot_surface_cp(...)` | 圆柱边界 Cp；3D 过滤 z≈0 | ✅ |
| `generate_report(...)` | 汇总 PNG 路径 | ✅ |

**实现要点**：`matplotlib` 使用 `Agg` 后端（无 GUI）；场数据来自 `foamToVTK` + **pyvista**（未用 foamlib）。

**验收**：`figures/velocity_field.png` 与 `figures/surface_pressure.png` 写入每次 run。

---

### Step 6 — CLI 与端到端编排 (`cli.py`)

**状态**：✅ 已实现（2026-06-15/16）

**入口**：
- **`nl-cfd-solver`** — `pip install -e .` 后 conda/PATH 可用；仓库根 `./nl-cfd-solver` 为 fallback wrapper
- 备选：`PYTHONPATH=src python -m cfd_workflow.cli`

**主要选项**：`--docker`, `--dry-run`, `--output-dir`, `--max-iterations`, `--residual-tol`, `--dimension`, `--span`, `--coarse-mesh`, `--fine-mesh`

**示例**：

```bash
nl-cfd-solver --docker "圆柱直径0.1米，雷诺数100，来流速度1米每秒。" --output-dir ../test
nl-cfd-solver --docker "三维，圆柱直径0.1米，雷诺数100，来流速度1米每秒。" --span 0.5 --output-dir ../test/3d_coarse_run
nl-cfd-solver --dry-run "..." --output-dir ../test
```

**端到端检查清单**（对照 `problem_description.md`）：

- [x] 4 条示例 NL 均能正确解析
- [x] 自动生成 OpenFOAM 算例（blockMesh + snappyHexMesh + 边界条件 + simpleFoam）
- [x] 算例配置摘要展示（setup_review_agent / case_setup）
- [x] 自动执行仿真并流式显示进度（迭代 + 残差）
- [x] 检测收敛（early-stop 或达到 maxIter）
- [x] 输出流速场与表面压力可视化
- [x] 2D + 3D 支持；3D 粗网格默认
- [x] README / USER_GUIDANCE / project/README 运行说明（含 nl-cfd-solver、层流 Re 说明）
- [ ] Streamlit Web（可选，未做）
- [ ] 湍流 Re 自动切换 RANS（**刻意不做**；见 §1.3 与 USER_GUIDANCE）

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
cd Yijun_LocalOpenfoam_viaLLM/project
conda env create -f environment.yml
conda activate cfd-agent-test
pip install -e .
pytest tests/unit -v
```

# Phase B — 算例生成
pytest tests/unit/test_case_generator.py -v

# Phase C — 集成（需 OpenFOAM）
pytest tests/integration -v -m openfoam

# Phase D — 手动/CI 全流程
nl-cfd-solver --docker "圆柱直径0.1米，雷诺数100，来流速度1米每秒。" --output-dir ../test
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

- **OpenFOAM** **2412** — Docker 镜像 `opencfd/openfoam-default:2412`（macOS Colima + Windows Docker Desktop）
- 可选：**ParaView** — 打开 `case/VTK/` 做交互 3D 查看

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

## 8. 下一步行动（维护 / 扩展）

**原型交付（当前）** — 已基本完成 Step 0–6 + 3b/3c；单元测试通过；2D/3D Docker 端到端验证。

**可选后续（未实现）**：

| 优先级 | 项 | 说明 |
|--------|-----|------|
| 低 | Streamlit Web | 演示用 UI |
| 低 | `--viz-slice-z` / 多 z 截面 | 短 L/D 圆柱端效应对比 |
| 中 | 高 Re 警告（代码内） | 文档已说明；可在 `parameter_warnings()` 加 Re 阈值提示 |
| 大 | 湍流 RANS 分支 | k-ω SST + 壁面网格 + 可能 `pimpleFoam` 非定常；超出当前原型范围 |
| 低 | 3D `--fine-mesh` 全量 Docker 测试 | 耗时长 |
| 低 | Windows 实机验证 | 文档已标注 not validated |

---

## 9. 实施进度记录

> 供日后查阅的设计决策与里程碑；按时间倒序。

### 2026-06-16 — 文档与层流说明

- **USER_GUIDANCE.md**：Quick reference（每会话） vs First-time installation（每台机器）分离；层流-only / Re 不自动切换湍流说明；示例 prompt 表
- **README.md**：与 USER_GUIDANCE 对齐；`nl-cfd-solver` 为主入口
- **planning.md**：本节进度记录 + 状态同步（本更新）

### 2026-06-15/16 — 3D + 粗网格 + 可视化

- 新增 `templates/cylinder_3d/`；parser 识别 `三维`/`3D`/span；`--dimension` 默认 **None**（修复 NL 三维被 CLI 默认 2d 覆盖）
- 3D **默认粗网格**；`resolve_coarse_mesh()`；CLI `--coarse-mesh` / `--fine-mesh`
- 3D 后处理：velocity z=0 slice；Cp mid-span；ParaView VTK 仍导出
- Docker 粗网格 3D 跑通：`test/3d_coarse_run/run_*`

### 2026-06-15 — 稳定性 + 可观测性 + CLI

- **macOS 修复**：matplotlib `Agg`；CrewAI `tracing=False` / 抑制 trace 交互提示
- **setup_review_agent**：算例配置摘要（problem §2）
- **monitor.py**：流式进度、残差解析、`--residual-tol` early-stop
- **nl-cfd-solver** 入口点；`docker_runner` 逐步容器执行
- CrewAI Flow 7 agents 编排

### 2026-06-12 前后 — 核心 Step 0–5

- NL parser、physics 补全、case_generator（2D）、runner、visualize、report
- 题目 4 条示例 NL golden tests
- Colima + OpenFOAM 2412 Docker 路径

### 刻意不做（记录备查）

- **Re 高 → 自动湍流**：始终 `simpleFoam` + `laminar`；Re 仅用于 ν/U。湍流需单独 Phase。
- **LLM 解析默认路径**：规则解析为主；CrewAI agents 为 deterministic wrapper。

---

## 10. 历史规划项（Step 0–3 初版）

以下保留原 Step 0–3 规划细节供参考；实现状态见 §9。

1. ✅ 完成本 `planning.md`
2. ✅ 创建 `project/` 脚手架（Step 0）
3. ✅ Step 1–2 单元测试 + parser + physics
4. ✅ Step 3–6 + 3b/3c
5. ✅ 端到端流程 + 文档

---
