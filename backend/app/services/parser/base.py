from abc import ABC, abstractmethod
from typing import Any


class BaseCSVParser(ABC):
    @abstractmethod
    def parse(self, csv_content: str) -> list[dict[str, Any]]:
        """
        Parses raw CSV content and outputs a list of dictionaries,
        each representing a normalized transaction.
        The keys should align with TransactionBase.
        """
        pass
