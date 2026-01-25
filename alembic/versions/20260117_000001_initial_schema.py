"""Initial schema for GRC Zero Trust Platform

Revision ID: 20260117_000001
Revises:
Create Date: 2026-01-17

This migration creates all core tables for the GRC platform including:
- User and role management
- Access requests and approvals
- Certification campaigns
- Firefighter/emergency access
- Audit logging
- Risk rules and violations
- Compliance management
- Multi-tenant support
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260117_000001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # MULTI-TENANT TABLES
    # ==========================================================================

    op.create_table(
        'tenants',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('domain', sa.String(255), unique=True),
        sa.Column('tier', sa.String(50), nullable=False, default='starter'),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('settings', postgresql.JSONB, default={}),
        sa.Column('limits', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('trial_ends_at', sa.DateTime, nullable=True),
        sa.Column('billing_email', sa.String(255)),
        sa.Column('admin_email', sa.String(255)),
    )

    op.create_index('ix_tenants_domain', 'tenants', ['domain'])
    op.create_index('ix_tenants_status', 'tenants', ['status'])

    # ==========================================================================
    # USER & ROLE TABLES
    # ==========================================================================

    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('username', sa.String(100)),
        sa.Column('email', sa.String(255)),
        sa.Column('first_name', sa.String(100)),
        sa.Column('last_name', sa.String(100)),
        sa.Column('full_name', sa.String(255)),
        sa.Column('department', sa.String(100)),
        sa.Column('cost_center', sa.String(50)),
        sa.Column('manager_id', sa.String(100)),
        sa.Column('employee_type', sa.String(50)),
        sa.Column('location', sa.String(100)),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('source_system', sa.String(50)),
        sa.Column('risk_score', sa.Float, default=0.0),
        sa.Column('violation_count', sa.Integer, default=0),
        sa.Column('last_login', sa.DateTime),
        sa.Column('last_synced_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'user_id', name='uq_users_tenant_user')
    )

    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('ix_users_user_id', 'users', ['user_id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_department', 'users', ['department'])
    op.create_index('ix_users_status', 'users', ['status'])

    op.create_table(
        'roles',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('role_id', sa.String(100), nullable=False),
        sa.Column('role_name', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('role_type', sa.String(50)),  # single, composite, derived
        sa.Column('source_system', sa.String(50)),
        sa.Column('risk_level', sa.String(20), default='low'),
        sa.Column('is_sensitive', sa.Boolean, default=False),
        sa.Column('owner_id', sa.String(100)),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('user_count', sa.Integer, default=0),
        sa.Column('transaction_count', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'role_id', name='uq_roles_tenant_role')
    )

    op.create_index('ix_roles_tenant_id', 'roles', ['tenant_id'])
    op.create_index('ix_roles_role_id', 'roles', ['role_id'])
    op.create_index('ix_roles_risk_level', 'roles', ['risk_level'])

    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('role_id', sa.String(100), nullable=False),
        sa.Column('source_system', sa.String(50)),
        sa.Column('valid_from', sa.DateTime),
        sa.Column('valid_to', sa.DateTime),
        sa.Column('request_id', sa.String(100)),
        sa.Column('assigned_by', sa.String(100)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'user_id', 'role_id', name='uq_user_roles_tenant_user_role')
    )

    op.create_index('ix_user_roles_tenant_id', 'user_roles', ['tenant_id'])
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'])
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'])

    op.create_table(
        'user_entitlements',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('auth_object', sa.String(100)),
        sa.Column('auth_field', sa.String(100)),
        sa.Column('auth_value', sa.String(255)),
        sa.Column('activity', sa.String(50)),
        sa.Column('source_role', sa.String(100)),
        sa.Column('source_system', sa.String(50)),
        sa.Column('is_sensitive', sa.Boolean, default=False),
        sa.Column('risk_level', sa.String(20)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index('ix_user_entitlements_tenant_id', 'user_entitlements', ['tenant_id'])
    op.create_index('ix_user_entitlements_user_id', 'user_entitlements', ['user_id'])

    # ==========================================================================
    # ACCESS REQUEST TABLES
    # ==========================================================================

    op.create_table(
        'access_requests',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('request_type', sa.String(50), nullable=False),  # role_request, role_removal, role_modification
        sa.Column('requester_id', sa.String(100), nullable=False),
        sa.Column('target_user_id', sa.String(100), nullable=False),
        sa.Column('business_justification', sa.Text),
        sa.Column('requested_roles', postgresql.JSONB, default=[]),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('risk_score', sa.Float, default=0.0),
        sa.Column('risk_level', sa.String(20)),
        sa.Column('violations', postgresql.JSONB, default=[]),
        sa.Column('priority', sa.String(20), default='normal'),
        sa.Column('valid_from', sa.DateTime),
        sa.Column('valid_to', sa.DateTime),
        sa.Column('submitted_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index('ix_access_requests_tenant_id', 'access_requests', ['tenant_id'])
    op.create_index('ix_access_requests_requester_id', 'access_requests', ['requester_id'])
    op.create_index('ix_access_requests_target_user_id', 'access_requests', ['target_user_id'])
    op.create_index('ix_access_requests_status', 'access_requests', ['status'])

    op.create_table(
        'approval_steps',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('request_id', sa.String(100), sa.ForeignKey('access_requests.id'), nullable=False),
        sa.Column('step_number', sa.Integer, nullable=False),
        sa.Column('step_type', sa.String(50)),  # manager, role_owner, risk_owner, security
        sa.Column('approver_id', sa.String(100)),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('decision', sa.String(50)),  # approved, rejected, delegated
        sa.Column('comments', sa.Text),
        sa.Column('decided_at', sa.DateTime),
        sa.Column('due_date', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index('ix_approval_steps_request_id', 'approval_steps', ['request_id'])
    op.create_index('ix_approval_steps_approver_id', 'approval_steps', ['approver_id'])
    op.create_index('ix_approval_steps_status', 'approval_steps', ['status'])

    # ==========================================================================
    # CERTIFICATION TABLES
    # ==========================================================================

    op.create_table(
        'certification_campaigns',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('campaign_type', sa.String(50)),  # user_access, role_membership, sod_violations
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('owner_id', sa.String(100)),
        sa.Column('scope', postgresql.JSONB, default={}),
        sa.Column('settings', postgresql.JSONB, default={}),
        sa.Column('start_date', sa.DateTime),
        sa.Column('end_date', sa.DateTime),
        sa.Column('reminder_frequency_days', sa.Integer, default=7),
        sa.Column('total_items', sa.Integer, default=0),
        sa.Column('completed_items', sa.Integer, default=0),
        sa.Column('certified_items', sa.Integer, default=0),
        sa.Column('revoked_items', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index('ix_certification_campaigns_tenant_id', 'certification_campaigns', ['tenant_id'])
    op.create_index('ix_certification_campaigns_status', 'certification_campaigns', ['status'])

    op.create_table(
        'certification_items',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('campaign_id', sa.String(100), sa.ForeignKey('certification_campaigns.id'), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('role_id', sa.String(100)),
        sa.Column('entitlement_type', sa.String(50)),
        sa.Column('entitlement_details', postgresql.JSONB, default={}),
        sa.Column('reviewer_id', sa.String(100)),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('decision', sa.String(50)),  # certified, revoked, modified
        sa.Column('comments', sa.Text),
        sa.Column('risk_level', sa.String(20)),
        sa.Column('last_used', sa.DateTime),
        sa.Column('decided_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index('ix_certification_items_campaign_id', 'certification_items', ['campaign_id'])
    op.create_index('ix_certification_items_reviewer_id', 'certification_items', ['reviewer_id'])
    op.create_index('ix_certification_items_status', 'certification_items', ['status'])

    # ==========================================================================
    # FIREFIGHTER TABLES
    # ==========================================================================

    op.create_table(
        'firefighter_ids',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('firefighter_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('system_id', sa.String(100)),
        sa.Column('owner_id', sa.String(100)),
        sa.Column('controller_id', sa.String(100)),
        sa.Column('risk_level', sa.String(20), default='critical'),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('max_session_hours', sa.Integer, default=8),
        sa.Column('requires_dual_approval', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'firefighter_id', name='uq_firefighter_ids_tenant_ff')
    )

    op.create_index('ix_firefighter_ids_tenant_id', 'firefighter_ids', ['tenant_id'])

    op.create_table(
        'firefighter_requests',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('firefighter_id', sa.String(100), nullable=False),
        sa.Column('requester_id', sa.String(100), nullable=False),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('reason_code', sa.String(50)),
        sa.Column('requested_hours', sa.Integer, default=4),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('approver_id', sa.String(100)),
        sa.Column('approved_at', sa.DateTime),
        sa.Column('rejection_reason', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index('ix_firefighter_requests_tenant_id', 'firefighter_requests', ['tenant_id'])
    op.create_index('ix_firefighter_requests_status', 'firefighter_requests', ['status'])

    op.create_table(
        'firefighter_sessions',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('request_id', sa.String(100), sa.ForeignKey('firefighter_requests.id'), nullable=False),
        sa.Column('firefighter_id', sa.String(100), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('started_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime),
        sa.Column('scheduled_end', sa.DateTime),
        sa.Column('activities', postgresql.JSONB, default=[]),
        sa.Column('activity_count', sa.Integer, default=0),
        sa.Column('sensitive_actions', sa.Integer, default=0),
        sa.Column('review_status', sa.String(50)),
        sa.Column('reviewed_by', sa.String(100)),
        sa.Column('reviewed_at', sa.DateTime),
        sa.Column('review_comments', sa.Text),
    )

    op.create_index('ix_firefighter_sessions_tenant_id', 'firefighter_sessions', ['tenant_id'])
    op.create_index('ix_firefighter_sessions_status', 'firefighter_sessions', ['status'])

    # ==========================================================================
    # RISK RULES & VIOLATIONS TABLES
    # ==========================================================================

    op.create_table(
        'risk_rules',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('rule_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('rule_type', sa.String(50)),  # sod, sensitive_access, critical_action
        sa.Column('module', sa.String(50)),  # FI, MM, SD, HR, BASIS
        sa.Column('risk_level', sa.String(20), default='high'),
        sa.Column('function_1', postgresql.JSONB),
        sa.Column('function_2', postgresql.JSONB),
        sa.Column('compliance_frameworks', postgresql.JSONB, default=[]),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('violation_count', sa.Integer, default=0),
        sa.Column('created_by', sa.String(100)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'rule_id', name='uq_risk_rules_tenant_rule')
    )

    op.create_index('ix_risk_rules_tenant_id', 'risk_rules', ['tenant_id'])
    op.create_index('ix_risk_rules_rule_type', 'risk_rules', ['rule_type'])
    op.create_index('ix_risk_rules_module', 'risk_rules', ['module'])

    op.create_table(
        'risk_violations',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('rule_id', sa.String(100), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('risk_level', sa.String(20)),
        sa.Column('violation_type', sa.String(50)),
        sa.Column('details', postgresql.JSONB, default={}),
        sa.Column('status', sa.String(50), default='open'),
        sa.Column('mitigation_id', sa.String(100)),
        sa.Column('remediation_action', sa.String(50)),
        sa.Column('detected_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime),
        sa.Column('resolved_by', sa.String(100)),
    )

    op.create_index('ix_risk_violations_tenant_id', 'risk_violations', ['tenant_id'])
    op.create_index('ix_risk_violations_user_id', 'risk_violations', ['user_id'])
    op.create_index('ix_risk_violations_status', 'risk_violations', ['status'])

    # ==========================================================================
    # COMPLIANCE TABLES
    # ==========================================================================

    op.create_table(
        'compliance_frameworks',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('framework_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('version', sa.String(50)),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index('ix_compliance_frameworks_tenant_id', 'compliance_frameworks', ['tenant_id'])

    op.create_table(
        'control_objectives',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('framework_id', sa.String(100), sa.ForeignKey('compliance_frameworks.id'), nullable=False),
        sa.Column('objective_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(100)),
        sa.Column('risk_rules', postgresql.JSONB, default=[]),
        sa.Column('assessment_frequency', sa.String(50)),
        sa.Column('last_assessed', sa.DateTime),
        sa.Column('compliance_status', sa.String(50)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index('ix_control_objectives_framework_id', 'control_objectives', ['framework_id'])

    # ==========================================================================
    # MITIGATION CONTROLS TABLE
    # ==========================================================================

    op.create_table(
        'mitigation_controls',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('control_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('control_type', sa.String(50)),  # preventive, detective, compensating
        sa.Column('owner_id', sa.String(100)),
        sa.Column('risk_rules', postgresql.JSONB, default=[]),
        sa.Column('assigned_users', postgresql.JSONB, default=[]),
        sa.Column('valid_from', sa.DateTime),
        sa.Column('valid_to', sa.DateTime),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('last_reviewed', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'control_id', name='uq_mitigation_controls_tenant_control')
    )

    op.create_index('ix_mitigation_controls_tenant_id', 'mitigation_controls', ['tenant_id'])

    # ==========================================================================
    # AUDIT LOG TABLE
    # ==========================================================================

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('timestamp', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('actor_user_id', sa.String(100)),
        sa.Column('actor_ip', sa.String(50)),
        sa.Column('actor_user_agent', sa.String(500)),
        sa.Column('target_type', sa.String(100)),
        sa.Column('target_id', sa.String(255)),
        sa.Column('source_system', sa.String(100)),
        sa.Column('details', postgresql.JSONB, default={}),
        sa.Column('old_values', postgresql.JSONB),
        sa.Column('new_values', postgresql.JSONB),
        sa.Column('success', sa.Boolean, default=True),
        sa.Column('error_message', sa.Text),
        sa.Column('compliance_tags', postgresql.JSONB, default=[]),
        sa.Column('retention_period_days', sa.Integer, default=2555),  # 7 years
    )

    op.create_index('ix_audit_logs_tenant_id', 'audit_logs', ['tenant_id'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_actor_user_id', 'audit_logs', ['actor_user_id'])
    op.create_index('ix_audit_logs_target', 'audit_logs', ['target_type', 'target_id'])

    # ==========================================================================
    # WORKFLOW TABLES
    # ==========================================================================

    op.create_table(
        'workflow_definitions',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('workflow_type', sa.String(50)),  # access_request, certification, firefighter
        sa.Column('trigger_conditions', postgresql.JSONB, default={}),
        sa.Column('steps', postgresql.JSONB, default=[]),
        sa.Column('escalation_rules', postgresql.JSONB, default={}),
        sa.Column('sla_hours', sa.Integer, default=48),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('version', sa.Integer, default=1),
        sa.Column('created_by', sa.String(100)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index('ix_workflow_definitions_tenant_id', 'workflow_definitions', ['tenant_id'])

    # ==========================================================================
    # NOTIFICATION TABLES
    # ==========================================================================

    op.create_table(
        'notification_templates',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('template_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('event_type', sa.String(100)),
        sa.Column('channel', sa.String(50)),  # email, slack, teams, webhook
        sa.Column('subject', sa.String(500)),
        sa.Column('body', sa.Text),
        sa.Column('variables', postgresql.JSONB, default=[]),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'template_id', name='uq_notification_templates_tenant_template')
    )

    op.create_index('ix_notification_templates_tenant_id', 'notification_templates', ['tenant_id'])
    op.create_index('ix_notification_templates_event_type', 'notification_templates', ['event_type'])

    op.create_table(
        'notification_logs',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('template_id', sa.String(100)),
        sa.Column('recipient', sa.String(255)),
        sa.Column('channel', sa.String(50)),
        sa.Column('subject', sa.String(500)),
        sa.Column('status', sa.String(50)),
        sa.Column('sent_at', sa.DateTime),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index('ix_notification_logs_tenant_id', 'notification_logs', ['tenant_id'])

    # ==========================================================================
    # SYSTEM CONFIGURATION TABLES
    # ==========================================================================

    op.create_table(
        'connected_systems',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('system_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('system_type', sa.String(50)),  # sap_ecc, sap_s4, azure_ad, etc.
        sa.Column('connection_type', sa.String(50)),  # rfc, rest, database, ldap
        sa.Column('connection_config', postgresql.JSONB, default={}),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('last_sync', sa.DateTime),
        sa.Column('sync_frequency_minutes', sa.Integer, default=60),
        sa.Column('user_count', sa.Integer, default=0),
        sa.Column('role_count', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'system_id', name='uq_connected_systems_tenant_system')
    )

    op.create_index('ix_connected_systems_tenant_id', 'connected_systems', ['tenant_id'])

    # ==========================================================================
    # BILLING TABLES
    # ==========================================================================

    op.create_table(
        'usage_records',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('metric', sa.String(100), nullable=False),
        sa.Column('value', sa.Float, nullable=False),
        sa.Column('unit', sa.String(50)),
        sa.Column('period_start', sa.DateTime),
        sa.Column('period_end', sa.DateTime),
        sa.Column('recorded_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index('ix_usage_records_tenant_id', 'usage_records', ['tenant_id'])
    op.create_index('ix_usage_records_period', 'usage_records', ['period_start', 'period_end'])

    op.create_table(
        'invoices',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(50), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('invoice_number', sa.String(100), nullable=False),
        sa.Column('period_start', sa.Date),
        sa.Column('period_end', sa.Date),
        sa.Column('subtotal', sa.Numeric(12, 2)),
        sa.Column('tax', sa.Numeric(12, 2)),
        sa.Column('total', sa.Numeric(12, 2)),
        sa.Column('currency', sa.String(10), default='USD'),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('due_date', sa.Date),
        sa.Column('paid_at', sa.DateTime),
        sa.Column('line_items', postgresql.JSONB, default=[]),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index('ix_invoices_tenant_id', 'invoices', ['tenant_id'])


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table('invoices')
    op.drop_table('usage_records')
    op.drop_table('connected_systems')
    op.drop_table('notification_logs')
    op.drop_table('notification_templates')
    op.drop_table('workflow_definitions')
    op.drop_table('audit_logs')
    op.drop_table('mitigation_controls')
    op.drop_table('control_objectives')
    op.drop_table('compliance_frameworks')
    op.drop_table('risk_violations')
    op.drop_table('risk_rules')
    op.drop_table('firefighter_sessions')
    op.drop_table('firefighter_requests')
    op.drop_table('firefighter_ids')
    op.drop_table('certification_items')
    op.drop_table('certification_campaigns')
    op.drop_table('approval_steps')
    op.drop_table('access_requests')
    op.drop_table('user_entitlements')
    op.drop_table('user_roles')
    op.drop_table('roles')
    op.drop_table('users')
    op.drop_table('tenants')
