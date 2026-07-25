from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from src.domain.cities import CITY_COORDS
from src.domain.exceptions.exceptions import (
    InsufficientHistoryException,
    InvalidCityException,
    NoDataException,
)
from src.domain.forecast import ForecastPoint
from src.domain.models_repository import ModelsRepository
from src.domain.weather_repository import WeatherRepository
from src.features import align_hourly_grid, build_ts_features


@dataclass
class WeatherUseCase:
    repo: WeatherRepository
    models: ModelsRepository

    def load_archive(
        self, city: str, start_time: datetime, end_time: datetime
    ) -> pd.DataFrame:
        df = self.repo.load_archive(city, start_time, end_time)
        return df

    def build_features(self, city_df: pd.DataFrame, city: str) -> pd.DataFrame:
        # Числовые признаки — общий билдер (тот же, что при обучении).
        city_df = align_hourly_grid(city_df)
        city_df = build_ts_features(city_df)

        # One-hot города воспроизводим по колонкам обученной схемы.
        for col in self.models.feature_columns:
            if col.startswith('city_'):
                city_df[col] = 0
        city_df[f'city_{city}'] = 1

        city_df = city_df.set_index('ds')
        city_df = city_df[self.models.feature_columns]
        return city_df.dropna()

    def to_naive_local(self, city: str, time: datetime) -> datetime:
        if city not in CITY_COORDS:
            raise InvalidCityException('Невалидный Город')
        tz = ZoneInfo(CITY_COORDS[city]['timezone'])  # type: ignore[arg-type]
        if time.tzinfo is not None:
            time = time.astimezone(tz)
        else:
            time = time.replace(tzinfo=tz)
        return time.replace(tzinfo=None, minute=0, second=0, microsecond=0)

    def now_in_city(self, city: str) -> datetime:
        if city not in CITY_COORDS:
            raise InvalidCityException('Невалидный Город')
        tz = CITY_COORDS[city]['timezone']
        now = datetime.now(ZoneInfo(tz)).replace(tzinfo=None)  # type: ignore[arg-type]
        return now.replace(minute=0, second=0, microsecond=0)

    def get_from_archive(
        self, city: str, time: datetime
    ) -> list[ForecastPoint]:
        start_in_archive = time - timedelta(hours=1)
        end_in_archive = time + timedelta(hours=1)
        df = self.load_archive(city, start_in_archive, end_in_archive)
        time = time.replace(minute=0, second=0, microsecond=0)
        match = df.loc[df['ds'] == time, 'temperature_2m']
        if match.empty:
            raise NoDataException(f'Нет данных за {time}')
        return [ForecastPoint(ts=time, temperature=float(match.iloc[0]))]

    def predict(self, city: str, end_time: datetime) -> list[ForecastPoint]:
        now = self.now_in_city(city)
        horizon_end = min(end_time, now + timedelta(hours=168))
        df = self.load_archive(city, now - timedelta(days=368), now)
        if df.empty:
            raise NoDataException(f'Нет исторических данных для города {city}')

        features = self.build_features(df, city)
        if features.empty:
            raise InsufficientHistoryException(
                'Недостаточно истории для построения прогноза'
            )

        last_day = features.index[-24:]
        points: list[ForecastPoint] = []
        for day in range(1, self.models.models_count + 1):
            for hour in last_day:
                curr_time = hour + timedelta(hours=day * 24)
                if now < curr_time <= horizon_end:
                    temp = self.models.predict(day, features.loc[[hour]])
                    points.append(
                        ForecastPoint(
                            ts=curr_time.to_pydatetime(),
                            temperature=float(temp),
                        )
                    )
        points.sort(key=lambda p: p.ts)
        return points
