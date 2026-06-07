# TradeSense 🧠📈
### "Turn Trading History Into Behavioral Intelligence."

> A behavioral analytics platform that helps retail investors understand **why** they make trading mistakes — not just **what** they traded.

---

## What It Does

TradeSense analyzes your broker's CSV trade history and surfaces:

| Metric | What It Measures |
|--------|-----------------|
| **Disposition Effect** (PGR/PLR) | Are you selling winners too early and holding losers too long? |
| **Portfolio Turnover Ratio** | Are you overtrading and bleeding returns to transaction costs? |
| **HHI Concentration** | Is your portfolio dangerously concentrated in a few stocks? |
| **Behavioral Risk Score** | A composite 0–100 score summarizing all behavioral biases |
| **Recommendations** | Personalized, severity-ranked coaching to fix the top issues |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts |
| State | Zustand + TanStack Query |
| Backend | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 + SQLAlchemy async |
| Migrations | Alembic |
| Auth | JWT (python-jose) + bcrypt |
| Infrastructure | Docker + Docker Compose |

---

## Quick Start (Docker — Recommended)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Uddivz/Trade_Sense.git
cd Trade_Sense
```

### 2. Configure environment

```bash
# Copy the backend environment template
cp backend/.env.example backend/.env

# Open backend/.env and set:
# SECRET_KEY=<run: openssl rand -hex 32>
# All other defaults work for local development
```

### 3. Start all services

```bash
docker compose up --build
```

This starts:
- **PostgreSQL** on port `5432`
- **FastAPI backend** on port `8000` with hot reload
- **Next.js frontend** on port `3000` with hot reload

### 4. Run database migrations

```bash
# In a new terminal:
docker compose --profile migrate up migrate
```

### 5. Open the application

| Service | URL |
|---------|-----|
| Frontend App | http://localhost:3000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Health Check | http://localhost:8000/health |

---

## Local Development (Without Docker)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env — set DATABASE_URL to your local PostgreSQL instance

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set environment variable
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
```

---

## Project Structure

```
Trade_Sense/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   ← Route handlers (auth, portfolios, uploads, analytics)
│   │   ├── core/               ← Security utilities (JWT, bcrypt)
│   │   ├── models/             ← SQLAlchemy ORM models
│   │   ├── schemas/            ← Pydantic request/response models
│   │   ├── services/           ← Business logic (parsers, cost basis)
│   │   ├── analytics/          ← Behavioral metrics engine
│   │   ├── recommendations/    ← Rule-based recommendation engine
│   │   ├── config.py           ← Settings (Pydantic BaseSettings)
│   │   ├── database.py         ← Async engine + session factory
│   │   └── main.py             ← FastAPI app factory
│   ├── alembic/                ← Database migrations
│   └── tests/                  ← pytest test suite
│
├── frontend/
│   ├── app/                    ← Next.js 14 App Router pages
│   ├── components/             ← Reusable UI components
│   │   ├── ui/                 ← KPICard, RecommendationCard, etc.
│   │   └── charts/             ← RiskGauge, DispositionChart, Treemap
│   ├── lib/                    ← API client (Axios)
│   ├── store/                  ← Zustand state
│   └── types/                  ← TypeScript interfaces
│
├── docs/                       ← Architecture docs, ADRs
├── docker-compose.yml
└── README.md
```

---

## API Reference

Interactive Swagger UI available at: **http://localhost:8000/docs**

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/auth/register` | Register new user |
| `POST` | `/v1/auth/login` | Obtain JWT token |
| `GET` | `/v1/portfolios/` | List user portfolios |
| `POST` | `/v1/portfolios/` | Create portfolio |
| `POST` | `/v1/uploads/{portfolio_id}` | Upload broker CSV |
| `GET` | `/v1/analytics/behavioral-summary` | Get all behavioral metrics |
| `GET` | `/v1/analytics/recommendations` | Get personalized recommendations |
| `PATCH` | `/v1/analytics/recommendations/{id}/dismiss` | Dismiss a recommendation |
| `GET` | `/health` | System health check |

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## Supported CSV Formats

| Broker | Format | Status |
|--------|--------|--------|
| Zerodha (Kite Console) | Trade Book CSV | ✅ Supported |
| Generic | Auto-detected columns | ✅ Supported |
| Groww | P&L Statement | 🔜 Phase 2 |
| Angel One | Trade Book | 🔜 Phase 2 |

---

## Development Phases

| Phase | Timeline | Focus |
|-------|----------|-------|
| **MVP** | Weeks 1–4 | Auth, CSV upload, 5 analytics metrics, dashboard |
| **Phase 2** | Weeks 5–12 | ML clustering, async tasks, additional brokers |
| **Phase 3** | Months 4–9 | Mobile app, predictive alerts, AI coaching |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit changes: `git commit -m "feat: add your feature"`
4. Push and open a pull request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built as a Final Year Engineering Project demonstrating quantitative finance, behavioral analytics, and full-stack engineering.*
