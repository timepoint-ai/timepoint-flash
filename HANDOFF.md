# HANDOFF - TIMEPOINT Flash v2.0 Rebuild

**Status**: Phase 4 Complete ✅ | Phase 5 Ready to Start 🚀
**Date**: 2025-11-29
**Branch**: `main`

---

## What's Done

### Phase 1: Cleanup ✅
- GitHub cleanup complete
- v1.0 archived → `archive/v1-legacy` branch + `v1.0.0-legacy` tag
- Clean `main` branch with fresh start

### Phase 2: Core Infrastructure ✅
- `pyproject.toml` with all dependencies
- Provider abstraction (`app/core/providers.py`)
- Google Gen AI SDK integration
- OpenRouter API client
- LLM Router with capability-based routing
- Database with SQLite + PostgreSQL support
- FastAPI app with health endpoints

### Phase 3: Generation Pipeline ✅
- Temporal system (`app/core/temporal.py`)
- Generation schemas (`app/schemas/`)
- Prompt templates (`app/prompts/`)
- Generation pipeline (`app/core/pipeline.py`)
- API endpoints (`app/api/v1/timepoints.py`)

### Phase 4: Agent Rebuild ✅
- **10 agents implemented** with Mirascope-style patterns:
  1. `JudgeAgent` - Query validation and classification
  2. `TimelineAgent` - Temporal coordinate extraction
  3. `SceneAgent` - Environment and atmosphere
  4. `CharactersAgent` - Up to 8 characters
  5. `MomentAgent` - Plot/tension/stakes (NEW)
  6. `DialogAgent` - Up to 7 lines period dialog
  7. `CameraAgent` - Composition/framing (NEW)
  8. `GraphAgent` - Character relationships (NEW)
  9. `ImagePromptAgent` - Prompt assembly
  10. `ImageGenAgent` - Image generation (NEW)

- **New schemas** for Moment, Camera, Graph
- **New prompts** for Moment, Camera, Graph
- **Pipeline refactored** to use agent classes
- **202 tests passing** (all fast tests)

---

## Current State

**Repository Structure:**
```
timepoint-flash/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings with ProviderConfig
│   ├── models.py            # SQLAlchemy models
│   ├── database.py          # DB connection
│   ├── agents/              # NEW: All agent implementations
│   │   ├── base.py          # BaseAgent, AgentResult, AgentChain
│   │   ├── judge.py         # JudgeAgent
│   │   ├── timeline.py      # TimelineAgent, TimelineInput
│   │   ├── scene.py         # SceneAgent, SceneInput
│   │   ├── characters.py    # CharactersAgent, CharactersInput
│   │   ├── moment.py        # MomentAgent, MomentInput (NEW)
│   │   ├── dialog.py        # DialogAgent, DialogInput
│   │   ├── camera.py        # CameraAgent, CameraInput (NEW)
│   │   ├── graph.py         # GraphAgent, GraphInput (NEW)
│   │   ├── image_prompt.py  # ImagePromptAgent, ImagePromptInput
│   │   └── image_gen.py     # ImageGenAgent, ImageGenInput (NEW)
│   ├── core/
│   │   ├── providers.py     # LLMProvider base classes
│   │   ├── llm_router.py    # Capability-based routing
│   │   ├── pipeline.py      # GenerationPipeline (uses agents)
│   │   └── temporal.py      # TemporalPoint system
│   ├── schemas/             # Pydantic response models
│   │   ├── judge.py
│   │   ├── timeline.py
│   │   ├── scene.py
│   │   ├── characters.py
│   │   ├── moment.py        # NEW
│   │   ├── dialog.py
│   │   ├── camera.py        # NEW
│   │   ├── graph.py         # NEW
│   │   └── image_prompt.py
│   ├── prompts/             # Prompt templates
│   │   ├── judge.py
│   │   ├── timeline.py
│   │   ├── scene.py
│   │   ├── characters.py
│   │   ├── moment.py        # NEW
│   │   ├── dialog.py
│   │   ├── camera.py        # NEW
│   │   ├── graph.py         # NEW
│   │   └── image_prompt.py
│   └── api/v1/
│       └── timepoints.py    # API routes
├── tests/
│   ├── conftest.py
│   └── unit/
│       ├── test_agents/
│       │   ├── test_base.py
│       │   └── test_agents.py
│       ├── test_providers.py
│       ├── test_llm_router.py
│       ├── test_temporal.py
│       ├── test_schemas.py
│       └── test_pipeline.py
├── README.md
├── REFACTOR.md
├── HANDOFF.md
└── archive/
```

**Test Results:**
```bash
pytest -m fast    # 202 passed, 9 deselected in 4.04s
```

**Note:** Use Python 3.10 for tests due to SQLAlchemy compatibility:
```bash
python3.10 -m pytest -m fast -v
```

---

## Next: Phase 5 - API Completion

**Your Mission**: Complete API endpoints and add streaming support

### Tasks (see REFACTOR.md section 8.5 for details)

1. **Complete API Endpoints**
   - [ ] `POST /api/v1/timepoints/generate` - Full generation
   - [ ] `GET /api/v1/timepoints/{slug}` - Retrieve timepoint
   - [ ] `GET /api/v1/timepoints` - List timepoints (pagination)
   - [ ] `DELETE /api/v1/timepoints/{id}` - Delete timepoint

2. **Streaming Support**
   - [ ] `POST /api/v1/timepoints/generate/stream` - SSE streaming
   - [ ] Stream progress events for each pipeline step
   - [ ] Handle partial failures gracefully

3. **Image Generation Integration**
   - [ ] Integrate ImageGenAgent into API
   - [ ] Add `generate_image` parameter to endpoint
   - [ ] Store image data in database

4. **Error Handling**
   - [ ] Consistent error response format
   - [ ] Rate limiting responses
   - [ ] Validation error messages

5. **Segmentation Agent (Optional)**
   - [ ] Implement SegmentationAgent for character masks
   - [ ] Integrate with image generation pipeline

---

## Key Architecture Decisions

### Agent Pattern
All agents follow a consistent pattern:
```python
class ExampleAgent(BaseAgent[InputType, OutputType]):
    response_model = OutputType

    def get_system_prompt(self) -> str: ...
    def get_prompt(self, input_data: InputType) -> str: ...
    async def run(self, input_data: InputType) -> AgentResult[OutputType]: ...
```

### Input Dataclasses
Each agent has an Input dataclass with factory methods:
```python
@dataclass
class ExampleInput:
    query: str
    year: int
    # ...

    @classmethod
    def from_data(cls, ...) -> "ExampleInput": ...
```

### Pipeline Flow
```
Query → JudgeAgent → TimelineAgent → SceneAgent → CharactersAgent
                                                        ↓
ImageGenAgent ← ImagePromptAgent ← GraphAgent ← CameraAgent ← DialogAgent ← MomentAgent
```

---

## Quick Commands

```bash
# Install dependencies
pip install -e .

# Run fast tests (use Python 3.10)
python3.10 -m pytest -m fast -v

# Run integration tests (requires API keys)
python3.10 -m pytest -m integration -v

# Start FastAPI server
GOOGLE_API_KEY=your-key uvicorn app.main:app --reload

# Check health
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
```

---

## Important Notes

⚠️ **Use Python 3.10** - SQLAlchemy has issues with Python 3.14
⚠️ **Test coverage is excellent** - 202 unit tests passing
⚠️ **Pipeline is agent-based** - Cleaner than v1.0's inline methods
⚠️ **New agents** - Moment, Camera, Graph, ImageGen are v2.0 additions
⚠️ **Segmentation not implemented** - Optional for Phase 5

---

## Success Criteria (Phase 5)

✅ All CRUD endpoints working
✅ Streaming endpoint returns progress events
✅ Image generation integrated with API
✅ Error responses are consistent
✅ Rate limiting implemented
✅ All tests still passing

**Time Budget**: Week 5-6

---

**Next Handoff**: After Phase 5 complete → Phase 6 (Testing & Documentation)
