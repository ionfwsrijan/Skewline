# Contributing to Skewline

Thanks for your interest in contributing to Skewline! This document covers the development setup and conventions.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Git

### Backend

```bash
git clone https://github.com/ionfwsrijan/Skewline.git
cd Skewline
pip install -e ".[dev]"
```

### Frontend

```bash
cd web
npm install
npm run dev    # Vite dev server at http://localhost:5173
```

### Running Tests

```bash
# Core tests (no matplotlib dependency)
pytest tests/test_agents.py tests/test_lob_matching.py tests/test_pnl_accounting.py \
       tests/test_risk_manager.py tests/test_price_process.py tests/test_multi_asset.py \
       tests/test_execution_quality.py tests/test_stat_tests.py tests/test_dqn_integration.py -q
```

> **Note:** `test_config_and_reporting.py` uses matplotlib and may crash on Windows due to Qt backend issues. CI runs on Ubuntu where this passes.

### Running the API

```bash
py -m uvicorn api.main:app --reload --port 8000
# Swagger docs at http://localhost:8000/docs
```

## Project Structure

```
src/
  agents/          Strategy implementations (one file per agent)
  engine/          Core simulation loop and risk manager
  market/          Price process, order book, calibration
  order_flow/      Noise and informed trader models
  metrics/         P&L decomposition, execution quality, accounting
  research/        Monte Carlo, walk-forward, scenario analysis
configs/           YAML experiment definitions
api/               FastAPI REST + WebSocket backend
web/               React + Tailwind frontend
tests/             pytest test suite
```

## Code Conventions

### Python

- Type hints on all public functions
- Follow existing patterns (see any agent file for reference)
- One class per file for agents
- All agents implement `BaseAgent.quote(AgentContext) -> Quote`
- Configs are YAML with a flat structure, validated by `config.validate_config()`

### TypeScript / React

- Functional components with hooks
- TypeScript strict mode (`tsc --noEmit` must pass)
- Use shadcn/ui components from `web/src/components/ui/`
- Tailwind classes only (no inline styles)
- Framer Motion for animations

### Commits

- Use conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `perf:`
- Keep commits focused on one change
- Run tests and `npm run build` before pushing

## Adding a New Agent

1. Create `src/agents/my_agent.py` implementing `BaseAgent`
2. Add `agent_id` field (e.g., `"my_agent"`)
3. Register in `src/agents/factory.py`
4. Add a config in `configs/my_agent.yaml`
5. Add tests in `tests/test_agents.py`

## Adding a New Frontend Tab

1. Create `web/src/components/MyTab.tsx`
2. Add `lazy(() => import("./components/MyTab"))` in `App.tsx`
3. Add to the `tabs` array and render inside `<Suspense>`

## Architecture

```
Price Process -> Order Flow -> Latency Queue -> LOB
                                                  |
                                              Agent.quote()
                                                  |
                                           Risk Manager
                                                  |
                                          P&L Decomposition
                                                  |
                                        Accounting Audit
                                                  |
                                        FastAPI REST/WS
                                                  |
                                       React Dashboard
```

## Questions?

Open an issue at https://github.com/ionfwsrijan/Skewline/issues
