import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry
from src.db import get_engine, upsert_weather

CITY_COORDS = {
    'Москва':           {'latitude': 55.7558, 'longitude': 37.6173, 'timezone': 'Europe/Moscow'},
    'Санкт-Петербург':  {'latitude': 59.9391, 'longitude': 30.3159, 'timezone': 'Europe/Moscow'},
    'Благовещенск':     {'latitude': 50.2907, 'longitude': 127.5272, 'timezone': 'Asia/Yakutsk'},
    'Находка':          {'latitude': 42.8237, 'longitude': 132.8942, 'timezone': 'Asia/Vladivostok'},
    'Сочи':             {'latitude': 43.5855, 'longitude': 39.7231, 'timezone': 'Europe/Moscow'},
    'Геленджик':        {'latitude': 44.5612, 'longitude': 38.0766, 'timezone': 'Europe/Moscow'},
}

def get_weather_data(city: str, start_date: str, end_date: str) -> pd.DataFrame:
	"""
	:param city: str [Москва | Санкт-Петербург | Благовещенск | Находка | Сочи | Геленджик]
	:param start_date: str like "YEAR-MONTH-DAY"
	:param end_date: str like "YEAR-MONTH-DAY"
	"""
	cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
	retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
	openmeteo = openmeteo_requests.Client(session=retry_session)

	url = "https://archive-api.open-meteo.com/v1/archive"
	params = {
		"latitude": CITY_COORDS[city]['latitude'],
		"longitude": CITY_COORDS[city]['longitude'],
		"timezone": CITY_COORDS[city]['timezone'],
		"start_date": start_date,
		"end_date": end_date,
		"hourly": [
			"temperature_2m",
			"relative_humidity_2m",
			"precipitation",
			"rain",
			"snowfall",
			"weather_code",
			"wind_speed_10m",
			"surface_pressure"
		],
	}
	responses = openmeteo.weather_api(url, params=params)
	response = responses[0]
	hourly = response.Hourly()
	hourly_data = {
		"temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
		"relative_humidity_2m": hourly.Variables(1).ValuesAsNumpy(),
		"precipitation": hourly.Variables(2).ValuesAsNumpy(),
		"rain": hourly.Variables(3).ValuesAsNumpy(),
		"snowfall": hourly.Variables(4).ValuesAsNumpy(),
		"weathercode": hourly.Variables(5).ValuesAsNumpy(),
		"wind_speed_10m": hourly.Variables(6).ValuesAsNumpy(),
		"surface_pressure": hourly.Variables(7).ValuesAsNumpy(),
	}
	ds = pd.date_range(
		start=pd.to_datetime(hourly.Time(), unit='s', utc=True),
		end=pd.to_datetime(hourly.TimeEnd(), unit='s', utc=True),
		freq=pd.Timedelta(seconds=hourly.Interval()),
		inclusive='left',
	).tz_convert(CITY_COORDS[city]['timezone']).tz_localize(None)

	df = pd.DataFrame(hourly_data)
	df.insert(0, "ds", ds)
	df.insert(1, "city", city)

	df["weathercode"] = df["weathercode"].round().astype("Int16")
	return df

def main(city: str, start_date: str, end_date: str):
	df = get_weather_data(city, start_date, end_date)
	print('Добавлено строк: ', upsert_weather())
	print('NaN в температуре:', df['temperature_2m'].isna().sum())

if __name__ == "__main__":
	city = input('Введите город: ')
	start_date = input('Введите начало (Год-месяц-день): ')
	end_date = input('Введите конец (Год-месяц-день): ')
	main(city, start_date, end_date)