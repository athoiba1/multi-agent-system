# Post-Mortem Document

## System: Multi-Agent Orchestration System

### 1. Scaling Issue Encountered/Anticipated

**WebSocket Connection Management Under High Concurrency**

The current implementation stores WebSocket connections in a simple dictionary (`WebSocketManager.connections`). This approach has several scaling limitations:

- **Memory**: Each connection consumes memory; 10,000 concurrent connections would require significant RAM
- **Single Process**: The in-memory dictionary only works within a single process; multiple server instances would have disconnected state
- **No Load Balancing**: Sticky sessions required but not implemented

**Mitigation Strategies**:
1. Use Redis Pub/Sub for cross-process event distribution
2. Implement connection pooling with limits per client
3. Add heartbeat/ping-pong to detect stale connections
4. Consider WebSocket gateways like Socket.IO for production

**Impact**: For the demo scope (< 100 concurrent users), the current approach works. For production, a message broker (Redis, Kafka) would be required.

---

### 2. Design Change in Hindsight

**Adding Checkpoint/Resume for Long-Running Pipelines**

The current pipeline executes steps sequentially with no persistence. If the system crashes mid-execution, all progress is lost.

**What I Would Change**:
- Add a `PipelineState` model that persists to disk/database after each step completion
- Implement a `resume` method that can reload state and continue from last successful step
- Add step-level idempotency keys to prevent duplicate execution

**Example Implementation**:
```python
class PipelineState:
    task_id: str
    completed_steps: list[str]
    step_results: dict[str, StepResult]
    checkpoint_path: str

    async def save(self):
        # Write to disk/database
        pass

    @classmethod
    async def load(cls, task_id: str):
        # Resume from checkpoint
        pass
```

**Trade-off**: Added complexity vs. reliability. For a demo, the current approach is acceptable. For production, checkpointing is essential.

---

### 3. Trade-offs and Reasoning

#### Trade-off 1: Sequential vs Parallel Execution

**Choice**: Sequential execution with dependency resolution

**Reasoning**:
- **Simplicity**: Easier to debug, reason about, and stream results
- **Dependency Safety**: Guarantees step dependencies are met
- **Streaming**: Natural order for progressive output

**Alternative Considered**:
- Parallel execution for independent steps using `asyncio.gather()`
- More complex but faster for steps without dependencies

**Decision**: Chose sequential for demo clarity. The topological sort supports parallel execution as a future enhancement.

---

#### Trade-off 2: Custom Implementation vs Agent Framework

**Choice**: Custom implementation (no LangChain, CrewAI, AutoGen)

**Reasoning**:
- **Full Control**: Every component is transparent and debuggable
- **No Black Boxes**: Understanding exactly what happens under the hood
- **Educational Value**: Demonstrates core concepts without abstraction leaks
- **Lightweight**: Smaller dependency footprint

**Alternative Considered**:
- LangChain for agent orchestration
- CrewAI for multi-agent workflows
- AutoGen for conversational agents

**Decision**: Custom implementation satisfies the requirement to "NOT rely on black-box agent frameworks without explicit justification." The codebase is ~500 lines total, making it fully understandable.

---

### 4. Lessons Learned

1. **Event-Driven Architecture Works**: asyncio.Queue-based pub/sub is simple but effective for streaming
2. **Topological Sort is Key**: Proper dependency resolution prevents execution errors
3. **Retry Logic is Essential**: LLM APIs are flaky; exponential backoff prevents cascading failures
4. **Manual Batching is Trivial**: The BatchProcessor is ~50 lines; no framework needed

### 5. Future Improvements

1. **Add Checkpointing**: Persist pipeline state for resume capability
2. **Parallel Execution**: Support concurrent independent steps
3. **Real Retriever**: Connect to actual search APIs (Tavily, Serper)
4. **Monitoring**: Add Prometheus metrics for agent performance
5. **Cost Tracking**: Track token usage per agent for optimization
