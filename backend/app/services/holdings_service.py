import uuid
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.services.portfolio_tracker import FIFOPortfolioTracker
from app.services.market_data_service import MarketDataService


class HoldingsService:
    @staticmethod
    async def update_portfolio_holdings(db: AsyncSession, portfolio_id: uuid.UUID) -> list[Holding]:
        """
        Recalculates and upserts holdings for a given portfolio.
        Fetches transactions, runs FIFO math, pulls prices, and synchronizes the DB state.
        """
        # 1. Fetch all transactions for this portfolio
        result = await db.execute(
            select(Transaction)
            .where(Transaction.portfolio_id == portfolio_id)
            .order_by(Transaction.trade_date.asc(), Transaction.created_at.asc())
        )
        transactions = result.scalars().all()

        # 2. Compute current positions via FIFO queue
        tracker = FIFOPortfolioTracker()
        summary = tracker.process_transactions(transactions)

        # 3. Pull current market prices for active positions
        active_symbols = [symbol for symbol, metrics in summary.items() if metrics["quantity"] > 0]
        prices = await MarketDataService.fetch_current_prices(active_symbols)

        # 4. Fetch existing holdings currently saved
        result_existing = await db.execute(
            select(Holding).where(Holding.portfolio_id == portfolio_id)
        )
        existing_holdings = {h.symbol.upper(): h for h in result_existing.scalars().all()}

        final_holdings = []

        # 5. Upsert active holdings
        for symbol, metrics in summary.items():
            qty = metrics["quantity"]
            avg_cost = metrics["avg_cost_basis"]
            realized_pnl = metrics.get("realized_pnl", Decimal("0"))

            if qty <= 0:
                continue

            price = prices.get(symbol.upper(), Decimal("500.00"))
            current_value = qty * price
            cost_value = qty * avg_cost
            unrealized_pnl = current_value - cost_value
            unrealized_pnl_pct = unrealized_pnl / cost_value if cost_value > 0 else Decimal("0")

            # Extract ISIN & Exchange details from transactions
            isin = None
            exchange = "NSE"
            for tx in transactions:
                if tx.symbol.upper() == symbol:
                    if tx.isin:
                        isin = tx.isin
                    if tx.exchange:
                        exchange = tx.exchange

            if symbol in existing_holdings:
                holding = existing_holdings[symbol]
                holding.quantity = qty
                holding.average_cost = avg_cost
                holding.market_price = price
                holding.market_value = current_value
                holding.unrealized_pnl = unrealized_pnl
                holding.unrealized_pnl_pct = unrealized_pnl_pct
                holding.realized_pnl = realized_pnl
                holding.isin = isin or holding.isin
                holding.exchange = exchange
            else:
                holding = Holding(
                    portfolio_id=portfolio_id,
                    symbol=symbol,
                    isin=isin,
                    exchange=exchange,
                    quantity=qty,
                    average_cost=avg_cost,
                    market_price=price,
                    market_value=current_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    realized_pnl=realized_pnl,
                )
                db.add(holding)

            final_holdings.append(holding)

        # 6. Delete holdings that are fully liquidated (quantity is 0)
        for symbol, holding in existing_holdings.items():
            if symbol not in summary or summary[symbol]["quantity"] <= 0:
                await db.delete(holding)

        await db.flush()
        return final_holdings
