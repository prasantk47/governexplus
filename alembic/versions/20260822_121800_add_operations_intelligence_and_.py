"""Add operations intelligence and security tables

Revision ID: 508dbe6ec160
Revises: 20260117_000001
Create Date: 2026-08-22

Adds tables for:
- Operations: org_rules, bulk_jobs, sync, transports, notifications, custom tcodes,
  model templates, mitigation monitoring
- Intelligence: troubleshooter KB, role intelligence, drift, fiori, identity,
  migration, timeline, audit evidence
- Security: SAP security controls, evaluations, exceptions, system profiles
- Approvers and approval rules
- Access request audit logs
- Tenant rule preferences
- Firefighter activities
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '508dbe6ec160'
down_revision: Union[str, None] = '20260117_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ======================================================================
    # ACCESS REQUEST LOGS
    # ======================================================================
    op.create_table('access_request_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.String(length=100), nullable=False),
        sa.Column('request_type', sa.String(length=50), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('requester_user_id', sa.String(length=50), nullable=False),
        sa.Column('requester_name', sa.String(length=255), nullable=True),
        sa.Column('requester_email', sa.String(length=255), nullable=True),
        sa.Column('requester_department', sa.String(length=100), nullable=True),
        sa.Column('requester_manager', sa.String(length=50), nullable=True),
        sa.Column('target_user_id', sa.String(length=50), nullable=False),
        sa.Column('target_user_name', sa.String(length=255), nullable=True),
        sa.Column('requested_roles', sa.JSON(), nullable=True),
        sa.Column('requested_permissions', sa.JSON(), nullable=True),
        sa.Column('business_justification', sa.Text(), nullable=True),
        sa.Column('ticket_reference', sa.String(length=100), nullable=True),
        sa.Column('valid_from', sa.DateTime(), nullable=True),
        sa.Column('valid_to', sa.DateTime(), nullable=True),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('violations_detected', sa.JSON(), nullable=True),
        sa.Column('risk_accepted', sa.Boolean(), nullable=True),
        sa.Column('approval_workflow', sa.String(length=100), nullable=True),
        sa.Column('current_approval_step', sa.Integer(), nullable=True),
        sa.Column('total_approval_steps', sa.Integer(), nullable=True),
        sa.Column('approvals', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('final_approver', sa.String(length=50), nullable=True),
        sa.Column('final_decision_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('provisioned', sa.Boolean(), nullable=True),
        sa.Column('provisioned_at', sa.DateTime(), nullable=True),
        sa.Column('provisioned_by', sa.String(length=50), nullable=True),
        sa.Column('provisioning_errors', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('access_request_logs', schema=None) as batch_op:
        batch_op.create_index('ix_access_request_logs_request_id', ['request_id'], unique=True)
        batch_op.create_index('ix_access_request_logs_requester_user_id', ['requester_user_id'], unique=False)
        batch_op.create_index('ix_access_request_logs_target_user_id', ['target_user_id'], unique=False)

    # ======================================================================
    # APPROVERS & APPROVAL RULES
    # ======================================================================
    op.create_table('approvers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('approver_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('approver_type', sa.String(length=50), nullable=False),
        sa.Column('process_scope', sa.JSON(), nullable=True),
        sa.Column('system_scope', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_available', sa.Boolean(), nullable=True),
        sa.Column('is_ooo', sa.Boolean(), nullable=True),
        sa.Column('ooo_until', sa.DateTime(), nullable=True),
        sa.Column('delegate_id', sa.String(length=100), nullable=True),
        sa.Column('ooo_reason', sa.String(length=500), nullable=True),
        sa.Column('ooo_approved_by', sa.String(length=100), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('avg_response_hours', sa.Float(), nullable=True),
        sa.Column('approval_rate', sa.Float(), nullable=True),
        sa.Column('current_queue_size', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'approver_id', name='uq_tenant_approver_id')
    )
    with op.batch_alter_table('approvers', schema=None) as batch_op:
        batch_op.create_index('ix_approvers_approver_id', ['approver_id'], unique=False)
        batch_op.create_index('ix_approvers_approver_type', ['approver_type'], unique=False)
        batch_op.create_index('ix_approvers_tenant_id', ['tenant_id'], unique=False)

    op.create_table('approval_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('rule_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('layer', sa.String(length=30), nullable=False),
        sa.Column('conditions', sa.JSON(), nullable=True),
        sa.Column('approver_specs', sa.JSON(), nullable=True),
        sa.Column('sla_hours', sa.Float(), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=True),
        sa.Column('order', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_builtin', sa.Boolean(), nullable=True),
        sa.Column('created_by', sa.String(length=50), nullable=True),
        sa.Column('version', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'rule_id', name='uq_tenant_approval_rule_id')
    )
    with op.batch_alter_table('approval_rules', schema=None) as batch_op:
        batch_op.create_index('ix_approval_rules_rule_id', ['rule_id'], unique=False)
        batch_op.create_index('ix_approval_rules_tenant_id', ['tenant_id'], unique=False)

    # ======================================================================
    # TENANT RULE PREFERENCES
    # ======================================================================
    op.create_table('tenant_rule_preferences',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('builtin_rule_id', sa.String(length=50), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=True),
        sa.Column('custom_override_id', sa.Integer(), nullable=True),
        sa.Column('disabled_by', sa.String(length=50), nullable=True),
        sa.Column('disabled_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('tenant_rule_preferences', schema=None) as batch_op:
        batch_op.create_index('ix_tenant_rule_preferences_tenant_id', ['tenant_id'], unique=False)

    # ======================================================================
    # OPERATIONS TABLES
    # ======================================================================
    op.create_table('org_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('rule_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('org_field', sa.String(length=20), nullable=False),
        sa.Column('condition_type', sa.String(length=20), nullable=False),
        sa.Column('condition_value', sa.String(length=500), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('org_rules', schema=None) as batch_op:
        batch_op.create_index('ix_org_rules_rule_id', ['rule_id'], unique=True)
        batch_op.create_index('ix_org_rules_tenant_id', ['tenant_id'], unique=False)

    op.create_table('org_user_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('org_field', sa.String(length=20), nullable=False),
        sa.Column('values', sa.JSON(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('org_user_assignments', schema=None) as batch_op:
        batch_op.create_index('ix_org_user_assignments_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_org_user_assignments_user_id', ['user_id'], unique=False)

    op.create_table('org_role_restrictions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('role_id', sa.String(length=255), nullable=False),
        sa.Column('rule_ids', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('org_role_restrictions', schema=None) as batch_op:
        batch_op.create_index('ix_org_role_restrictions_role_id', ['role_id'], unique=False)
        batch_op.create_index('ix_org_role_restrictions_tenant_id', ['tenant_id'], unique=False)

    op.create_table('bulk_jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('job_id', sa.String(length=50), nullable=False),
        sa.Column('operation', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('target_users', sa.JSON(), nullable=True),
        sa.Column('total', sa.Integer(), nullable=False),
        sa.Column('processed', sa.Integer(), nullable=False),
        sa.Column('succeeded', sa.Integer(), nullable=False),
        sa.Column('failed_count', sa.Integer(), nullable=False),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('bulk_jobs', schema=None) as batch_op:
        batch_op.create_index('ix_bulk_jobs_job_id', ['job_id'], unique=True)
        batch_op.create_index('ix_bulk_jobs_tenant_id', ['tenant_id'], unique=False)

    op.create_table('sync_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('config_id', sa.String(length=50), nullable=False),
        sa.Column('system_name', sa.String(length=100), nullable=False),
        sa.Column('system_type', sa.String(length=50), nullable=False),
        sa.Column('direction', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('schedule_minutes', sa.Integer(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_status', sa.String(length=20), nullable=True),
        sa.Column('objects_synced', sa.Integer(), nullable=False),
        sa.Column('sync_scope', sa.JSON(), nullable=True),
        sa.Column('connection_config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('sync_configs', schema=None) as batch_op:
        batch_op.create_index('ix_sync_configs_config_id', ['config_id'], unique=True)
        batch_op.create_index('ix_sync_configs_tenant_id', ['tenant_id'], unique=False)

    op.create_table('sync_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('sync_id', sa.String(length=50), nullable=False),
        sa.Column('config_id', sa.String(length=50), nullable=False),
        sa.Column('system_name', sa.String(length=100), nullable=False),
        sa.Column('direction', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('objects_synced', sa.Integer(), nullable=False),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('sync_history', schema=None) as batch_op:
        batch_op.create_index('ix_sync_history_config_id', ['config_id'], unique=False)
        batch_op.create_index('ix_sync_history_sync_id', ['sync_id'], unique=True)
        batch_op.create_index('ix_sync_history_tenant_id', ['tenant_id'], unique=False)

    op.create_table('transport_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('transport_id', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('source_system', sa.String(length=50), nullable=False),
        sa.Column('target_system', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('objects', sa.JSON(), nullable=True),
        sa.Column('dependencies', sa.JSON(), nullable=True),
        sa.Column('conflicts', sa.JSON(), nullable=True),
        sa.Column('owner', sa.String(length=50), nullable=False),
        sa.Column('released_at', sa.DateTime(), nullable=True),
        sa.Column('imported_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('transport_records', schema=None) as batch_op:
        batch_op.create_index('ix_transport_records_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_transport_records_transport_id', ['transport_id'], unique=True)

    op.create_table('notification_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('notification_id', sa.String(length=50), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('recipient_id', sa.String(length=50), nullable=False),
        sa.Column('recipient_email', sa.String(length=255), nullable=True),
        sa.Column('recipient_slack_channel', sa.String(length=100), nullable=True),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('notification_records', schema=None) as batch_op:
        batch_op.create_index('ix_notification_records_notification_id', ['notification_id'], unique=True)
        batch_op.create_index('ix_notification_records_tenant_id', ['tenant_id'], unique=False)

    op.create_table('notification_preferences',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.String(length=50), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), nullable=False),
        sa.Column('slack_enabled', sa.Boolean(), nullable=False),
        sa.Column('slack_channel', sa.String(length=100), nullable=True),
        sa.Column('disabled_types', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('notification_preferences', schema=None) as batch_op:
        batch_op.create_index('ix_notification_preferences_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_notification_preferences_user_id', ['user_id'], unique=False)

    op.create_table('custom_tcodes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('tcode', sa.String(length=20), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('program', sa.String(length=100), nullable=False),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('risk_score', sa.Integer(), nullable=False),
        sa.Column('auth_objects', sa.JSON(), nullable=True),
        sa.Column('behavior_patterns', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('users_assigned', sa.Integer(), nullable=False),
        sa.Column('analyzed_at', sa.DateTime(), nullable=True),
        sa.Column('analyzed_by', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('custom_tcodes', schema=None) as batch_op:
        batch_op.create_index('ix_custom_tcodes_tcode', ['tcode'], unique=True)
        batch_op.create_index('ix_custom_tcodes_tenant_id', ['tenant_id'], unique=False)

    op.create_table('model_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('template_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('position', sa.String(length=100), nullable=False),
        sa.Column('roles', sa.JSON(), nullable=True),
        sa.Column('systems', sa.JSON(), nullable=True),
        sa.Column('compliance_rate', sa.Float(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('model_templates', schema=None) as batch_op:
        batch_op.create_index('ix_model_templates_template_id', ['template_id'], unique=True)
        batch_op.create_index('ix_model_templates_tenant_id', ['tenant_id'], unique=False)

    op.create_table('mitigation_monitor',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('monitor_id', sa.String(length=50), nullable=False),
        sa.Column('control_id', sa.String(length=50), nullable=False),
        sa.Column('control_name', sa.String(length=255), nullable=False),
        sa.Column('control_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('health_score', sa.Integer(), nullable=False),
        sa.Column('assigned_violations', sa.Integer(), nullable=False),
        sa.Column('expiry_date', sa.DateTime(), nullable=True),
        sa.Column('last_reviewed', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.String(length=50), nullable=True),
        sa.Column('last_certified', sa.DateTime(), nullable=True),
        sa.Column('certified_by', sa.String(length=50), nullable=True),
        sa.Column('owner', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('mitigation_monitor', schema=None) as batch_op:
        batch_op.create_index('ix_mitigation_monitor_control_id', ['control_id'], unique=False)
        batch_op.create_index('ix_mitigation_monitor_monitor_id', ['monitor_id'], unique=True)
        batch_op.create_index('ix_mitigation_monitor_tenant_id', ['tenant_id'], unique=False)

    # ======================================================================
    # INTELLIGENCE TABLES
    # ======================================================================
    op.create_table('troubleshooter_users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('user_ext_id', sa.String(length=20), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('valid_from', sa.DateTime(), nullable=True),
        sa.Column('valid_to', sa.DateTime(), nullable=True),
        sa.Column('roles', sa.JSON(), nullable=True),
        sa.Column('system', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('troubleshooter_users', schema=None) as batch_op:
        batch_op.create_index('ix_troubleshooter_users_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_troubleshooter_users_user_ext_id', ['user_ext_id'], unique=False)

    op.create_table('troubleshooter_roles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('role_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('role_type', sa.String(length=20), nullable=False),
        sa.Column('transactions', sa.JSON(), nullable=True),
        sa.Column('auth_objects', sa.JSON(), nullable=True),
        sa.Column('org_levels', sa.JSON(), nullable=True),
        sa.Column('systems_deployed', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('troubleshooter_roles', schema=None) as batch_op:
        batch_op.create_index('ix_troubleshooter_roles_role_name', ['role_name'], unique=False)
        batch_op.create_index('ix_troubleshooter_roles_tenant_id', ['tenant_id'], unique=False)

    op.create_table('troubleshooter_transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('tcode', sa.String(length=20), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('module', sa.String(length=20), nullable=True),
        sa.Column('is_sensitive', sa.Boolean(), nullable=False),
        sa.Column('auth_requirements', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('troubleshooter_transactions', schema=None) as batch_op:
        batch_op.create_index('ix_troubleshooter_transactions_tcode', ['tcode'], unique=True)
        batch_op.create_index('ix_troubleshooter_transactions_tenant_id', ['tenant_id'], unique=False)

    op.create_table('role_intelligence',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('role_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('role_type', sa.String(length=20), nullable=False),
        sa.Column('owner', sa.String(length=100), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('transactions', sa.JSON(), nullable=True),
        sa.Column('auth_objects', sa.JSON(), nullable=True),
        sa.Column('org_values', sa.JSON(), nullable=True),
        sa.Column('user_count', sa.Integer(), nullable=False),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('has_sod_conflicts', sa.Boolean(), nullable=False),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('naming_convention_ok', sa.Boolean(), nullable=False),
        sa.Column('system', sa.String(length=20), nullable=False),
        sa.Column('business_process', sa.String(length=50), nullable=True),
        sa.Column('is_seed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('role_intelligence', schema=None) as batch_op:
        batch_op.create_index('ix_role_intelligence_role_name', ['role_name'], unique=False)
        batch_op.create_index('ix_role_intelligence_tenant_id', ['tenant_id'], unique=False)

    op.create_table('drift_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('snapshot_id', sa.String(length=50), nullable=False),
        sa.Column('role_name', sa.String(length=100), nullable=False),
        sa.Column('system', sa.String(length=20), nullable=False),
        sa.Column('snapshot_hash', sa.String(length=64), nullable=False),
        sa.Column('transactions', sa.JSON(), nullable=True),
        sa.Column('auth_objects', sa.JSON(), nullable=True),
        sa.Column('org_levels', sa.JSON(), nullable=True),
        sa.Column('menu_nodes', sa.JSON(), nullable=True),
        sa.Column('captured_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('drift_snapshots', schema=None) as batch_op:
        batch_op.create_index('ix_drift_snapshots_role_name', ['role_name'], unique=False)
        batch_op.create_index('ix_drift_snapshots_snapshot_id', ['snapshot_id'], unique=True)
        batch_op.create_index('ix_drift_snapshots_tenant_id', ['tenant_id'], unique=False)

    op.create_table('fiori_apps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('app_id', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('catalog_id', sa.String(length=100), nullable=True),
        sa.Column('catalog_name', sa.String(length=255), nullable=True),
        sa.Column('space_id', sa.String(length=100), nullable=True),
        sa.Column('odata_services', sa.JSON(), nullable=True),
        sa.Column('backend_transactions', sa.JSON(), nullable=True),
        sa.Column('required_auth_objects', sa.JSON(), nullable=True),
        sa.Column('target_mapping_id', sa.String(length=100), nullable=True),
        sa.Column('semantic_object', sa.String(length=100), nullable=True),
        sa.Column('semantic_action', sa.String(length=100), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=True),
        sa.Column('business_area', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('fiori_apps', schema=None) as batch_op:
        batch_op.create_index('ix_fiori_apps_app_id', ['app_id'], unique=True)
        batch_op.create_index('ix_fiori_apps_tenant_id', ['tenant_id'], unique=False)

    op.create_table('identity_accounts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('account_id', sa.String(length=50), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('employee_id', sa.String(length=50), nullable=True),
        sa.Column('system_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('entitlements', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('identity_accounts', schema=None) as batch_op:
        batch_op.create_index('ix_identity_accounts_account_id', ['account_id'], unique=True)
        batch_op.create_index('ix_identity_accounts_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_identity_accounts_username', ['username'], unique=False)

    op.create_table('identity_clusters',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('cluster_id', sa.String(length=50), nullable=False),
        sa.Column('canonical_name', sa.String(length=255), nullable=False),
        sa.Column('canonical_email', sa.String(length=255), nullable=True),
        sa.Column('employee_id', sa.String(length=50), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('account_ids', sa.JSON(), nullable=False),
        sa.Column('correlation_confidence', sa.Float(), nullable=False),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('anomalies', sa.JSON(), nullable=True),
        sa.Column('last_correlated', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('identity_clusters', schema=None) as batch_op:
        batch_op.create_index('ix_identity_clusters_cluster_id', ['cluster_id'], unique=True)
        batch_op.create_index('ix_identity_clusters_tenant_id', ['tenant_id'], unique=False)

    op.create_table('migration_mappings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('ecc_tcode', sa.String(length=20), nullable=False),
        sa.Column('s4_tcode', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('fiori_app_ids', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('business_process', sa.String(length=100), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('migration_mappings', schema=None) as batch_op:
        batch_op.create_index('ix_migration_mappings_ecc_tcode', ['ecc_tcode'], unique=False)
        batch_op.create_index('ix_migration_mappings_tenant_id', ['tenant_id'], unique=False)

    op.create_table('timeline_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('event_id', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('user_ext_id', sa.String(length=50), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('target_object', sa.String(length=255), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('performed_by', sa.String(length=100), nullable=True),
        sa.Column('system', sa.String(length=50), nullable=True),
        sa.Column('event_timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('timeline_events', schema=None) as batch_op:
        batch_op.create_index('ix_timeline_events_event_id', ['event_id'], unique=True)
        batch_op.create_index('ix_timeline_events_event_timestamp', ['event_timestamp'], unique=False)
        batch_op.create_index('ix_timeline_events_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_timeline_events_user_ext_id', ['user_ext_id'], unique=False)

    op.create_table('audit_evidence',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('evidence_id', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_system', sa.String(length=100), nullable=True),
        sa.Column('compliance_framework', sa.String(length=100), nullable=True),
        sa.Column('evidence_data', sa.JSON(), nullable=True),
        sa.Column('collected_at', sa.DateTime(), nullable=False),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('audit_evidence', schema=None) as batch_op:
        batch_op.create_index('ix_audit_evidence_evidence_id', ['evidence_id'], unique=True)
        batch_op.create_index('ix_audit_evidence_tenant_id', ['tenant_id'], unique=False)

    # ======================================================================
    # SAP SECURITY CONTROLS
    # ======================================================================
    op.create_table('sap_security_controls',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('control_id', sa.String(length=50), nullable=False),
        sa.Column('control_name', sa.String(length=500), nullable=False),
        sa.Column('business_area', sa.String(length=255), nullable=False),
        sa.Column('control_type', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('purpose', sa.Text(), nullable=True),
        sa.Column('procedure', sa.Text(), nullable=True),
        sa.Column('profile_parameter', sa.String(length=255), nullable=True),
        sa.Column('expected_value', sa.Text(), nullable=True),
        sa.Column('default_risk_rating', sa.String(length=10), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('is_automated', sa.Boolean(), nullable=True),
        sa.Column('compliance_frameworks', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('sap_security_controls', schema=None) as batch_op:
        batch_op.create_index('ix_sap_controls_business_area', ['business_area'], unique=False)
        batch_op.create_index('ix_sap_controls_category', ['category'], unique=False)
        batch_op.create_index('ix_sap_controls_status', ['status'], unique=False)
        batch_op.create_index('ix_sap_security_controls_control_id', ['control_id'], unique=True)

    op.create_table('control_value_mappings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('value_condition', sa.Text(), nullable=False),
        sa.Column('value_pattern', sa.String(length=500), nullable=True),
        sa.Column('risk_rating', sa.String(length=10), nullable=False),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('evaluation_order', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['control_id'], ['sap_security_controls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('control_value_mappings', schema=None) as batch_op:
        batch_op.create_index('ix_control_value_mappings_control_id', ['control_id'], unique=False)

    op.create_table('control_exceptions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exception_id', sa.String(length=100), nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('system_id', sa.String(length=100), nullable=True),
        sa.Column('requested_by', sa.String(length=100), nullable=False),
        sa.Column('requested_date', sa.DateTime(), nullable=False),
        sa.Column('business_justification', sa.Text(), nullable=False),
        sa.Column('risk_acceptance', sa.Text(), nullable=True),
        sa.Column('compensating_controls', sa.JSON(), nullable=True),
        sa.Column('approval_status', sa.String(length=50), nullable=True),
        sa.Column('approved_by', sa.String(length=100), nullable=True),
        sa.Column('approved_date', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('valid_from', sa.DateTime(), nullable=True),
        sa.Column('valid_to', sa.DateTime(), nullable=True),
        sa.Column('is_permanent', sa.Boolean(), nullable=True),
        sa.Column('review_frequency_days', sa.Integer(), nullable=True),
        sa.Column('next_review_date', sa.DateTime(), nullable=True),
        sa.Column('last_review_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['control_id'], ['sap_security_controls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('control_exceptions', schema=None) as batch_op:
        batch_op.create_index('ix_control_exceptions_exception_id', ['exception_id'], unique=True)
        batch_op.create_index('ix_exceptions_status', ['approval_status'], unique=False)
        batch_op.create_index('ix_exceptions_validity', ['valid_from', 'valid_to'], unique=False)

    op.create_table('control_evaluations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('system_id', sa.String(length=100), nullable=False),
        sa.Column('client', sa.String(length=10), nullable=True),
        sa.Column('evaluation_id', sa.String(length=100), nullable=False),
        sa.Column('evaluation_date', sa.DateTime(), nullable=False),
        sa.Column('evaluated_by', sa.String(length=100), nullable=True),
        sa.Column('actual_value', sa.Text(), nullable=True),
        sa.Column('actual_value_details', sa.JSON(), nullable=True),
        sa.Column('risk_rating', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('finding_description', sa.Text(), nullable=True),
        sa.Column('affected_users', sa.JSON(), nullable=True),
        sa.Column('affected_count', sa.Integer(), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=True),
        sa.Column('evidence_path', sa.String(length=500), nullable=True),
        sa.Column('remediation_steps', sa.JSON(), nullable=True),
        sa.Column('remediation_deadline', sa.DateTime(), nullable=True),
        sa.Column('remediation_owner', sa.String(length=100), nullable=True),
        sa.Column('is_exception_requested', sa.Boolean(), nullable=True),
        sa.Column('exception_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['control_id'], ['sap_security_controls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['exception_id'], ['control_exceptions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('evaluation_id')
    )
    with op.batch_alter_table('control_evaluations', schema=None) as batch_op:
        batch_op.create_index('ix_control_evaluations_control_id', ['control_id'], unique=False)
        batch_op.create_index('ix_control_evaluations_evaluation_date', ['evaluation_date'], unique=False)
        batch_op.create_index('ix_control_evaluations_system_id', ['system_id'], unique=False)
        batch_op.create_index('ix_evaluations_rating', ['risk_rating'], unique=False)
        batch_op.create_index('ix_evaluations_system', ['system_id', 'evaluation_date'], unique=False)

    op.create_table('system_security_profiles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('system_id', sa.String(length=100), nullable=False),
        sa.Column('system_name', sa.String(length=255), nullable=True),
        sa.Column('system_type', sa.String(length=50), nullable=True),
        sa.Column('last_evaluation_date', sa.DateTime(), nullable=True),
        sa.Column('total_controls', sa.Integer(), nullable=True),
        sa.Column('controls_evaluated', sa.Integer(), nullable=True),
        sa.Column('green_count', sa.Integer(), nullable=True),
        sa.Column('yellow_count', sa.Integer(), nullable=True),
        sa.Column('red_count', sa.Integer(), nullable=True),
        sa.Column('security_score', sa.Float(), nullable=True),
        sa.Column('category_scores', sa.JSON(), nullable=True),
        sa.Column('compliance_status', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('system_security_profiles', schema=None) as batch_op:
        batch_op.create_index('ix_system_security_profiles_system_id', ['system_id'], unique=True)

    # ======================================================================
    # FIREFIGHTER ACTIVITIES (depends on firefighter_sessions)
    # ======================================================================
    op.create_table('firefighter_activities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('activity_id', sa.String(length=100), nullable=False),
        sa.Column('session_id', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('action_details', sa.JSON(), nullable=True),
        sa.Column('transaction_code', sa.String(length=50), nullable=True),
        sa.Column('program_name', sa.String(length=100), nullable=True),
        sa.Column('table_name', sa.String(length=100), nullable=True),
        sa.Column('client_ip', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('sap_gui_version', sa.String(length=50), nullable=True),
        sa.Column('is_sensitive', sa.Boolean(), nullable=True),
        sa.Column('requires_review', sa.Boolean(), nullable=True),
        sa.Column('risk_flag', sa.String(length=50), nullable=True),
        sa.Column('reviewed', sa.Boolean(), nullable=True),
        sa.Column('reviewer_comments', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('firefighter_activities', schema=None) as batch_op:
        batch_op.create_index('ix_firefighter_activities_activity_id', ['activity_id'], unique=True)
        batch_op.create_index('ix_firefighter_activities_timestamp', ['timestamp'], unique=False)
        batch_op.create_index('ix_firefighter_activities_transaction_code', ['transaction_code'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table('firefighter_activities')
    op.drop_table('system_security_profiles')
    op.drop_table('control_evaluations')
    op.drop_table('control_exceptions')
    op.drop_table('control_value_mappings')
    op.drop_table('sap_security_controls')
    op.drop_table('audit_evidence')
    op.drop_table('timeline_events')
    op.drop_table('migration_mappings')
    op.drop_table('identity_clusters')
    op.drop_table('identity_accounts')
    op.drop_table('fiori_apps')
    op.drop_table('drift_snapshots')
    op.drop_table('role_intelligence')
    op.drop_table('troubleshooter_transactions')
    op.drop_table('troubleshooter_roles')
    op.drop_table('troubleshooter_users')
    op.drop_table('mitigation_monitor')
    op.drop_table('model_templates')
    op.drop_table('custom_tcodes')
    op.drop_table('notification_preferences')
    op.drop_table('notification_records')
    op.drop_table('transport_records')
    op.drop_table('sync_history')
    op.drop_table('sync_configs')
    op.drop_table('bulk_jobs')
    op.drop_table('org_role_restrictions')
    op.drop_table('org_user_assignments')
    op.drop_table('org_rules')
    op.drop_table('tenant_rule_preferences')
    op.drop_table('approval_rules')
    op.drop_table('approvers')
    op.drop_table('access_request_logs')
