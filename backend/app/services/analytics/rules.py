"""
TradeSense — Recommendation Rules Engine
Evaluates a BehavioralMetric snapshot against fixed thresholds to generate coaching Recommendations.
Ensures idempotency to avoid duplicating active recommendations.
"""
import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.behavioral_metric import BehavioralMetric
from app.models.recommendation import Recommendation

logger = logging.getLogger(__name__)


class RulesEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(self, metric: BehavioralMetric) -> list[Recommendation]:
        """
        Evaluate the latest BehavioralMetric and generate any applicable Recommendations.
        """
        new_recommendations = []

        if not metric:
            return new_recommendations

        user_id = metric.user_id
        
        # Pull all currently ACTIVE recommendations for this user to ensure idempotency
        stmt = select(Recommendation).where(
            Recommendation.user_id == user_id,
            Recommendation.status == "ACTIVE"
        )
        active_recs = (await self.db.execute(stmt)).scalars().all()
        active_rule_ids = {r.rule_id for r in active_recs}

        # Rule R001: Disposition Effect
        de_score = metric.disposition_effect_score
        if de_score is not None and de_score > 0.05:
            if "R001" not in active_rule_ids:
                logger.info(
                    "Rule R001 fired: High Disposition Effect",
                    extra={"user_id": str(user_id), "de_score": de_score, "pgr": metric.pgr, "plr": metric.plr},
                )
                r001 = Recommendation(
                    user_id=user_id,
                    rule_id="R001",
                    category="Behavioral Bias",
                    severity="HIGH",
                    title="High Disposition Effect Detected",
                    body="You are systematically selling your winning positions too early while holding onto your losing positions for too long. This erodes long-term compounding.",
                    supporting_data={"pgr": float(metric.pgr or 0), "plr": float(metric.plr or 0), "de_score": float(de_score)},
                    status="ACTIVE"
                )
                self.db.add(r001)
                new_recommendations.append(r001)

        # Rule R002: Concentration Risk
        hhi_score = metric.hhi
        if hhi_score is not None and hhi_score > 2500:
            if "R002" not in active_rule_ids:
                logger.info(
                    "Rule R002 fired: Dangerous Concentration",
                    extra={"user_id": str(user_id), "hhi": hhi_score},
                )
                r002 = Recommendation(
                    user_id=user_id,
                    rule_id="R002",
                    category="Concentration Risk",
                    severity="HIGH",
                    title="Dangerous Portfolio Concentration",
                    body="Your portfolio is highly concentrated in just a few assets. A sharp drawdown in one of these holdings will disproportionately impact your total net worth.",
                    supporting_data={"hhi": float(hhi_score)},
                    status="ACTIVE"
                )
                self.db.add(r002)
                new_recommendations.append(r002)

        # Rule R003: Overtrading
        ptr_score = metric.portfolio_turnover_ratio
        if ptr_score is not None and ptr_score > 0.10:
            if "R003" not in active_rule_ids:
                logger.info(
                    "Rule R003 fired: High Portfolio Turnover",
                    extra={"user_id": str(user_id), "ptr": ptr_score, "cost_drag_pct": metric.cost_drag_pct},
                )
                r003 = Recommendation(
                    user_id=user_id,
                    rule_id="R003",
                    category="Overtrading",
                    severity="MEDIUM",
                    title="High Portfolio Turnover",
                    body="You are trading very frequently compared to your portfolio size. High turnover generates significant frictional costs (brokerage and taxes) which drag down your net return.",
                    supporting_data={"ptr": float(ptr_score), "cost_drag_pct": float(metric.cost_drag_pct or 0)},
                    status="ACTIVE"
                )
                self.db.add(r003)
                new_recommendations.append(r003)

        if new_recommendations:
            # ISSUE-06 FIX: Do NOT commit here. ingestion.py owns the transaction.
            # flush() writes rows without committing so they're visible in the same session.
            await self.db.flush()
            logger.info(
                "New recommendations flushed",
                extra={"user_id": str(user_id), "count": len(new_recommendations), "rule_ids": [r.rule_id for r in new_recommendations]},
            )

        return new_recommendations
