from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from dataclasses import dataclass
import numpy as np

from src.domain.exceptions.exceptions import InvalidCityException, NoDataException, InsufficientHistoryException
from src.domain.models_repository import ModelsRepository
from src.domain.cities import CITY_COORDS

from src.domain.weather_repository import WeatherRepository


@dataclass
class WeatherUseCase:
    repo: WeatherRepository
    models: ModelsRepository
    def load_archive(self, city: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        df = self.repo.load_archive(city, start_time, end_time)
        return df

    def build_features(self, city_df: pd.DataFrame, city: str) -> pd.DataFrame:
        HOURS_PER_DAY = 24
        DAYS_PER_YEAR = 365
        LAGS = [1, 2, 3, HOURS_PER_DAY, HOURS_PER_DAY * DAYS_PER_YEAR]

        def add_cyclical_features(city_df: pd.DataFrame, feature: pd.Series, period: int, name: str):
            angle = feature * (2 * np.pi / period)
            city_df[f'{name}_sin'] = np.sin(angle)
            city_df[f'{name}_cos'] = np.cos(angle)

        city_df = city_df.copy()
        city_df['ds'] = pd.to_datetime(city_df['ds'])
        city_df = city_df.sort_values(by='ds')

        city_df = city_df.set_index('ds').asfreq('h')
        smooth_cols = ['temperature_2m', 'surface_pressure', 'relative_humidity_2m']
        ffill_cols = ['wind_speed_10m', 'precipitation', 'rain', 'snowfall', 'weathercode']
        for col in smooth_cols:
            city_df[col] = city_df[col].interpolate(method='linear')
        for col in ffill_cols:
            city_df[col] = city_df[col].ffill()
        city_df['precipitation'] = city_df['precipitation'].fillna(0)
        city_df = city_df.reset_index()

        for lag in LAGS:
            city_df[f'lag_{lag}'] = city_df['temperature_2m'].shift(lag)

        add_cyclical_features(city_df, city_df['ds'].dt.month, 12, 'month')
        add_cyclical_features(city_df, city_df['ds'].dt.dayofyear, 365.25, 'day_of_year')
        add_cyclical_features(city_df, city_df['ds'].dt.hour, HOURS_PER_DAY, 'hour')

        city_df['diff_1_hour'] = city_df['lag_1'] - city_df['lag_2']
        city_df['diff_1_day'] = city_df['lag_1'] - city_df[f'lag_{HOURS_PER_DAY}']
        city_df['press_lag_3'] = city_df['surface_pressure'].shift(3)
        city_df['press_diff_3h'] = city_df['surface_pressure'] - city_df['press_lag_3']

        roll_precip = city_df['precipitation'].shift(1).rolling(window=24)
        city_df['precip_sum_24h'] = roll_precip.sum()
        roll_wind = city_df['wind_speed_10m'].shift(1).rolling(window=3)
        city_df['wind_mean_3h'] = roll_wind.mean()

        windows = [3, 24]
        for w in windows:
            roll = city_df['temperature_2m'].shift(1).rolling(window=w)
            city_df[f'roll_mean_{w}h'] = roll.mean()
            city_df[f'roll_std_{w}h'] = roll.std()
            city_df[f'roll_max_{w}h'] = roll.max()
            city_df[f'roll_min_{w}h'] = roll.min()
        city_df['current_temp'] = city_df['temperature_2m']
        for col in self.models.feature_columns:
            if col.startswith('city_'):
                city_df[col] = 0
        city_df[f'city_{city}'] = 1

        city_df = city_df.set_index('ds')
        city_df = city_df[self.models.feature_columns]
        city_df = city_df.dropna()
        return city_df


    def to_naive_local(self, city: str, time: datetime) -> datetime:
        if city not in CITY_COORDS:
            raise InvalidCityException('Невалидный Город')
        tz = ZoneInfo(CITY_COORDS[city]['timezone'])
        if time.tzinfo is not None:
            time = time.astimezone(tz)
        else:
            time = time.replace(tzinfo=tz)
        return time.replace(tzinfo=None, minute=0, second=0, microsecond=0)


    def now_in_city(self, city: str) -> datetime:
        if city not in CITY_COORDS:
            raise InvalidCityException('Невалидный Город')
        tz = CITY_COORDS[city]['timezone']
        now = datetime.now(ZoneInfo(tz)).replace(tzinfo=None)
        now = now.replace(minute=0, second=0, microsecond=0)
        return now

    def get_from_archive(self, city: str, time: datetime) -> dict:
        start_in_archive = time - timedelta(hours=1)
        end_in_archive = time + timedelta(hours=1)
        df = self.load_archive(city, start_in_archive, end_in_archive)
        time = time.replace(minute=0, second=0, microsecond=0)
        match = df.loc[df['ds'] == time, 'temperature_2m']
        if match.empty:
            raise NoDataException(f'Нет данных за {time}')
        temp = float(match.iloc[0])
        return {
            'time': [time],
            'temp': [temp],
        }


    def predict(self, city: str, end_time: datetime) -> dict:
        now = self.now_in_city(city)
        horizon_end = min(end_time, now + timedelta(hours=168))
        df = self.load_archive(city, now - timedelta(days=368), now)
        if df.empty:
            raise NoDataException(f'Нет исторических данных для города {city}')

        features = self.build_features(df, city)
        if features.empty:
            raise InsufficientHistoryException('Недостаточно истории для построения прогноза')

        last_day = features.index[-24:]
        points = []

        for day in range(1, self.models.models_count + 1):
            for hour in last_day:
                curr_time = hour + timedelta(hours=day * 24)
                if now < curr_time <= horizon_end:
                    temp = self.models.predict(day, features.loc[[hour]])
                    points.append((curr_time, temp))
        return {
            'time': [time for time, temp in points],
            'temp': [temp for time, temp in points],
        }
