"""Create initial normalized schema (see app.models for definitions).

Revision ID: 0001_initial
Revises:
"""
from alembic import op
from app.db import Base
from app import models  # noqa
revision='0001_initial'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
