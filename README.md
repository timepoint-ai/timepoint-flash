# Social Sim Monolith

A minimal, self-contained LLM-driven social network simulator. Takes a scenario → generates 3-step simulation → outputs network graph visualizations + JSON.

## Quick Start

```bash
chmod +x init.sh
./init.sh
source .venv/bin/activate
python monolith.py "US Constitutional Convention"
```

Results in `outputs/YYYYMMDD_HHMMSS/` with PNG graphs + JSON data.

## Setup (Detailed)

### 1. Get API Key (Free)

1. Go to https://openrouter.ai/keys
2. Sign up or log in
3. Copy your key (starts with `sk-or-v1-`)

### 2. Install

```bash
chmod +x init.sh
./init.sh
```

This creates `.venv/`, installs deps, makes `outputs/` and `data_files/` directories.

### 3. Configure

```bash
cp .env.example .env
# Edit .env, replace with your actual key
# OR just export: export OPENROUTER_API_KEY="sk-or-v1-..."
```

The `.env` file should look like:
```
OPENROUTER_API_KEY=sk-or-v1-25c016ef...
```

### 4. Run

```bash
source .venv/bin/activate
python monolith.py "Your scenario here"
```

Add `-v` for verbose logging:
```bash
python monolith.py "Your scenario here" -v
```

## Examples

```bash
python monolith.py "US Constitutional Convention"
python monolith.py "Fall of Rome"
python monolith.py "Scientific Revolution"
python monolith.py "Moon landing race"
python monolith.py "Internet development"
```

## Output Structure

Each run creates a timestamped folder:

```
outputs/20251106_185430/
├── step_0.png
├── step_1.png
├── step_2.png
└── simulation.json
```

And a disposable database:
```
data_files/sim_20251106_185430.db
```

## What It Does

1. **Parse input**: Your scenario as a string
2. **Initialize**: 5-node NetworkX graph, SQLite DB
3. **Run LLM loop** (3 steps):
   - Send current graph + scenario to LLM (OpenRouter)
   - LLM returns JSON: `{"interactions": [...], "states": [...]}`
   - Apply changes to graph
   - Render PNG with node colors (neutral=blue, active=red, resolved=green)
4. **Finalize**: Save JSON with full simulation data

## Architecture

Single `SimulationMonolith` class handles everything:
- Graph management (NetworkX)
- LLM orchestration (OpenRouter API)
- Database persistence (SQLite)
- Monitoring (Logfire, no keys needed)
- Visualization (Matplotlib)

Configuration via `SimConfig` dataclass:
```python
config = SimConfig(
    scenario="...",
    nodes=5,           # Number of actors
    steps=3,           # Simulation steps
    max_tokens=1000,   # LLM response limit
    temperature=0.5    # 0=deterministic, 1=random
)
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'httpx'"

Activate venv:
```bash
source .venv/bin/activate
```

### "Set OPENROUTER_API_KEY env var"

Your `.env` isn't loading. Check:
1. File exists: `ls -la .env`
2. No quotes: Should be `KEY=value`, not `KEY="value"`
3. Or export: `export OPENROUTER_API_KEY="sk-or-..."`

### "API error" or timeout

- Verify key at https://openrouter.ai/keys
- Check internet connection
- Increase timeout in SimConfig: `timeout=120`

### "Out of memory"

Use fewer nodes/steps in SimConfig:
```python
config = SimConfig(scenario="...", nodes=3, steps=2)
```

## Customization

### Change Model

Edit `monolith.py`, find `model` in SimConfig:
```python
model="meta-llama/llama-2-7b-chat"  # or use another from openrouter.io
```

### Change Prompt

Edit `prompt.json`:
```json
{
  "system": "Your custom system prompt",
  "user": "Your custom user prompt with {scenario} and {graph} placeholders"
}
```

### Add More Steps

```python
config = SimConfig(scenario="...", steps=5)
```

### Analyze Results

```bash
python analyze.py                          # Latest
python analyze.py outputs/20251106_185430  # Specific
```

Shows interaction counts, node activity, state distributions.

## Performance

- Runtime: 10-60 seconds per simulation (LLM latency dependent)
- Memory: ~100MB
- Disk: ~1-2MB per run
- Tokens: ~1000 per run (3 steps × ~300 tokens)

Spring layout uses 50 iterations (seed=42 for reproducibility).
PNG rendered at 80 DPI (fast).

## Files

```
.
├── monolith.py         Core engine (~250 lines)
├── prompt.json         LLM prompts
├── requirements.txt    Dependencies (httpx, networkx, matplotlib, python-dotenv, logfire)
├── .env.example        API key template
├── init.sh             Setup script
├── analyze.py          Output analyzer
├── .gitignore          Git ignore
├── README.md           This file
├── outputs/            Simulation results (created)
└── data_files/         Databases (created)
```

## Observability

Built-in Logfire spans (no extra config):

```
simulation
├── initialization
│   ├── database_init
│   └── graph_init
├── step_0
│   ├── llm_orchestration → api_call
│   ├── parse_step
│   ├── apply_step_0
│   └── render_step_0
└── finalize
```

All LLM responses logged to SQLite for audit trail.

## API Pricing

OpenRouter free tier provides free credits. Check your usage at https://openrouter.io/usage

Typical cost per simulation: $0.001 - $0.01 (varies by model)

## Notes

- Each run is isolated (no coordination needed)
- Databases auto-cleanup (just delete files)
- Graph layout deterministic (seed=42)
- LLM output parsed with regex fallback (robust to formatting)
- State mutations applied to NetworkX graph directly
- All JSON pretty-printed for inspection

## Support

Issues? Check:
1. API key valid: https://openrouter.ai/keys
2. .env format (no quotes, NEWLINE at end)
3. Python 3.10+: `python --version`
4. Venv active: `which python` (should be in `.venv/bin/`)
5. Internet connection working

## Examples of Good Scenarios

- Historical events ("US Constitution signing", "Fall of Rome")
- Scientific achievements ("Moon landing", "Germ theory discovery")
- Modern scenarios ("Twitter IPO", "ChatGPT launch")
- Fictional ("Game of Thrones Red Wedding", "Lord of the Rings Fellowship")
- Personal ("startup founding team dynamics")

The LLM will simulate 3 steps of social interactions and state changes.

## License

MIT
