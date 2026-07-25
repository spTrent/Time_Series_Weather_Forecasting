import sqlalchemy
import pandas as pd
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SqlAlchemyWeatherRepository:
    engine: sqlalchemy.engine.Engine

    def load_archive(self, city: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        query = sqlalchemy.text("""
        SELECT city, ds, temperature_2m, relative_humidity_2m,
               precipitation, rain, snowfall, weathercode,
               wind_speed_10m, surface_pressure
        FROM weather_hourly
        WHERE city = :city AND ds >= :start_time AND ds <= :end_time
        ORDER BY ds
        """)
        df = pd.read_sql(
            query,
            self.engine,
            params={'city': city, 'start_time': start_time, 'end_time': end_time},
            parse_dates=['ds']
        )
        return df
