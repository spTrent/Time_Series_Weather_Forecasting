import os
from pathlib import Path
from sqlalchemy import create_engine
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import text

load_dotenv()


MODELS_DIR = Path(__file__).resolve().parents[2] / 'Models'

def get_engine():
    user = os.getenv('POSTGRES_USER')
    password = os.getenv('POSTGRES_PASSWORD')
    db_name = os.getenv('POSTGRES_DB')
    host = os.getenv('PGDB_HOST', 'localhost')
    port = os.getenv('PGDB_PORT', '5432')
    return create_engine(f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}', pool_pre_ping=True)

def upsert_weather(df: pd.DataFrame, engine=None):
    if df.empty:
        return 0

    cols = df.columns
    cols_list = ', '.join(cols)
    engine = engine or get_engine()
    with engine.begin() as conn:
        df.to_sql('weather_staging', conn, index=False, if_exists='replace')
        result = conn.execute(
            text(f'''INSERT INTO weather_hourly ({cols_list})
                    SELECT {cols_list} FROM weather_staging
                    ON CONFLICT (city, ds) DO NOTHING'''))

        conn.execute(text("DROP TABLE IF EXISTS weather_staging"))
    return result.rowcount
