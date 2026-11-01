"""Risk module enhancements: velocity score, contingency plan, parent risk, aggregation, workflow

Revision ID: 20261031_100000
Revises: 20261005_200000
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20261031_100000'
down_revision = '20261005_200000'
branch_labels = None
depends_on = None


def upgrade():
    # ── enterprise_risks: new fields ─────────────────────────────────────────
    op.add_column('enterprise_risks',
        sa.Column('parent_risk_id', sa.Integer(), sa.ForeignKey('enterprise_risks.id'), nullable=True))
    op.add_column('enterprise_risks',
        sa.Column('contingency_plan', sa.Text(), nullable=True))
    op.add_column('enterprise_risks',
        sa.Column('aggregated_score', sa.Float(), nullable=True))
    op.add_column('enterprise_risks',
        sa.Column('child_count', sa.Integer(), server_default='0', nullable=False))
    # velocity_numeric: computed from velocity string; stored for query performance
    op.add_column('enterprise_risks',
        sa.Column('velocity_numeric', sa.Integer(), nullable=True))
    # workflow tracking
    op.add_column('enterprise_risks',
        sa.Column('workflow_status', sa.String(50), server_default='none', nullable=False))
    op.add_column('enterprise_risks',
        sa.Column('workflow_step', sa.Integer(), server_default='0', nullable=False))

    # ── risk_workflows: approval workflow table ───────────────────────────────
    op.create_table(
        'risk_workflows',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('workflow_id', sa.String(100), nullable=False),
        sa.Column('workflow_type', sa.String(50), nullable=False),
        # risk_proposal | risk_approval | assessment_approval | response_approval
        sa.Column('object_id', sa.String(100), nullable=False),   # risk_id / assessment_id / response_id
        sa.Column('object_type', sa.String(50), nullable=False),  # risk | assessment | response
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('total_steps', sa.Integer(), server_default='3', nullable=False),
        sa.Column('current_step', sa.Integer(), server_default='1', nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        # pending | in_progress | approved | rejected | withdrawn
        sa.Column('submitted_by', sa.String(100), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('metadata_', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_risk_workflows_tenant_id', 'risk_workflows', ['tenant_id'], if_not_exists=True)
    op.create_index('ix_risk_workflows_workflow_id', 'risk_workflows', ['workflow_id'], unique=True, if_not_exists=True)
    op.create_index('ix_risk_workflows_object_id', 'risk_workflows', ['object_id'], if_not_exists=True)

    # ── risk_workflow_steps: individual approval steps ────────────────────────
    op.create_table(
        'risk_workflow_steps',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('workflow_id', sa.String(100), sa.ForeignKey('risk_workflows.workflow_id'), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('step_name', sa.String(255), nullable=True),
        sa.Column('approver_role', sa.String(100), nullable=True),
        sa.Column('approver_user_id', sa.String(100), nullable=True),
        sa.Column('approver_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        # pending | approved | rejected | delegated
        sa.Column('decision', sa.String(50), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_risk_workflow_steps_workflow_id', 'risk_workflow_steps', ['workflow_id'], if_not_exists=True)

    # ── kri_data_sources: non-SAP KRI automation ─────────────────────────────
    op.create_table(
        'kri_data_sources',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('source_id', sa.String(100), nullable=False),
        sa.Column('source_name', sa.String(255), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        # SAP_ECC | SAP_S4H | WORKDAY | SERVICENOW | SPLUNK | REST_API | DATABASE | MANUAL
        sa.Column('kri_id', sa.String(100), nullable=False),
        sa.Column('connection_config', sa.JSON(), nullable=True),
        sa.Column('query_template', sa.Text(), nullable=True),
        sa.Column('schedule_cron', sa.String(100), nullable=True),
        sa.Column('last_pulled_at', sa.DateTime(), nullable=True),
        sa.Column('last_value', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_kri_data_sources_tenant_id', 'kri_data_sources', ['tenant_id'], if_not_exists=True)
    op.create_index('ix_kri_data_sources_kri_id', 'kri_data_sources', ['kri_id'], if_not_exists=True)


def downgrade():
    op.drop_table('kri_data_sources')
    op.drop_table('risk_workflow_steps')
    op.drop_table('risk_workflows')
    op.drop_column('enterprise_risks', 'workflow_step')
    op.drop_column('enterprise_risks', 'workflow_status')
    op.drop_column('enterprise_risks', 'velocity_numeric')
    op.drop_column('enterprise_risks', 'child_count')
    op.drop_column('enterprise_risks', 'aggregated_score')
    op.drop_column('enterprise_risks', 'contingency_plan')
    op.drop_column('enterprise_risks', 'parent_risk_id')
