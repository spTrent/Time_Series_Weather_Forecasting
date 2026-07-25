from pathlib import Path

from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse, FileResponse

from src.api.models.response import WeatherResponse
from src.repositories.sqlalchemy_weather_repository import SqlAlchemyWeatherRepository
from src.repositories.xgboost_models_repository import XGBoostModelsRepository
from src.use_cases.prediction import WeatherUseCase
from src.api.config import get_engine, MODELS_DIR
from src.domain.exceptions.exceptions import (
    BaseWeatherException,
    InvalidCityException,
    NoDataException,
    InsufficientHistoryException,
)
from datetime import datetime

app = FastAPI(title='Weather Forecast')

WEATHER_EXCEPTION_STATUS = {
    InvalidCityException: 404,
    NoDataException: 404,
    InsufficientHistoryException: 422,
}


@app.exception_handler(BaseWeatherException)
def handle_weather_exception(request: Request, exc: BaseWeatherException):
    status_code = WEATHER_EXCEPTION_STATUS.get(type(exc), 400)
    return JSONResponse(status_code=status_code, content={'detail': str(exc)})

engine = get_engine()
WR = SqlAlchemyWeatherRepository(engine=engine)
MR = XGBoostModelsRepository(models_dir=str(MODELS_DIR), source='db')


FRONTEND_FILE = Path(__file__).resolve().parents[1] / 'WeatherForecast.html'


def get_weather_use_case() -> WeatherUseCase:
    return WeatherUseCase(WR, MR)

@app.get('/', include_in_schema=False)
def index():
    return FileResponse(FRONTEND_FILE)

@app.get('/weather', response_model=WeatherResponse)
def weather(city: str, time: datetime, wus: WeatherUseCase = Depends(get_weather_use_case)):
    time = wus.to_naive_local(city, time)
    if time <= wus.now_in_city(city):
        return wus.get_from_archive(city, time)
    return wus.predict(city, time)
