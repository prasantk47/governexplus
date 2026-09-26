"""Add MFA columns to users table

Revision ID: 20260904_120000
Revises: 20260903_100000
Create Date: 2026-09-04

Adds mfa_enabled (BOOLEAN, default False) and mfa_secret (VARCHAR 64, nullable)
to the users table to support TOTP-based Multi-Factor Authentication.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260904_120000"
down_revision = "20260903_100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("mfa_secret", sa.String(length=64), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("mfa_secret")
        batch_op.drop_column("mfa_enabled")
