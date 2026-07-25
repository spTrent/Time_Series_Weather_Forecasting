class BaseWeatherException(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class NoDataException(BaseWeatherException):
    pass


class InvalidCityException(BaseWeatherException):
    pass


class InsufficientHistoryException(BaseWeatherException):
    pass
