from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import sqlalchemy


@dataclass
class SqlAlchemyWeatherRepository:
    engine: sqlalchemy.engine.Engine

    def load_archive(
        self, city: str, start_time: datetime, end_time: datetime
    ) -> pd.DataFrame:
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
            params={
                'city': city,
                'start_time': start_time,
                'end_time': end_time,
            },
            parse_dates=['ds'],
        )
        return df

    def upsert(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0

        cols_list = ', '.join(df.columns)
        with self.engine.begin() as conn:
            df.to_sql(
                'weather_staging', conn, index=False, if_exists='replace'
            )
            result = conn.execute(
                sqlalchemy.text(
                    f'INSERT INTO weather_hourly ({cols_list}) '
                    f'SELECT {cols_list} FROM weather_staging '
                    f'ON CONFLICT (city, ds) DO NOTHING'
                )
            )
            conn.execute(
                sqlalchemy.text('DROP TABLE IF EXISTS weather_staging')
            )
        return result.rowcount
