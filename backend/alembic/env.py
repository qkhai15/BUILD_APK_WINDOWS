from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.db import Base, DATABASE_URL
from app import models
config=context.config
config.set_main_option('sqlalchemy.url',DATABASE_URL.replace('%','%%'))
if config.config_file_name: fileConfig(config.config_file_name)
target_metadata=Base.metadata

def run_migrations_online():
    connectable=engine_from_config(config.get_section(config.config_ini_section),prefix='sqlalchemy.',poolclass=pool.NullPool)
    with connectable.connect() as conn:
        context.configure(connection=conn,target_metadata=target_metadata,compare_type=True)
        with context.begin_transaction(): context.run_migrations()

run_migrations_online()
