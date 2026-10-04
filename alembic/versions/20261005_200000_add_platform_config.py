"""Add platform_config key-value table

Revision ID: 20261005_200000
Revises: 20261005_100000
Create Date: 2026-10-05
"""

from alembic import op
import sqlalchemy as sa

revision = '20261005_200000'
down_revision = '20261005_100000'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'platform_config',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('namespace', sa.String(100), nullable=False),
        sa.Column('config_key', sa.String(255), nullable=False),
        sa.Column('config_value', sa.JSON, nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'namespace', 'config_key', name='uq_platform_config'),
    )


def downgrade():
    op.drop_table('platform_config')
