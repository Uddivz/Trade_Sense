"""
TradeSense — Behavioral Analytics Engine
Coordinates the extraction of portfolio data, calculates metrics via the pure math module,
and saves the resultant BehavioralMetric snapshot to the database.
"""
import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.holding import Holding
from app.models.transaction import Transaction
from app.models.behavioral_metric import BehavioralMetric
from app.services.analytics import math as analytics_math


class AnalyticsEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_metrics(self, user_id: uuid.UUID, portfolio_id: uuid.UUID) -> BehavioralMetric | None:
        """
        Extracts raw data, calculates all behavioral metrics, and persists the snapshot.
        """
        # 1. Fetch Holdings
        stmt_h = select(Holding).where(Holding.portfolio_id == portfolio_id)
        holdings = (await self.db.execute(stmt_h)).scalars().all()

        # 2. Fetch Transactions
        stmt_t = select(Transaction).where(Transaction.portfolio_id == portfolio_id)
        transactions = (await self.db.execute(stmt_t)).scalars().all()

        if not transactions and not holdings:
            return None

        # ── Aggregate Gains & Losses ──────────────────────────────────────────
        realized_gains = sum(Decimal(str(h.realized_pnl)) for h in holdings if h.realized_pnl and h.realized_pnl > 0)
        realized_losses = sum(abs(Decimal(str(h.realized_pnl))) for h in holdings if h.realized_pnl and h.realized_pnl < 0)
        
        paper_gains = sum(Decimal(str(h.unrealized_pnl)) for h in holdings if h.unrealized_pnl and h.unrealized_pnl > 0)
        paper_losses = sum(abs(Decimal(str(h.unrealized_pnl))) for h in holdings if h.unrealized_pnl and h.unrealized_pnl < 0)

        # ── Compute Math Metrics ─────────────────────────────────────────────
        pgr = analytics_math.calculate_pgr(
            realized_gains=Decimal(realized_gains) if realized_gains else Decimal("0.0"),
            paper_gains=Decimal(paper_gains) if paper_gains else Decimal("0.0")
        )
        plr = analytics_math.calculate_plr(
            realized_losses=Decimal(realized_losses) if realized_losses else Decimal("0.0"),
            paper_losses=Decimal(paper_losses) if paper_losses else Decimal("0.0")
        )
        de_score = analytics_math.calculate_disposition_effect(pgr, plr)

        # ── Compute Concentration ────────────────────────────────────────────
        market_values = [Decimal(str(h.market_value)) for h in holdings if h.market_value and h.market_value > 0]
        hhi_score = analytics_math.calculate_hhi(market_values)

        # ── Aggregate Transaction Data ───────────────────────────────────────
        total_buys = sum(Decimal(str(t.total_value)) for t in transactions if t.transaction_type == 'BUY')
        total_sells = sum(Decimal(str(t.total_value)) for t in transactions if t.transaction_type == 'SELL')
        total_costs = sum(Decimal(str(t.brokerage + t.stt + t.other_charges + t.fees)) for t in transactions)
        total_traded_value = sum(Decimal(str(t.total_value)) for t in transactions)
        
        # Approximate average portfolio value for the MVP as the current total market value
        current_portfolio_value = sum(Decimal(str(h.market_value)) for h in holdings if h.market_value)
        
        ptr_score = analytics_math.calculate_ptr(
            total_buys=total_buys if total_buys else Decimal("0.0"),
            total_sells=total_sells if total_sells else Decimal("0.0"),
            avg_portfolio_value=current_portfolio_value if current_portfolio_value else Decimal("0.0")
        )
        
        cost_drag_pct = analytics_math.calculate_cost_drag(
            total_costs=total_costs if total_costs else Decimal("0.0"),
            total_traded_value=total_traded_value if total_traded_value else Decimal("0.0")
        )

        # ── Create & Persist Snapshot ────────────────────────────────────────
        metric = BehavioralMetric(
            user_id=user_id,
            portfolio_id=portfolio_id,
            period_type="ALL_TIME",
            pgr=float(pgr),
            plr=float(plr),
            disposition_effect_score=float(de_score),
            portfolio_turnover_ratio=float(ptr_score),
            hhi=float(hhi_score),
            cost_drag_pct=float(cost_drag_pct),
            metric_details={
                "realized_gains": float(realized_gains),
                "realized_losses": float(realized_losses),
                "paper_gains": float(paper_gains),
                "paper_losses": float(paper_losses),
                "total_buys": float(total_buys),
                "total_sells": float(total_sells),
                "total_costs": float(total_costs),
                "total_traded_value": float(total_traded_value),
                "current_portfolio_value": float(current_portfolio_value)
            }
        )
        
        self.db.add(metric)
        # ISSUE-06 FIX: Do NOT commit here. ingestion.py owns the transaction.
        # flush() assigns the DB-generated id without committing.
        await self.db.flush()

        return metric
