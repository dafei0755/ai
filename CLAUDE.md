# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Intelligent Project Analyzer** is a LangGraph-based multi-agent system for analyzing design projects (interior design, product design, branding, etc.). It uses dynamic role selection, batch scheduling, and human-in-the-loop interactions to provide expert-level analysis from requirements gathering to quality review.

**Tech Stack:**
- Backend: Python 3.10+, LangGraph 0.2+, FastAPI, Redis
- Frontend: Next.js 14, React 18, TypeScript, React Flow
- LLM: OpenAI/Azure/DeepSeek/Gemini via LangChain
- Task Queue: Celery (for multi-user concurrency)

## Development Commands

### Starting Services

**Quick start (all services):**
```cmd
start_services.bat
```

**Backend only:**
```cmd
python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
```

**Frontend only:**
```cmd
cd frontend-nextjs
npm run dev
```

**Redis (required):**
```cmd
redis-server
```

**Celery worker (optional, for multi-user):**
```cmd
celery -A intelligent_project_analyzer.services.celery_app worker --loglevel=info --concurrency=4
```

### Testing

**Run all tests:**
```bash
pytest tests/
```

**Run specific test file:**
```bash
python tests/test_content_safety.py
python tests/test_workflow_fix.py
```

**Validate YAML configuration:**
```bash
python scripts/check_prompts.py
```

**Integration test (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/run_integration_test.ps1
```

### Frontend Development

**Install dependencies:**
```bash
cd frontend-nextjs
npm install
```

**Build for production:**
```bash
npm run build
```

**Lint:**
```bash
npm run lint
```

## Architecture Overview

### Core Workflow (16-Step Process)

The system uses LangGraph to orchestrate a stateful workflow with human-in-the-loop interactions:

```
User Input → Input Guard → Requirements Analyst → Domain Validator
→ Calibration Questionnaire (user interaction)
→ Requirements Confirmation (user interaction)
→ Project Director (role selection + task allocation)
→ Role & Task Unified Review (user interaction)
→ Quality Preflight → Batch Executor (3 batches)
→ Batch Aggregator → Challenge Detection
→ Result Aggregator → Report Guard → PDF Generator
→ User Question (optional follow-up)
```

### Key Architectural Patterns

**1. Dynamic Role System**
- Roles are defined in YAML (`config/roles/`) with V2-V6 hierarchy
- Project Director dynamically selects 3-8 expert roles based on project type
- Role selection uses keyword matching + jieba tokenization for Chinese text
- Roles are organized in dependency batches (V4 → V3 → V2)

**2. Batch Scheduling**
- 3-batch execution model: Batch 1 (V4 research) → Batch 2 (V3 experts) → Batch 3 (V2 director)
- Automatic topological sorting based on role dependencies
- Batch confirmations are auto-approved (no user intervention)
- Parallel execution within batches (future enhancement)

**3. Human-in-the-Loop Interactions**
- Uses LangGraph's `interrupt()` mechanism to pause workflow
- 4 interaction points: Calibration Questionnaire, Requirements Confirmation, Task Review, Follow-up Questions
- State persisted in Redis between interruptions
- Frontend polls `/api/analysis/status/{session_id}` for interaction prompts

**4. State Management**
- Central state: `ProjectAnalysisState` (TypedDict with reducers)
- State stored in Redis via `RedisSessionManager`
- Reducers handle concurrent updates: `merge_agent_results`, `merge_lists`, `take_max_timestamp`
- Session TTL: 72 hours (configurable via `SESSION_TTL_HOURS`)

**5. Multi-Modal File Processing**
- Supports: PDF, TXT, Word, Excel, images, ZIP
- File processor: `services/file_processor.py`
- Vision API integration: Google Gemini Flash for image analysis
- Files stored per-session: `data/uploads/{session_id}/`

**6. Quality Assurance**
- 4-stage review: Red Team (critique) → Blue Team (optimize) → Judge (score) → Client (final)
- Challenge detection: identifies must-fix vs should-fix issues
- Quality preflight: validates input completeness before batch execution
- Report guard: final safety check before PDF generation

### Directory Structure

```
intelligent_project_analyzer/
├── agents/                    # Agent implementations
│   ├── requirements_analyst.py    # Analyzes user requirements
│   ├── dynamic_project_director.py # Selects roles & allocates tasks
│   ├── agent_executor.py          # Generic expert executor
│   └── conversation_agent.py      # Follow-up Q&A agent
├── api/
│   ├── server.py              # FastAPI main server (WebSocket + REST)
│   └── client.py              # Python SDK
├── config/
│   ├── prompts/               # YAML prompt templates (20+ files)
│   ├── roles/                 # Role definitions (V2-V6)
│   └── role_selection_strategy.yaml
├── core/
│   ├── state.py               # ProjectAnalysisState definition
│   ├── types.py               # Type definitions
│   ├── prompt_manager.py      # Singleton prompt loader
│   └── role_manager.py        # Role loading & synthesis
├── interaction/nodes/         # Human-in-the-loop nodes
│   ├── calibration_questionnaire.py
│   ├── requirements_confirmation.py
│   ├── role_task_unified_review.py
│   └── user_question.py
├── report/
│   ├── result_aggregator.py   # LLM-driven result synthesis
│   ├── pdf_generator.py       # PDF rendering (FPDF)
│   └── text_generator.py
├── review/
│   ├── multi_perspective_review.py  # 4-stage review coordinator
│   └── review_agents.py
├── security/
│   ├── input_guard_node.py    # Content safety (Tencent API)
│   ├── domain_validator_node.py
│   └── report_guard_node.py
├── services/
│   ├── llm_factory.py         # LLM instantiation
│   ├── redis_session_manager.py
│   ├── file_processor.py      # Multi-modal file handling
│   ├── celery_app.py          # Celery configuration
│   └── followup_history_manager.py
├── workflow/
│   └── main_workflow.py       # LangGraph workflow orchestration (1700+ lines)
└── settings.py                # Pydantic Settings (env vars)

frontend-nextjs/
├── app/
│   ├── page.tsx               # Home (input form)
│   ├── analysis/[sessionId]/  # Workflow visualization
│   └── report/[sessionId]/    # Report display + follow-up
├── components/
│   ├── WorkflowDiagram.tsx    # React Flow diagram
│   ├── ConfirmationModal.tsx
│   └── RoleTaskReviewModal.tsx
├── lib/
│   ├── api.ts                 # API client
│   └── websocket.ts           # WebSocket client
└── types/
    └── index.ts               # TypeScript types
```

## Important Implementation Details

### YAML Configuration

**Prompt files** (`config/prompts/*.yaml`):
- Must use UTF-8 without BOM
- Use `|` block scalar for `system_prompt`
- Avoid embedded Markdown code blocks (```)
- Avoid unindented separators (`---`, `___`)

**Role files** (`config/roles/*.yaml`):
- Each role has: `name`, `role_id`, `keywords`, `system_prompt`
- Role IDs follow format: `{level}-{index}` (e.g., "2-1", "3-2")
- Keywords used for weighted role selection

### State Reducers

When multiple nodes update the same state field concurrently, use reducers:

```python
# In state.py
class ProjectAnalysisState(TypedDict):
    agent_results: Annotated[Dict[str, Any], merge_agent_results]
    selected_roles: Annotated[List[str], merge_lists]
    updated_at: Annotated[str, take_max_timestamp]
```

### Adding a New Agent

1. Create prompt file: `config/prompts/your_agent.yaml`
2. Implement agent class in `agents/your_agent.py`
3. Register in workflow: `workflow/main_workflow.py`
   - Add node: `workflow.add_node("your_agent", self._your_agent_node)`
   - Add edges: `workflow.add_edge("prev_node", "your_agent")`
4. Validate: `python scripts/check_prompts.py`

### WebSocket Protocol

**Connection:** `ws://localhost:8000/ws/{session_id}`

**Message types:**
- `status_update`: Workflow progress
- `node_update`: Node execution status
- `interaction_required`: User input needed
- `error`: Error occurred
- `completed`: Analysis finished

### Environment Variables

Key variables in `.env`:

```bash
# LLM Configuration
LLM__PROVIDER=openai
LLM__MODEL=gpt-4o-2024-11-20
OPENAI_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1  # Optional

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API
API_HOST=0.0.0.0
API_PORT=8000

# Session
SESSION_TTL_HOURS=72

# Vision API (optional)
GOOGLE_API_KEY=...
ENABLE_VISION_API=true
```

### Common Pitfalls

1. **Infinite loops in workflow:** Ensure routing functions return valid node names or `END`. Check `_route_after_*` functions.

2. **YAML parsing errors:** Use `|` for multi-line strings, avoid unindented `---` separators.

3. **State not persisting:** Verify Redis is running and `RedisSessionManager` is used (not `MemorySaver`).

4. **LLM SSL errors:** v3.5.1+ has built-in retry mechanism (3 attempts with exponential backoff).

5. **Prompt not found:** `PromptManager` is a singleton. First load caches all prompts. Check file paths in `config/prompts/`.

6. **Batch execution stuck:** Verify `batch_plan` in state has correct structure: `[{"batch_id": 1, "roles": [...], "dependencies": []}]`

7. **Frontend WebSocket disconnects:** Check CORS settings in `api/server.py`. Frontend auto-reconnects with exponential backoff.

## Testing Strategy

- **Unit tests:** Individual agent/node logic (`tests/test_*.py`)
- **Integration tests:** Full workflow execution (`tests/test_integration.py`)
- **Content safety:** Tencent API integration (`tests/test_content_safety.py`)
- **Regression tests:** Workflow fixes (`tests/test_workflow_fix.py`)

## Performance Considerations

- **PromptManager:** Singleton pattern, loads all prompts once (99.9% speedup)
- **Redis caching:** Session state cached, reduces DB queries
- **PDF generation:** FPDF native engine (10x faster than Playwright)
- **Celery:** Async task queue for multi-user concurrency
- **LLM retry:** 3 attempts with exponential backoff for SSL errors

## Debugging

**Logs:**
- API logs: `logs/api.log`
- Reports: `reports/project_analysis_*.txt`
- Debug: `data/debug/`

**Common debug commands:**
```bash
# Check Redis connection
redis-cli ping

# View session data
redis-cli GET "session:{session_id}"

# Monitor Celery tasks
celery -A intelligent_project_analyzer.services.celery_app flower

# Check LLM config
python scripts/check_llm_config.py
```

## Version History Notes

- **v7.1.3 (2025-12-06):** FPDF PDF generation (10x speedup), removed ZIP support
- **v7.0:** Multi-deliverable architecture, each deliverable shows responsible agent's output
- **v3.11:** Follow-up conversation mode, smart context management (up to 50 rounds)
- **v3.10:** JWT authentication, membership tiers
- **v3.9:** File preview, upload progress bar, ZIP support
- **v3.8:** Conversation mode, Word/Excel support
- **v3.7:** Multi-modal file upload, Google Gemini Vision
- **v3.6:** Smart follow-up questions (LLM-driven)
- **v3.5:** Expert proactivity protocol, unified task review, Next.js frontend

## Additional Resources

- LangGraph docs: https://langchain-ai.github.io/langgraph/
- FastAPI docs: https://fastapi.tiangolo.com/
- Next.js docs: https://nextjs.org/docs
- React Flow docs: https://reactflow.dev/
