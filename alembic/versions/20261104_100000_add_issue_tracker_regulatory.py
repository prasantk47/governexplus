"""Add Issue Tracker, Regulatory Intelligence tables

Revision ID: 20261104_100000
Revises: 20261102_100000
Create Date: 2026-11-04

New tables:
  - grc_issues
  - grc_issue_actions
  - regulatory_frameworks
  - regulatory_obligations
  - obligation_evidence
"""

from alembic import op
import sqlalchemy as sa

revision = '20261104_100000'
down_revision = '20261102_100000'
branch_labels = None
depends_on = None


def upgrade():
    # ── grc_issues ─────────────────────────────────────────────────────────────
    op.create_table(
        'grc_issues',
        sa.Column('issue_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('issue_type', sa.String(50), nullable=False, server_default='operational'),
        sa.Column('source_module', sa.String(50), nullable=False, server_default='manual'),
        sa.Column('severity', sa.String(50), nullable=False, server_default='medium'),
        sa.Column('status', sa.String(50), nullable=False, server_default='open'),
        sa.Column('source_record_id', sa.String(100), nullable=True),
        sa.Column('source_record_type', sa.String(100), nullable=True),
        sa.Column('owner_id', sa.String(100), nullable=True),
        sa.Column('owner_name', sa.String(200), nullable=True),
        sa.Column('assigned_by', sa.String(100), nullable=True),
        sa.Column('assigned_at', sa.DateTime, nullable=True),
        sa.Column('identified_date', sa.DateTime, nullable=True),
        sa.Column('due_date', sa.DateTime, nullable=True),
        sa.Column('closed_date', sa.DateTime, nullable=True),
        sa.Column('target_remediation_date', sa.DateTime, nullable=True),
        sa.Column('root_cause', sa.Text, nullable=True),
        sa.Column('root_cause_category', sa.String(100), nullable=True),
        sa.Column('financial_impact', sa.Integer, nullable=True),
        sa.Column('regulatory_impact', sa.Boolean, server_default='false'),
        sa.Column('reputational_impact', sa.Boolean, server_default='false'),
        sa.Column('remediation_plan', sa.Text, nullable=True),
        sa.Column('remediation_progress', sa.Integer, server_default='0'),
        sa.Column('validation_required', sa.Boolean, server_default='true'),
        sa.Column('validated_by', sa.String(100), nullable=True),
        sa.Column('validated_at', sa.DateTime, nullable=True),
        sa.Column('is_repeat', sa.Boolean, server_default='false'),
        sa.Column('repeat_count', sa.Integer, server_default='0'),
        sa.Column('previous_issue_id', sa.String(50), nullable=True),
        sa.Column('tags', sa.JSON, nullable=True),
        sa.Column('extra', sa.JSON, nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('last_updated_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_grc_issues_tenant_id', 'grc_issues', ['tenant_id'])
    op.create_index('ix_grc_issues_status', 'grc_issues', ['tenant_id', 'status'])

    # ── grc_issue_actions ──────────────────────────────────────────────────────
    op.create_table(
        'grc_issue_actions',
        sa.Column('action_id', sa.String(50), primary_key=True),
        sa.Column('issue_id', sa.String(50), sa.ForeignKey('grc_issues.issue_id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False, server_default='note'),
        sa.Column('performed_by', sa.String(100), nullable=False),
        sa.Column('performed_by_name', sa.String(200), nullable=True),
        sa.Column('performed_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('old_status', sa.String(50), nullable=True),
        sa.Column('new_status', sa.String(50), nullable=True),
        sa.Column('evidence_url', sa.String(500), nullable=True),
        sa.Column('evidence_description', sa.Text, nullable=True),
    )
    op.create_index('ix_grc_issue_actions_issue_id', 'grc_issue_actions', ['issue_id'])
    op.create_index('ix_grc_issue_actions_tenant', 'grc_issue_actions', ['tenant_id'])

    # ── regulatory_frameworks ──────────────────────────────────────────────────
    op.create_table(
        'regulatory_frameworks',
        sa.Column('framework_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(300), nullable=False),
        sa.Column('short_name', sa.String(50), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('region', sa.String(50), nullable=False, server_default='global'),
        sa.Column('effective_date', sa.DateTime, nullable=True),
        sa.Column('next_review_date', sa.DateTime, nullable=True),
        sa.Column('is_mandatory', sa.Boolean, server_default='true'),
        sa.Column('external_reference', sa.String(500), nullable=True),
        sa.Column('owner_id', sa.String(100), nullable=True),
        sa.Column('owner_name', sa.String(200), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_regulatory_frameworks_tenant', 'regulatory_frameworks', ['tenant_id'])

    # ── regulatory_obligations ─────────────────────────────────────────────────
    op.create_table(
        'regulatory_obligations',
        sa.Column('obligation_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('framework_id', sa.String(50), sa.ForeignKey('regulatory_frameworks.framework_id'), nullable=False),
        sa.Column('reference_code', sa.String(100), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('requirement_text', sa.Text, nullable=True),
        sa.Column('obligation_type', sa.String(100), nullable=True),
        sa.Column('owner_id', sa.String(100), nullable=True),
        sa.Column('owner_name', sa.String(200), nullable=True),
        sa.Column('accountable_department', sa.String(200), nullable=True),
        sa.Column('compliance_status', sa.String(50), nullable=False, server_default='not_assessed'),
        sa.Column('compliance_score', sa.Float, nullable=True),
        sa.Column('last_assessed_date', sa.DateTime, nullable=True),
        sa.Column('next_assessment_date', sa.DateTime, nullable=True),
        sa.Column('assessed_by', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('is_key_obligation', sa.Boolean, server_default='false'),
        sa.Column('penalty_risk', sa.String(50), nullable=True),
        sa.Column('evidence_summary', sa.Text, nullable=True),
        sa.Column('gaps_identified', sa.Text, nullable=True),
        sa.Column('linked_control_ids', sa.JSON, nullable=True),
        sa.Column('linked_risk_ids', sa.JSON, nullable=True),
        sa.Column('linked_policy_ids', sa.JSON, nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_regulatory_obligations_tenant', 'regulatory_obligations', ['tenant_id'])
    op.create_index('ix_regulatory_obligations_framework', 'regulatory_obligations', ['framework_id'])

    # ── obligation_evidence ────────────────────────────────────────────────────
    op.create_table(
        'obligation_evidence',
        sa.Column('evidence_id', sa.String(50), primary_key=True),
        sa.Column('obligation_id', sa.String(50), sa.ForeignKey('regulatory_obligations.obligation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('evidence_type', sa.String(100), nullable=True),
        sa.Column('file_reference', sa.String(500), nullable=True),
        sa.Column('collected_by', sa.String(100), nullable=True),
        sa.Column('collected_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('valid_until', sa.DateTime, nullable=True),
        sa.Column('is_sufficient', sa.Boolean, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_obligation_evidence_obligation', 'obligation_evidence', ['obligation_id'])


def downgrade():
    op.drop_table('obligation_evidence')
    op.drop_table('regulatory_obligations')
    op.drop_table('regulatory_frameworks')
    op.drop_table('grc_issue_actions')
    op.drop_table('grc_issues')
