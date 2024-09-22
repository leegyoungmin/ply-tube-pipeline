import os
from dotenv import load_dotenv
from databases import Database
from sqlalchemy import create_engine, MetaData

load_dotenv(verbose=True, override=True)
postgres_user = os.getenv('POSTGRESQL_USERNAME')
postgres_pwd = os.getenv('POSTGRESQL_PASSWORD')
postgres_db = os.getenv('POSTGRESQL_DATABASE')

DATABASE_URL = f"postgresql://{postgres_user}:{postgres_pwd}@localhost:5430/{postgres_db}"

database = Database(DATABASE_URL)

engine = create_engine(DATABASE_URL)

