from collections import deque, defaultdict
from decimal import Decimal
from typing import Sequence
from app.models.transaction import Transaction

class FIFOPortfolioTracker:
    def __init__(self):
        # Maps symbol to deque of open BUY lots
        self.open_lots = defaultdict(deque)
        # Maps symbol to total realized PnL
        self.realized_pnl = defaultdict(Decimal)
        # Set of symbols that were held but are now fully liquidated
        self.closed_positions = set()

    def process_transactions(self, transactions: Sequence[Transaction]) -> dict[str, dict]:
        """
        Processes a chronological list of transactions using FIFO method.
        Returns a dictionary mapping symbol to holdings summary.
        """
        # Group by symbol
        by_symbol: dict[str, list[Transaction]] = defaultdict(list)
        for tx in transactions:
            by_symbol[tx.symbol.upper()].append(tx)

        holdings_summary = {}

        for symbol, tx_list in by_symbol.items():
            # Sort chronologically. Same date -> BUY before SELL
            tx_list.sort(key=lambda t: (t.trade_date, 0 if t.transaction_type == "BUY" else 1))

            for tx in tx_list:
                qty = Decimal(str(tx.quantity))

                if tx.transaction_type == "BUY":
                    cost_basis_per_unit = Decimal(str(tx.net_value)) / qty
                    self.open_lots[symbol].append({
                        "quantity": qty,
                        "cost_basis_per_unit": cost_basis_per_unit,
                        "trade_date": tx.trade_date,
                    })
                    if symbol in self.closed_positions:
                        self.closed_positions.remove(symbol)
                
                elif tx.transaction_type == "SELL":
                    sell_qty_remaining = qty
                    sell_price_per_unit = Decimal(str(tx.net_value)) / qty

                    while sell_qty_remaining > Decimal("0"):
                        if not self.open_lots[symbol]:
                            raise ValueError(
                                f"Invalid sell: Selling more than owned for {symbol} on {tx.trade_date}. "
                                f"Quantity to sell: {sell_qty_remaining}"
                            )

                        oldest_lot = self.open_lots[symbol][0]
                        lot_qty = oldest_lot["quantity"]

                        if lot_qty <= sell_qty_remaining:
                            # Sell entire oldest lot
                            sold_qty = lot_qty
                            self.open_lots[symbol].popleft()
                            sell_qty_remaining -= sold_qty
                        else:
                            # Partial sell of oldest lot
                            sold_qty = sell_qty_remaining
                            oldest_lot["quantity"] -= sold_qty
                            sell_qty_remaining = Decimal("0")

                        # Calculate Realized PnL for this chunk
                        # PnL = (Sell Price - Cost Basis) * Quantity Sold
                        lot_cost_basis = oldest_lot["cost_basis_per_unit"]
                        pnl_chunk = (sell_price_per_unit - lot_cost_basis) * sold_qty
                        self.realized_pnl[symbol] += pnl_chunk
            
            # Post-process for symbol
            total_qty = sum(lot["quantity"] for lot in self.open_lots[symbol])
            if total_qty > Decimal("0"):
                total_cost = sum(lot["quantity"] * lot["cost_basis_per_unit"] for lot in self.open_lots[symbol])
                avg_cost_basis = total_cost / total_qty
                holdings_summary[symbol] = {
                    "quantity": total_qty,
                    "avg_cost_basis": avg_cost_basis,
                    "realized_pnl": self.realized_pnl[symbol],
                }
            else:
                self.closed_positions.add(symbol)
                holdings_summary[symbol] = {
                    "quantity": Decimal("0"),
                    "avg_cost_basis": Decimal("0"),
                    "realized_pnl": self.realized_pnl[symbol],
                }

        return holdings_summary
