import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.portfolio import Portfolio
from app.services.parser.detector import detect_broker, BrokerEnum
from app.services.parser.zerodha import ZerodhaParser
from app.services.parser.groww import GrowwParser
from app.repositories.transaction import TransactionRepository
from app.services.holdings_service import HoldingsService
from app.services.analytics.engine import AnalyticsEngine
from app.services.analytics.rules import RulesEngine


class IngestionCoordinator:
    @staticmethod
    async def ingest_csv(db: AsyncSession, portfolio_id: uuid.UUID, csv_content: str) -> dict:
        """
        Coordinates the transaction ingestion flow: sniffs, parses,
        deduplicates, persists, and triggers portfolio recalculations.
        """
        try:
            # 1. Detect broker type
            broker = detect_broker(csv_content)

            # 2. Instantiate correct parser and parse
            if broker == BrokerEnum.ZERODHA:
                parser = ZerodhaParser()
            elif broker == BrokerEnum.GROWW:
                parser = GrowwParser()
            else:
                raise ValueError(f"Parser for broker {broker} is not implemented.")

            parsed_records = parser.parse(csv_content)
            if not parsed_records:
                return {
                    "status": "success",
                    "records_parsed": 0,
                    "records_inserted": 0,
                    "records_skipped": 0,
                    "message": "No valid transaction records found in the uploaded file.",
                }

            # 3. Filter duplicates
            tx_repo = TransactionRepository(db)
            unique_records = await tx_repo.filter_duplicates(portfolio_id, parsed_records)

            # 4. Persistence
            if unique_records:
                await tx_repo.bulk_insert(portfolio_id, unique_records)

            # 5. Holdings calculation recalculation trigger
            await HoldingsService.update_portfolio_holdings(db, portfolio_id)

            # 6. Synchronously Compute Behavioral Metrics & Recommendations
            portfolio = await db.get(Portfolio, portfolio_id)
            analytics_engine = AnalyticsEngine(db)
            metric = await analytics_engine.compute_metrics(
                user_id=portfolio.user_id,
                portfolio_id=portfolio.id
            )
            
            if metric:
                rules_engine = RulesEngine(db)
                await rules_engine.evaluate(metric)

            # 7. Commit transaction
            await db.commit()

            return {
                "status": "success",
                "records_parsed": len(parsed_records),
                "records_inserted": len(unique_records),
                "records_skipped": len(parsed_records) - len(unique_records),
                "message": f"Successfully processed {len(parsed_records)} trades. Saved {len(unique_records)} new trades.",
            }
        except Exception:
            await db.rollback()
            raise
