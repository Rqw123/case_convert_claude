# 自然语言测试用例信号匹配工具

> 基于 DeepSeek 大模型的车控信号语义匹配工具，支持将自然语言测试用例与 DBC/Excel 信号矩阵进行智能匹配，并将结果回填到原始测试用例表格中导出。

---

## 功能特性

- **多格式信号源**：支持 `.dbc` 文件和 `.xls/.xlsx/.xlsm` Excel 信号矩阵
- **自然语言理解**：覆盖顺序颠倒、同义词、位置别名、范围展开、否定式/反义表达、枚举值语义等
- **全过程留痕**：所有中间数据（语义归一化、候选召回、Prompt、LLM 响应）全部落库，便于排查和调优
- **结果回填导出**：匹配结果自动回填原始 Excel，新增匹配状态、信号汇总、未匹配原因列
- **Web 界面**：无需安装前端框架，单 HTML 文件，拖拽上传，实时预览

---

## 快速开始

### 1. 安装依赖

```bash
# 获取依赖，若无，安装python: uv install python3.11.9
uv python list
# 创建虚拟环境并激活
uv venv
.venv\Scripts\activate
# 安装依赖
uv pip install -r .\backend\requirements.txt
```

### 2. 配置 API Key

```bash
# 编辑 backend/.env 文件
DEEPSEEK_API_KEY=sk-你的DeepSeek密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 3. 一键启动

```bash
python start.py
```

浏览器将自动打开 `http://localhost:8000`

**完整参数：**

```bash
python start.py --port 8000 --api-key sk-xxx --model deepseek-chat --base-url https://api.deepseek.com
```

---

## 使用流程

1. **上传信号文件**：拖入 DBC 或 Excel 信号矩阵，查看解析摘要
2. **上传测试用例**：拖入测试用例 Excel，预览识别到的用例列表
3. **配置模型参数**：确认 API Key、模型名称、温度值
4. **执行匹配**：点击"执行匹配"，等待结果
5. **查看 & 导出**：页面预览匹配结果，点击"导出回填 Excel"下载

---

## 目录结构

```
case_convert/
├── start.py                    # 一键启动脚本
├── README.md                   # 本文档
├── backend/
│   ├── server.py               # Flask 后端（单文件，含全部业务逻辑）
│   ├── .env                    # 环境变量（API Key 等）
│   ├── .env.example            # 环境变量模板
│   ├── requirements.txt        # Python 依赖
│   └── app/                    # 模块化服务层（供扩展使用）
│       ├── core/               # 配置、日志、数据库、异常
│       ├── models/             # SQLAlchemy ORM 模型
│       ├── schemas/            # Pydantic 数据模型
│       └── services/           # 信号解析、用例解析、归一化、召回、Prompt 构建
├── frontend/
│   └── index.html              # 单页前端（无需构建）
└── legacy/
    └── signal_extractor.py     # 原始信号解析脚本（迁移参考）
```

---

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/signals/parse` | 上传解析信号文件，返回 `signal_session_id` |
| POST | `/api/cases/parse` | 上传解析测试用例，返回 `case_session_id` |
| POST | `/api/match/run` | 执行匹配，返回全部匹配结果 |
| POST | `/api/export/fill` | 导出回填后的 Excel 文件 |
| POST | `/api/prompts/preview` | 预览指定用例的 Prompt（调试用） |
| GET  | `/health` | 健康检查 |

---

## 语义覆盖说明

| 语义类型 | 示例 |
|---|---|
| 位置等价 | 主驾=左前，副驾=右前 |
| 范围展开 | 左侧→左前+左后，全部→四个位置 |
| 否定转换 | 未打开→关闭，未关闭→打开 |
| 动作同义 | 开启/启动/激活 → 打开 |
| 枚举语义 | 2档→Level2，最大→最高等级，高档→High |
| 顺序颠倒 | "空调打开" = "打开空调" |

---

## 数据库说明

工具使用 SQLite（`backend/case_convert.db`）保存全过程数据，包含以下核心表：

- `match_task`：任务主表
- `case_semantics`：语义归一化结果（含展开步骤、否定模式、枚举映射）
- `case_candidate_signal`：候选信号召回结果（含命中原因和打分）
- `prompt_record`：构建的 Prompt 全文（含 hash）
- `llm_call_record`：LLM 原始请求与响应（含 token 用量、耗时）
- `case_match_result`：最终结构化匹配结果

排查问题时可直接用 SQLite 工具查询（如 [DB Browser for SQLite](https://sqlitebrowser.org/)）。

---

## 常见问题

**Q: 列名识别失败怎么办？**
支持的用例列名别名：`case_id / 用例编号 / 测试用例ID / 编号`，步骤列：`case_step / 测试步骤 / 步骤 / 用例描述`。

**Q: 信号匹配结果全部失败？**
优先检查 API Key 是否正确配置，可在 `backend/.env` 文件中设置 `DEEPSEEK_API_KEY`。

**Q: 支持其他模型吗？**
支持所有 OpenAI 兼容接口，修改 `--base-url` 和 `--model` 参数即可（如通义千问、智谱 AI 等）。

---

## 依赖

- Python 3.8+
- flask
- pandas
- openpyxl
