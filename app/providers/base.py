from abc import ABC, abstractmethod
from typing import Optional
from app.schemas.signal import SignalCreate


class BaseProvider(ABC):
    @abstractmethod
    async def extract(self, company_id: int, website: str) -> Optional[SignalCreate]:
        """Extract signal data from the target website and return a SignalCreate schema."""
        pass