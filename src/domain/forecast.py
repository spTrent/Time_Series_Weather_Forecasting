from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ForecastPoint:
    """Одна точка прогноза/наблюдения: момент времени и температура."""

    ts: datetime
    temperature: float
