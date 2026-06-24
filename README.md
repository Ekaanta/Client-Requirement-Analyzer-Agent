# AI Requirement Validation Platform

Compares software requirements against Figma designs using **Grok AI** and **n8n**, surfacing every UI/UX mismatch in a clean Streamlit dashboard.

---

## Architecture

```
Streamlit UI → FastAPI → n8n Webhook → Figma API + Grok AI → Structured Report
                ↑ (fallback: direct Figma + Grok if n8n unreachable)
```

## Folder Structure

```
requirement-validator/
├── backend/
│   ├── api/
│   │   ├── app.py            # FastAPI application factory
│   │   └── routes/
│   │       └── analyze.py    # POST /api/v1/analyze, GET /api/v1/health
│   ├── core/
│   │   ├── config.py         # Pydantic settings (env vars)
│   │   ├── exceptions.py     # Custom exception hierarchy
│   │   └── logging.py        # Structlog configuration
│   ├── models/
│   │   └── schemas.py        # Pydantic request/response models
│   └── services/
│       ├── figma_service.py  # Figma API client + design extractor
│       ├── grok_service.py   # Grok AI client + report builder
│       └── n8n_service.py    # n8n webhook trigger + fallback
├── frontend/
│   └── app.py                # Streamlit dashboard
├── n8n/
│   └── requirement_validator_workflow.json  # Import into n8n
├── tests/
│   └── test_core.py
├── run_backend.py
├── requirements.txt
└── .env.example
```

---

## Quick Start

### 1. Install dependencies

```bash
cd requirement-validator
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in:
#   GROK_API_KEY     — from console.x.ai
#   FIGMA_ACCESS_TOKEN — from figma.com/developers
#   N8N_WEBHOOK_URL  — after importing workflow into n8n
```

### 3. Set up n8n (optional but recommended)

```bash
# Run n8n with Docker
docker run -it --rm \
  -p 5678:5678 \
  -e GROK_API_KEY=your_key \
  -e FIGMA_ACCESS_TOKEN=your_token \
  n8nio/n8n

# Then:
# 1. Open http://localhost:5678
# 2. Import n8n/requirement_validator_workflow.json
# 3. Activate the workflow
# 4. Copy the webhook URL and set N8N_WEBHOOK_URL in .env
```

> **Note:** If n8n is not reachable, FastAPI will automatically fall back to calling Figma and Grok directly.

### 4. Start the backend

```bash
python run_backend.py
# OR
uvicorn backend.api.app:app --reload --port 8000
```

### 5. Start the frontend

```bash
streamlit run frontend/app.py
```

Open **http://localhost:8501**

---

## API Reference

### `POST /api/v1/analyze`

**Request:**
```json
{
  "requirements": "1. User can log in with email and password\n2. Dashboard shows recent orders...",
  "figma_url": "https://www.figma.com/file/XXXXXXXXX/Your-App"
}
```

**Response:**
```json
{
  "success": true,
  "report": {
    "overall_score": 68,
    "requirement_coverage": 72.5,
    "total_issues": 14,
    "critical_count": 2,
    "high_count": 5,
    "medium_count": 4,
    "low_count": 3,
    "ai_summary": "...",
    "issues": [...],
    "screens_found": [...],
    "components_found": [...]
  }
}
```

### `GET /api/v1/health`

Returns backend status and whether n8n is reachable.

---

## Analysis Categories

| Category | What's checked |
|----------|---------------|
| Requirement Coverage | Which requirements have no matching screen/component |
| Missing Screen | Screens mentioned in requirements but absent in design |
| Missing Component | Buttons, forms, inputs, modals, navigation |
| Missing State | Loading, empty, success, error states |
| Typography | Inconsistent fonts, sizes, weights |
| Color | Unexpected color usage outside the palette |
| Spacing | Alignment and layout issues |
| Responsive | Missing breakpoints or mobile screens |
| Accessibility | Missing labels, poor contrast |
| UI Consistency | Inconsistent naming or patterns |
| UX Problem | Flow issues, missing affordances |
| Business Logic | Requirements that conflict with design |
| Design Quality | Overall design quality issues |

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GROK_API_KEY` | xAI Grok API key | ✅ |
| `FIGMA_ACCESS_TOKEN` | Figma personal access token | ✅ |
| `N8N_WEBHOOK_URL` | n8n webhook URL | Optional |
| `N8N_API_KEY` | n8n API key for auth | Optional |
| `BACKEND_URL` | FastAPI URL (for Streamlit) | Optional |
| `GROK_MODEL` | Grok model name | Optional |
| `API_PORT` | FastAPI port (default 8000) | Optional |
| `LOG_LEVEL` | Logging level | Optional |
