# TradeSense — Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the TradeSense project.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](ADR-001-tech-stack.md) | Technology Stack Selection | Accepted |
| [ADR-002](ADR-002-async-db.md) | Async Database Access Pattern | Accepted |
| [ADR-003](ADR-003-fifo-cost-basis.md) | FIFO Cost Basis Algorithm | Accepted |

---

## ADR-001: Technology Stack Selection

**Status:** Accepted  
**Date:** 2026-06-07

### Context
TradeSense is a 4-week MVP with a team of 1–3 developers targeting a resume-quality, production-grade codebase.

### Decision
- **Backend:** FastAPI (Python 3.12) — async, auto-OpenAPI, Python ML ecosystem
- **Database:** PostgreSQL 16 — ACID guarantees required for financial data
- **Frontend:** Next.js 14 + TypeScript — SSR for landing pages, CSR for dashboard
- **Auth:** JWT with bcrypt — stateless, scalable, standard

### Consequences
- Python ML libraries (scikit-learn, yfinance) integrate natively with FastAPI workers
- PostgreSQL NUMERIC type prevents floating-point precision loss on financial calculations
- FastAPI auto-generates OpenAPI docs — reduces documentation overhead

---

## ADR-002: Synchronous Analytics in MVP

**Status:** Accepted  
**Date:** 2026-06-07

### Context
Phase 2 design calls for Celery async task queue. However, this adds operational complexity (Redis, worker processes) that is unrealistic for a 4-week sprint.

### Decision
Analytics are computed synchronously in the upload endpoint. This adds ~3–8 seconds to the upload response time, which is acceptable for MVP demo purposes.

### Migration Path
In Phase 2: extract `engine.compute_and_save()` into a Celery task. The upload endpoint returns 202 Accepted immediately and uses Server-Sent Events (SSE) to notify the frontend on completion.

---

## ADR-003: FIFO Cost Basis

**Status:** Accepted  
**Date:** 2026-06-07

### Context
Multiple cost basis methods exist: FIFO, LIFO, Weighted Average Cost. The correct behavioral analytics require tracking individual lots to compute per-sale gain/loss.

### Decision
FIFO (First In, First Out) is implemented as the default. This is the method required by Indian tax law (SEBI guidelines) and the most common in broker reporting.

### Consequences
- Individual lot tracking enables accurate PGR/PLR computation
- LIFO and WAC can be added as portfolio-level settings in Phase 2
- Corporate actions (splits, bonuses) require retroactive lot adjustment — deferred to Phase 2
