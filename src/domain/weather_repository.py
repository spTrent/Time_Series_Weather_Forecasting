from datetime import datetime
from typing import Protocol

import pandas as pd


class WeatherRepository(Protocol):
    def load_archive(
        self, city: str, start_time: datetime, end_time: datetime
    ) -> pd.DataFrame: ...

    def upsert(self, df: pd.DataFrame) -> int: ...
