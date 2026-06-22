import csv
import io
from datetime import datetime, date
from decimal import Decimal
from typing import Any
from app.services.parser.base import BaseCSVParser


class ZerodhaParser(BaseCSVParser):
    def parse(self, csv_content: str) -> list[dict[str, Any]]:
        """
        Parses Zerodha Kite CSV files.
        """
        # Read lines, strip out any potential header/metadata lines before column headers
        lines = csv_content.strip().splitlines()
        
        # Find index of header row
        header_row_index = 0
        for i, line in enumerate(lines[:10]):
            lower_line = line.lower()
            if "symbol" in lower_line and ("type" in lower_line or "transaction_type" in lower_line) and "quantity" in lower_line:
                header_row_index = i
                break
        
        csv_data = "\n".join(lines[header_row_index:])
        reader = csv.DictReader(io.StringIO(csv_data))
        
        normalized_records = []
        for row in reader:
            # Skip empty rows or rows without symbol
            row = {k.strip().lower() if k else "": v.strip() for k, v in row.items()}
            symbol = row.get("symbol")
            if not symbol:
                continue
            
            # Map values
            isin = row.get("isin")
            exchange = row.get("exchange", "NSE").upper()
            
            # Transaction Type mapping
            tx_type = row.get("type", row.get("transaction_type", "")).upper()
            if tx_type in ("BUY", "B"):
                tx_type = "BUY"
            elif tx_type in ("SELL", "S"):
                tx_type = "SELL"
            else:
                continue  # Skip invalid transaction type
                
            qty = Decimal(row.get("quantity", "0"))
            price = Decimal(row.get("price", "0"))
            
            # Parse Date
            trade_date_str = row.get("trade date", row.get("trade_date", ""))
            trade_date = self._parse_date(trade_date_str)
            
            # Charges
            brokerage = Decimal(row.get("brokerage", "0") or "0")
            stt = Decimal(row.get("stt", "0") or "0")
            other_charges = Decimal(row.get("other charges", row.get("other_charges", "0")) or "0")
            
            total_value = qty * price
            
            if tx_type == "BUY":
                net_value = total_value + brokerage + stt + other_charges
            else:
                net_value = total_value - brokerage - stt - other_charges
                
            broker_trade_id = row.get("trade id", row.get("trade_id", row.get("broker_trade_id")))
            
            normalized_records.append({
                "symbol": symbol.upper(),
                "isin": isin,
                "exchange": exchange if exchange else "NSE",
                "transaction_type": tx_type,
                "quantity": qty,
                "price": price,
                "total_value": total_value,
                "brokerage": brokerage,
                "stt": stt,
                "other_charges": other_charges,
                "net_value": net_value,
                "trade_date": trade_date,
                "broker_trade_id": broker_trade_id,
                "raw_data": row
            })
            
        return normalized_records

    def _parse_date(self, date_str: str) -> date:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%d-%b-%Y"):
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Could not parse trade date: '{date_str}'")
