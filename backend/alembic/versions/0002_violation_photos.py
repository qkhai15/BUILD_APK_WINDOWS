"""Add private image evidence references.

Revision ID: 0002_violation_photos
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_violation_photos'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

def upgrade():
    # Migration 0001 dynamically creates Base.metadata tables in fresh installs.
    # Upgrading existing v0.6 databases still requires this table.
    if sa.inspect(op.get_bind()).has_table('violation_photos'):
        return
    op.create_table('violation_photos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('violation_id', sa.Integer(), sa.ForeignKey('violations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('file_key', sa.String(length=80), nullable=False, unique=True),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('byte_size', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('violation_id', 'sha256', name='uq_violation_photo_hash'),
    )
    op.create_index('ix_violation_photos_violation_id', 'violation_photos', ['violation_id'])

def downgrade():
    op.drop_index('ix_violation_photos_violation_id', table_name='violation_photos')
    op.drop_table('violation_photos')
