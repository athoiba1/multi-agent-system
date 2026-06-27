# System Design Document: Multi-Agent Orchestration System

## Overview

This system decomposes complex user requests into discrete steps and executes them using specialized agents. It streams partial results in real-time and handles failures gracefully with retry logic.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Server                           │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │ REST Endpoint │  │ WebSocket    │  │ StreamingResponse   │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬──────────┘   │
│         └────────────────┼──────────────────────┘              │
│                          ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Orchestrator                           │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │   │
│  │  │ Task        │  │ Pipeline     │  │ Batch         │  │   │
│  │  │ Decomposer  │  │ Executor     │  │ Processor     │  │   │
│  │  └─────────────┘  └──────────────┘  └───────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                     │
│         ┌────────────────┼────────────────┐                   │
│         ▼                ▼                ▼                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │  Planner    │  │  Retriever  │  │  Analyzer   │           │
│  │  Agent      │  │  Agent      │  │  Agent      │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
│         │                │                │                   │
│         └────────────────┼────────────────┘                   │
│                          ▼                                     │
│                  ┌─────────────┐                               │
│                  │   Writer    │                               │
│                  │   Agent     │                               │
│                  └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Input**: User submits a complex task via REST API
2. **Decomposition**: PlannerAgent breaks task into ordered steps
3. **Execution**: Pipeline executes steps in topological order
4. **Streaming**: Events published via asyncio.Queue for real-time updates
5. **Output**: Final result returned, partial results stream via WebSocket/SSE

### Key Design Decisions

**1. No Black-Box Frameworks**
All orchestration logic is implemented from scratch:
- Custom `Pipeline` class for step execution
- Custom `BatchProcessor` for manual batching
- Custom `EventQueue` for streaming

**2. Async-First Architecture**
- All agents use `async/await`
- asyncio.Queue for event-driven communication
- Concurrent execution where dependencies allow

**3. Event-Driven Streaming**
- Each component publishes events to EventQueue
- Subscribers (WebSocket, SSE) receive events in real-time
- Events include: STEP_START, STEP_PROGRESS, STEP_COMPLETE, ERROR

**4. Failure Handling**
- Retry with exponential backoff (configurable max_retries)
- Partial result preservation on failure
- Step-level isolation (one failed step doesn't crash entire pipeline)

## Components

### Models (`models/`)
- `Task`: Represents a complex user request with ordered steps
- `Step`: Individual unit of work with status tracking
- `StepResult`/`PipelineResult`: Execution outcomes

### Agents (`agents/`)
- `Agent` (base): Abstract class with retry logic and event emission
- `PlannerAgent`: Uses LLM to decompose tasks into steps
- `RetrieverAgent`: Simulates information retrieval (can be extended to real APIs)
- `AnalyzerAgent`: Processes and synthesizes retrieved data
- `WriterAgent`: Generates structured output

### Orchestrator (`orchestrator/`)
- `Decomposer`: Uses PlannerAgent to create Task with ordered steps
- `Pipeline`: Executes steps in topological order with dependency resolution
- `BatchProcessor`: Manual batching with configurable batch size

### Streaming (`streaming/`)
- `EventQueue`: asyncio.Queue-based pub/sub system
- `WebSocketManager`: Manages WebSocket connections
- `SSEHandler`: Server-Sent Events for HTTP streaming

### LLM (`llm/`)
- `LLMClient`: Async wrapper around Ollama API (local inference)
- `prompts.py`: Agent-specific system prompts

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/execute` | Execute a task (returns full result) |
| POST | `/api/execute/stream` | Execute with SSE streaming |
| POST | `/api/batch` | Execute multiple tasks in batches |
| WS | `/api/ws` | WebSocket for real-time events |
| GET | `/health` | Health check |

## Configuration

Environment variables (`.env`):
- `OLLAMA_HOST`: Ollama server URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model to use (default: llama3.2)
- `MAX_RETRIES`: Maximum retry attempts (default: 3)
- `RETRY_DELAY`: Base delay between retries (default: 1.0s)
- `BATCH_SIZE`: Default batch size (default: 5)

## Testing

Run tests:
```bash
pytest tests/ -v
```

Test coverage includes:
- Model creation and validation
- Event queue pub/sub
- Batch processor sequential and parallel modes
- Pipeline topological sorting
- Error handling in batch processing
