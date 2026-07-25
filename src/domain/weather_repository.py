from typing import Protocol
import pandas as pd
from datetime import datetime


class WeatherRepository(Protocol):
    def load_archive(self, city: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        ...