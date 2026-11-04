"""Add Risk Acceptance Register and Policy Exception Register tables

Revision ID: 20261104_200000
Revises: 20261104_100000
Create Date: 2026-11-04

New tables:
  - risk_acceptances
  - policy_exceptions
"""

from alembic import op
import sqlalchemy as sa


revision = '20261104_200000'
down_revision = '20261104_100000'
branch_labels = None
depends_on = None


def upgrade():
    # ── risk_acceptances ───────────────────────────────────────────────────
    op.create_table(
        'risk_acceptances',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('acceptance_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('risk_id', sa.String(100), nullable=False, index=True),
        sa.Column('risk_title', sa.String(500), nullable=True),
        sa.Column('decision', sa.String(50), nullable=False, server_default='accepted'),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('conditions', sa.Text(), nullable=True),
        sa.Column('financial_exposure', sa.Float(), nullable=True),
        sa.Column('authorized_by', sa.String(255), nullable=False),
        sa.Column('authorized_by_role', sa.String(255), nullable=True),
        sa.Column('authorized_at', sa.DateTime(), nullable=True),
        sa.Column('second_approver', sa.String(255), nullable=True),
        sa.Column('second_approved_at', sa.DateTime(), nullable=True),
        sa.Column('effective_date', sa.DateTime(), nullable=True),
        sa.Column('expiry_date', sa.DateTime(), nullable=True),
        sa.Column('renewal_reminder_days', sa.Integer(), nullable=True, server_default='30'),
        sa.Column('reviewed_by', sa.String(255), nullable=True),
        sa.Column('last_reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('next_review_date', sa.DateTime(), nullable=True),
        sa.Column('residual_score_snapshot', sa.Float(), nullable=True),
        sa.Column('risk_level_snapshot', sa.String(50), nullable=True),
        sa.Column('renewal_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_renewed_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── policy_exceptions ──────────────────────────────────────────────────
    op.create_table(
        'policy_exceptions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('exception_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('policy_id', sa.String(100), nullable=False, index=True),
        sa.Column('policy_title', sa.String(500), nullable=True),
        sa.Column('policy_section', sa.String(500), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('scope_description', sa.Text(), nullable=True),
        sa.Column('business_impact_if_denied', sa.Text(), nullable=True),
        sa.Column('exception_risk', sa.String(50), nullable=False, server_default='medium'),
        sa.Column('compensating_controls', sa.Text(), nullable=True),
        sa.Column('residual_risk_description', sa.Text(), nullable=True),
        sa.Column('requested_by', sa.String(255), nullable=False),
        sa.Column('requested_by_role', sa.String(255), nullable=True),
        sa.Column('requested_at', sa.DateTime(), nullable=True),
        sa.Column('org_unit', sa.String(255), nullable=True),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_by_role', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('second_approver', sa.String(255), nullable=True),
        sa.Column('second_approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('effective_date', sa.DateTime(), nullable=True),
        sa.Column('expiry_date', sa.DateTime(), nullable=True),
        sa.Column('duration_days', sa.Integer(), nullable=True),
        sa.Column('renewal_reminder_days', sa.Integer(), nullable=True, server_default='30'),
        sa.Column('renewal_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_renewed_at', sa.DateTime(), nullable=True),
        sa.Column('next_review_date', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.String(255), nullable=True),
        sa.Column('last_reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending_approval'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('policy_exceptions')
    op.drop_table('risk_acceptances')
