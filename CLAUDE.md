# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

A natural language test case signal matching tool (自然语言测试用例信号匹配工具). It uses a DeepSeek/OpenAI-compatible LLM to match automotive test case descriptions (in Chinese natural language) against vehicle signal definitions from DBC files or Excel signal matrices.

## Running the Application

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Start the server (auto-opens browser at http://localhost:8000)
python start.py

# With options
python start.py --port 8000 --api-key sk-xxx --model deepseek-chat --base-url https://api.deepseek.com --no-browser
```

Configure `backend/.env` (see `backend/.env.example`):
```
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DATABASE_URL=sqlite:///./app.db
UPLOAD_DIR=./uploads
LOG_LEVEL=INFO
```

There are no build, lint, or test commands — the project has no test suite.

## Architecture

### Dual-Layer Design (Important)

There are two implementations:
- **`backend/server.py`** — the **active running server** (Flask, single file, all business logic lives here)
- **`backend/app/`** — a modular service layer (FastAPI + SQLAlchemy + Pydantic) that exists as a scaffold for future refactoring but is **not currently used**

When making changes, work in `backend/server.py`. The `backend/app/` modules (`signal_parser`, `case_parser`, `normalizer`, `retrieval`, `prompt_builder`) are reference implementations only.

### Data Flow

1. User uploads **signal file** (DBC or Excel) → signals parsed and stored in SQLite with a `signal_session_id`
2. User uploads **test case Excel** → cases parsed, stored with a `case_session_id`
3. **Match run**: for each test case step:
   - Semantic normalization (synonyms, position aliases, negation inversion, range expansion, enum mapping)
   - Candidate signal retrieval via fuzzy/semantic scoring
   - LLM prompt constructed and sent to DeepSeek API
   - Full audit trail (prompt, raw response, token usage, latency) persisted to SQLite
4. **Export**: results back-filled into original Excel, returned as download

### API Routes (all in `backend/server.py`)

| Route | Purpose |
|---|---|
| `POST /api/signals/parse` | Parse DBC or Excel signal matrix |
| `POST /api/cases/parse` | Parse test case Excel |
| `POST /api/match/run` | Run LLM-based matching |
| `POST /api/export/fill` | Export results back into Excel |
| `GET /api/prompts/preview` | Debug: preview a generated prompt |
| `GET /health` | Health check |

### Frontend

`frontend/index.html` is a single static HTML file (no framework, no build step) served directly by Flask. All UI logic is inline.

### Chinese Semantic Normalization

The normalizer handles automotive-domain Chinese semantics:
- Position equivalence: 主驾=左前, 副驾=右前
- Range expansion: 左侧 → 左前+左后
- Negation: 未打开 → 关闭
- Action synonyms: 开启/启动/激活 → 打开
- Enum mapping: 2档 → Level2, 最大 → highest level

### LLM Integration

Uses the `openai` Python SDK pointed at DeepSeek's endpoint. Any OpenAI-compatible provider works by changing `--base-url` and `--model`.
