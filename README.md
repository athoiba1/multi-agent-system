# Multi-Agent Orchestration System

A system that decomposes complex user requests into discrete steps and executes them using specialized agents. Streams partial results in real-time and handles failures gracefully.

## Features

- **Task Decomposition**: Automatically breaks complex requests into ordered steps
- **Specialized Agents**: Planner, Retriever, Analyzer, Writer
- **Async Execution**: Full async/await architecture for performance
- **Real-time Streaming**: WebSocket and SSE for live updates
- **Manual Batching**: Custom batch processing without black-box abstractions
- **Failure Handling**: Retry with exponential backoff

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install and Start Ollama

```bash
# Install Ollama: https://ollama.ai
# Pull a model:
ollama pull llama3.2

# Start Ollama server (runs on http://localhost:11434):
ollama serve
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env to configure model (default: llama3.2)
```

### 3. Run Server

```bash
python run.py
```

Server starts at `http://localhost:8000`

### 4. API Documentation

Visit `http://localhost:8000/docs` for Swagger UI

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/execute` | Execute a task (returns full result) |
| POST | `/api/execute/stream` | Execute with SSE streaming |
| POST | `/api/batch` | Execute multiple tasks in batches |
| WS | `/api/ws` | WebSocket for real-time events |
| GET | `/health` | Health check |

## Example Usage

### Execute a Task

```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "Research the impact of AI on healthcare in 2026 and write a report"}'
```

### Execute with Streaming (SSE)

```bash
curl -X POST http://localhost:8000/api/execute/stream \
  -H "Content-Type: application/json" \
  -d '{"task": "Research quantum computing advances"}'
```

### Execute Batch

```bash
curl -X POST http://localhost:8000/api/batch \
  -H "Content-Type: application/json" \
  -d '{"tasks": ["Task 1", "Task 2", "Task 3"], "batch_size": 2}'
```

### WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

## Architecture

```
User Request → Decomposer → Pipeline → Agents → Result
                    ↓            ↓         ↓
               Planner      Step 1    Retriever
                           Step 2    Analyzer
                           Step 3    Writer
```

See [docs/DESIGN.md](docs/DESIGN.md) for detailed architecture.

## Testing

```bash
pytest tests/ -v
```

## Project Structure

```
multi-agent-system/
├── agents/           # Specialized agent implementations
├── api/              # FastAPI endpoints
├── docs/             # Design and post-mortem docs
├── llm/              # Ollama client and prompts
├── models/           # Pydantic data models
├── orchestrator/     # Pipeline and batch processing
├── streaming/        # Event streaming
├── tests/            # Unit tests
├── run.py            # Server entry point
└── requirements.txt  # Dependencies
```

## License

MIT
