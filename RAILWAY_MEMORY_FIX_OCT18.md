# Railway Memory Crisis Fix - October 18, 2025

## Problem

**Railway Crash**: Memory usage 6.3GB → exceeds Railway limits → server crash
**Log Evidence**: `2025-10-19 00:23:54,285 - WARNING - 💾 High Memory: 6.3GB`

## Root Causes

### 1. Permanent Model Loading (3.2GB baseline)
```python
# Current (problematic):
def initialize(self):
    self.model = AutoModel.from_pretrained(...)  # Loads into memory permanently
    self.model.eval()  # Keeps model loaded 24/7
```

**Problem**: JinaV3 model stays in memory even when idle
**Impact**: 3.2GB baseline + requests + connections = 6.3GB+

### 2. Unbounded SSE Connections
```python
# Line 1004 in mcp-claude-connector-memory-server.py:
while True:
    await asyncio.sleep(30)
    await response.write(b": keepalive\n\n")  # Never exits!
```

**Problem**: Each Mobile/Desktop connection creates infinite loop
**Impact**: 10 connections × overhead = memory accumulation

### 3. No Resource Cleanup
- Warning system detects high memory but doesn't act
- No model unloading when idle
- No connection limits or cleanup
- No garbage collection triggers

## Railway Resource Limits

**Likely Tier**: Free or Hobby plan
- **Memory Limit**: 512MB - 1GB
- **Current Usage**: 6.3GB (6-12x over limit)
- **Result**: OOM kill → crash

## Solution: Lazy Loading + Automatic Cleanup

### Fix 1: Lazy Model Loading

**Concept**: Only load JinaV3 when actually needed, unload when idle

```python
class LazyJinaV3Embedder:
    def __init__(self):
        self.model = None
        self.last_used = None
        self.idle_timeout = 300  # 5 minutes

    async def get_embedding(self, text):
        # Load model on-demand
        if self.model is None:
            await self._load_model()

        self.last_used = time.time()
        result = self._generate(text)

        # Schedule unload if idle
        asyncio.create_task(self._check_idle_unload())

        return result

    async def _check_idle_unload(self):
        await asyncio.sleep(self.idle_timeout)
        if time.time() - self.last_used > self.idle_timeout:
            self._unload_model()

    def _unload_model(self):
        if self.model is not None:
            del self.model
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            gc.collect()
            self.model = None
            logger.info("🧹 Model unloaded to free memory")
```

**Benefit**: 3.2GB freed when idle → only ~500MB baseline

### Fix 2: SSE Connection Limits

```python
# Global connection tracking
active_sse_connections = set()
MAX_SSE_CONNECTIONS = 5

async def handle_sse(request):
    if len(active_sse_connections) >= MAX_SSE_CONNECTIONS:
        return web.Response(
            status=503,
            text="Server at capacity. Please try again in a moment."
        )

    session_id = str(uuid4())
    active_sse_connections.add(session_id)

    try:
        # ... existing SSE logic ...
        while True:
            await asyncio.sleep(30)
            await response.write(b": keepalive\n\n")
    finally:
        # CRITICAL: Always cleanup on disconnect
        active_sse_connections.remove(session_id)
        logger.info(f"🧹 SSE connection {session_id[:8]} cleaned up")
```

**Benefit**: Prevents connection accumulation

### Fix 3: Memory-Based Circuit Breaker

```python
async def check_memory_before_request(request, handler):
    memory_gb = psutil.Process().memory_info().rss / 1024**3

    if memory_gb > 4.5:  # 4.5GB threshold (before Railway kills at 5GB)
        logger.warning(f"⚠️ Memory {memory_gb:.1f}GB - rejecting requests")

        # Emergency cleanup
        gc.collect()
        if hasattr(embedder, '_unload_model'):
            embedder._unload_model()

        return web.Response(
            status=503,
            text="Server performing memory cleanup. Please retry in 30 seconds."
        )

    return await handler(request)
```

**Benefit**: Prevents crash by rejecting requests before OOM

## Implementation Plan

### Phase 1: Quick Fix (30 minutes)
1. Add SSE connection limit (MAX_SSE_CONNECTIONS=5)
2. Add connection cleanup in `finally` block
3. Add memory circuit breaker middleware
4. Deploy to Railway

**Expected Result**: Stop crashes, reduce memory to ~2-3GB

### Phase 2: Lazy Loading (2 hours)
1. Implement lazy model loading
2. Add idle timeout unloading (5 minutes)
3. Add memory-triggered unloading
4. Test locally with memory profiling

**Expected Result**: Idle memory ~500MB, active ~3.5GB

### Phase 3: Long-term Optimization (future)
1. Move to Railway Pro plan (8GB memory)
2. Implement Redis caching for embeddings
3. Add horizontal scaling with load balancer
4. Separate embedding service

## Deployment

**Quick Fix Deployment**:
```bash
cd llm/mcp/connectors/mcp-claude-connector/neo4j-mcp-railway-repo
# Apply Phase 1 fixes
git add mcp-claude-connector-memory-server.py
git commit -m "fix(railway): Add SSE connection limits + memory circuit breaker"
git push  # Triggers Railway auto-deploy
```

**Monitoring After Deploy**:
- Watch Railway logs for memory warnings
- Check connection count stays ≤ 5
- Verify no more crashes

## Alternative: Disable JinaV3 on Railway

**Nuclear Option** (if fixes don't work):
```python
# In Railway environment only:
if os.getenv("RAILWAY_ENVIRONMENT") == "production":
    USE_JINA_EMBEDDINGS = False
    logger.warning("⚠️ JinaV3 disabled on Railway due to memory constraints")
```

**Trade-off**: Lose semantic search quality, but server stays up

## References

- Railway Memory Limits: <https://docs.railway.app/reference/pricing#resource-limits>
- JinaV3 Memory Profile: ~3.2GB (documented in jina_v3_optimized_embedder.py:238)
- SSE Keepalive Loop: mcp-claude-connector-memory-server.py:1004

---

**Status**: Diagnosis complete, awaiting fix implementation
**Priority**: P0 (service down)
**ETA**: 30 minutes for Phase 1 quick fix
