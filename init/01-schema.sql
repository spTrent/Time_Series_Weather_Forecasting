CREATE TABLE IF NOT EXISTS weather_hourly (
    CITY    TEXT    NOT NULL,
    ds  TIMESTAMP   NOT NULL,
    temperature_2m        DOUBLE PRECISION,
    relative_humidity_2m  DOUBLE PRECISION,
    precipitation         DOUBLE PRECISION,
    rain                  DOUBLE PRECISION,
    snowfall              DOUBLE PRECISION,
    weathercode           SMALLINT,
    wind_speed_10m        DOUBLE PRECISION,
    surface_pressure      DOUBLE PRECISION,
    PRIMARY KEY (city, ds)
);
