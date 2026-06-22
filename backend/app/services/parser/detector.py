from enum import Enum


class BrokerEnum(str, Enum):
    ZERODHA = "ZERODHA"
    GROWW = "GROWW"


def detect_broker(csv_content: str) -> BrokerEnum:
    """
    Sniffs the first few lines of the CSV content to identify the broker.
    Raises ValueError if detection fails.
    """
    # Clean and read first few lines
    lines = [line.strip().lower() for line in csv_content.splitlines() if line.strip()][:10]
    full_text = "\n".join(lines)

    # Zerodha (Kite) patterns
    if "zerodha" in full_text:
        return BrokerEnum.ZERODHA
    if "trade date" in full_text and "isin" in full_text and "symbol" in full_text:
        return BrokerEnum.ZERODHA
    if "trade_date" in full_text and "symbol" in full_text and "quantity" in full_text:
        return BrokerEnum.ZERODHA

    # Groww patterns
    if "groww" in full_text:
        return BrokerEnum.GROWW
    if "groww transaction id" in full_text or "groww_transaction_id" in full_text:
        return BrokerEnum.GROWW

    raise ValueError("Unsupported or unrecognized broker CSV format.")
