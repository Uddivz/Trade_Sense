import hashlib
from typing import Sequence
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def generate_signature(
        self,
        portfolio_id: uuid.UUID,
        symbol: str,
        tx_type: str,
        qty: float,
        price: float,
        trade_date_str: str,
        broker: str | None = None,
        external_trade_id: str | None = None,
    ) -> str:
        # Standardize representation to avoid floating point mismatch issues in hashing strings
        qty_str = f"{float(qty):.6f}"
        price_str = f"{float(price):.4f}"
        broker_str = broker.strip().upper() if broker else ""
        ext_id_str = external_trade_id.strip() if external_trade_id else ""
        components = f"{portfolio_id}:{symbol.upper()}:{tx_type.upper()}:{qty_str}:{price_str}:{trade_date_str}:{broker_str}:{ext_id_str}"
        return hashlib.sha256(components.encode("utf-8")).hexdigest()

    async def get_portfolio_transactions(self, portfolio_id: uuid.UUID) -> Sequence[Transaction]:
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.portfolio_id == portfolio_id)
            .order_by(Transaction.trade_date.asc(), Transaction.created_at.asc())
        )
        return result.scalars().all()

    async def filter_duplicates(
        self, portfolio_id: uuid.UUID, parsed_records: list[dict]
    ) -> list[dict]:
        """
        Compares parsed records against existing database transactions.
        Returns only new records.
        """
        existing_txs = await self.get_portfolio_transactions(portfolio_id)

        existing_trade_ids = set()
        existing_signatures = set()

        for tx in existing_txs:
            if tx.broker_trade_id:
                existing_trade_ids.add(tx.broker_trade_id.strip())
            sig = self.generate_signature(
                portfolio_id=tx.portfolio_id,
                symbol=tx.symbol,
                tx_type=tx.transaction_type,
                qty=tx.quantity,
                price=tx.price,
                trade_date_str=tx.trade_date.isoformat(),
                broker=tx.broker,
                external_trade_id=tx.external_trade_id,
            )
            existing_signatures.add(sig)

        unique_records = []
        for record in parsed_records:
            broker_trade_id = record.get("broker_trade_id")
            if broker_trade_id and broker_trade_id.strip() in existing_trade_ids:
                continue

            sig = self.generate_signature(
                portfolio_id=portfolio_id,
                symbol=record["symbol"],
                tx_type=record["transaction_type"],
                qty=record["quantity"],
                price=record["price"],
                trade_date_str=record["trade_date"].isoformat(),
                broker=record.get("broker"),
                external_trade_id=record.get("external_trade_id"),
            )
            if sig in existing_signatures:
                continue

            unique_records.append(record)

        return unique_records

    async def bulk_insert(self, portfolio_id: uuid.UUID, records: list[dict]) -> list[Transaction]:
        db_records = []
        for r in records:
            tx = Transaction(
                portfolio_id=portfolio_id,
                broker_trade_id=r.get("broker_trade_id"),
                symbol=r["symbol"],
                isin=r.get("isin"),
                exchange=r.get("exchange", "NSE"),
                transaction_type=r["transaction_type"],
                quantity=r["quantity"],
                price=r["price"],
                total_value=r["total_value"],
                brokerage=r.get("brokerage", 0),
                stt=r.get("stt", 0),
                other_charges=r.get("other_charges", 0),
                net_value=r["net_value"],
                trade_date=r["trade_date"],
                notes=r.get("notes"),
                raw_data=r.get("raw_data"),
            )
            self.db.add(tx)
            db_records.append(tx)

        if db_records:
            await self.db.flush()
        return db_records
