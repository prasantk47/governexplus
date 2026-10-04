"""Add extended modules (JML, TPRM, Fraud, BCM, Whistleblower, Survey)

Revision ID: 20261004_100000
Revises: 20260918_100000
Create Date: 2026-10-04

Creates all tables for the six new extended GRC modules:

JML (Joiner-Mover-Leaver):
  - jml_policies
  - jml_events

TPRM (Third-Party Risk Management):
  - vendors
  - vendor_assessments
  - vendor_issues
  - vendor_contracts

Fraud Detection:
  - fraud_rules
  - fraud_alerts
  - fraud_cases

BCM (Business Continuity Management):
  - bia_records
  - bcm_plans
  - bcm_test_exercises
  - incident_activations

Whistleblower:
  - whistleblower_cases
  - whistleblower_messages

Survey (standalone):
  - standalone_surveys
  - survey_distributions
  - survey_answers
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261004_100000'
down_revision: Union[str, None] = '20260918_100000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ==========================================================================
    # JML — JOINER / MOVER / LEAVER
    # ==========================================================================

    # --------------------------------------------------------------------------
    # jml_policies
    # --------------------------------------------------------------------------
    op.create_table(
        'jml_policies',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('policy_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('org_unit', sa.String(length=255), nullable=True),
        sa.Column('position_criteria', sa.JSON(), nullable=True),
        sa.Column('birthright_roles', sa.JSON(), nullable=True),
        sa.Column('actions', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('jml_policies', schema=None) as batch_op:
        batch_op.create_index('ix_jml_policies_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_jml_policies_event_type', ['event_type'], unique=False)

    # --------------------------------------------------------------------------
    # jml_events
    # --------------------------------------------------------------------------
    op.create_table(
        'jml_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('employee_id', sa.String(length=100), nullable=False),
        sa.Column('employee_name', sa.String(length=255), nullable=True),
        sa.Column('old_position', sa.String(length=255), nullable=True),
        sa.Column('new_position', sa.String(length=255), nullable=True),
        sa.Column('old_org_unit', sa.String(length=255), nullable=True),
        sa.Column('new_org_unit', sa.String(length=255), nullable=True),
        sa.Column('effective_date', sa.DateTime(), nullable=True),
        sa.Column('hr_system', sa.String(length=100), nullable=True),
        sa.Column('raw_payload', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
        sa.Column('matched_policy_id', sa.String(length=36), nullable=True),
        sa.Column('actions_taken', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('jml_events', schema=None) as batch_op:
        batch_op.create_index('ix_jml_events_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_jml_events_event_type', ['event_type'], unique=False)
        batch_op.create_index('ix_jml_events_employee_id', ['employee_id'], unique=False)
        batch_op.create_index('ix_jml_events_status', ['status'], unique=False)
        batch_op.create_index('ix_jml_events_matched_policy_id', ['matched_policy_id'], unique=False)

    # ==========================================================================
    # TPRM — THIRD-PARTY RISK MANAGEMENT
    # ==========================================================================

    # --------------------------------------------------------------------------
    # vendors
    # --------------------------------------------------------------------------
    op.create_table(
        'vendors',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('vendor_name', sa.String(length=255), nullable=False),
        sa.Column('vendor_code', sa.String(length=100), nullable=True),
        sa.Column('tier', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='active'),
        sa.Column('primary_contact', sa.String(length=255), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('services_provided', sa.JSON(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('last_assessment_date', sa.DateTime(), nullable=True),
        sa.Column('next_assessment_date', sa.DateTime(), nullable=True),
        sa.Column('contract_expiry', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('vendors', schema=None) as batch_op:
        batch_op.create_index('ix_vendors_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_vendors_vendor_code', ['vendor_code'], unique=False)
        batch_op.create_index('ix_vendors_status', ['status'], unique=False)

    # --------------------------------------------------------------------------
    # vendor_assessments
    # --------------------------------------------------------------------------
    op.create_table(
        'vendor_assessments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('vendor_id', sa.String(length=36), nullable=False),
        sa.Column('assessment_name', sa.String(length=255), nullable=False),
        sa.Column('questionnaire_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('sent_date', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('completed_date', sa.DateTime(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('risk_rating', sa.String(length=10), nullable=True),
        sa.Column('responses', sa.JSON(), nullable=True),
        sa.Column('assessor', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('vendor_assessments', schema=None) as batch_op:
        batch_op.create_index('ix_vendor_assessments_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_vendor_assessments_vendor_id', ['vendor_id'], unique=False)
        batch_op.create_index('ix_vendor_assessments_questionnaire_id', ['questionnaire_id'], unique=False)
        batch_op.create_index('ix_vendor_assessments_status', ['status'], unique=False)

    # --------------------------------------------------------------------------
    # vendor_issues
    # --------------------------------------------------------------------------
    op.create_table(
        'vendor_issues',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('vendor_id', sa.String(length=36), nullable=False),
        sa.Column('issue_title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='open'),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('owner', sa.String(length=100), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('closed_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('vendor_issues', schema=None) as batch_op:
        batch_op.create_index('ix_vendor_issues_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_vendor_issues_vendor_id', ['vendor_id'], unique=False)
        batch_op.create_index('ix_vendor_issues_severity', ['severity'], unique=False)
        batch_op.create_index('ix_vendor_issues_status', ['status'], unique=False)

    # --------------------------------------------------------------------------
    # vendor_contracts
    # --------------------------------------------------------------------------
    op.create_table(
        'vendor_contracts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('vendor_id', sa.String(length=36), nullable=False),
        sa.Column('contract_name', sa.String(length=255), nullable=False),
        sa.Column('contract_type', sa.String(length=100), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('auto_renew', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('notice_period_days', sa.Integer(), nullable=True),
        sa.Column('key_slas', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('vendor_contracts', schema=None) as batch_op:
        batch_op.create_index('ix_vendor_contracts_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_vendor_contracts_vendor_id', ['vendor_id'], unique=False)
        batch_op.create_index('ix_vendor_contracts_status', ['status'], unique=False)

    # ==========================================================================
    # FRAUD DETECTION
    # ==========================================================================

    # --------------------------------------------------------------------------
    # fraud_rules
    # --------------------------------------------------------------------------
    op.create_table(
        'fraud_rules',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('rule_name', sa.String(length=255), nullable=False),
        sa.Column('rule_type', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('conditions', sa.JSON(), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('alert_on_breach', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('last_triggered_at', sa.DateTime(), nullable=True),
        sa.Column('trigger_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('fraud_rules', schema=None) as batch_op:
        batch_op.create_index('ix_fraud_rules_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_fraud_rules_rule_type', ['rule_type'], unique=False)

    # --------------------------------------------------------------------------
    # fraud_alerts
    # --------------------------------------------------------------------------
    op.create_table(
        'fraud_alerts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('rule_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=True),
        sa.Column('system_id', sa.String(length=100), nullable=True),
        sa.Column('alert_type', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='open'),
        sa.Column('triggered_at', sa.DateTime(), nullable=False),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('case_id', sa.String(length=36), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('fraud_alerts', schema=None) as batch_op:
        batch_op.create_index('ix_fraud_alerts_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_fraud_alerts_rule_id', ['rule_id'], unique=False)
        batch_op.create_index('ix_fraud_alerts_user_id', ['user_id'], unique=False)
        batch_op.create_index('ix_fraud_alerts_status', ['status'], unique=False)
        batch_op.create_index('ix_fraud_alerts_case_id', ['case_id'], unique=False)

    # --------------------------------------------------------------------------
    # fraud_cases
    # --------------------------------------------------------------------------
    op.create_table(
        'fraud_cases',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('case_reference', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('assigned_to', sa.String(length=100), nullable=True),
        sa.Column('linked_alert_ids', sa.JSON(), nullable=True),
        sa.Column('linked_finding_id', sa.String(length=100), nullable=True),
        sa.Column('opened_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('outcome', sa.Text(), nullable=True),
        sa.Column('loss_amount', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('fraud_cases', schema=None) as batch_op:
        batch_op.create_index('ix_fraud_cases_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_fraud_cases_case_reference', ['case_reference'], unique=False)
        batch_op.create_index('ix_fraud_cases_severity', ['severity'], unique=False)
        batch_op.create_index('ix_fraud_cases_status', ['status'], unique=False)

    # ==========================================================================
    # BCM — BUSINESS CONTINUITY MANAGEMENT
    # ==========================================================================

    # --------------------------------------------------------------------------
    # bia_records
    # --------------------------------------------------------------------------
    op.create_table(
        'bia_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('process_name', sa.String(length=500), nullable=False),
        sa.Column('process_owner', sa.String(length=255), nullable=True),
        sa.Column('criticality', sa.String(length=20), nullable=False),
        sa.Column('rto_hours', sa.Float(), nullable=True),
        sa.Column('rpo_hours', sa.Float(), nullable=True),
        sa.Column('mtpd_hours', sa.Float(), nullable=True),
        sa.Column('dependencies', sa.JSON(), nullable=True),
        sa.Column('recovery_strategy', sa.Text(), nullable=True),
        sa.Column('impact_description', sa.Text(), nullable=True),
        sa.Column('last_reviewed', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('bia_records', schema=None) as batch_op:
        batch_op.create_index('ix_bia_records_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_bia_records_criticality', ['criticality'], unique=False)

    # --------------------------------------------------------------------------
    # bcm_plans
    # --------------------------------------------------------------------------
    op.create_table(
        'bcm_plans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('plan_name', sa.String(length=255), nullable=False),
        sa.Column('plan_type', sa.String(length=20), nullable=False),
        sa.Column('scope', sa.Text(), nullable=True),
        sa.Column('owner', sa.String(length=100), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=True, server_default='1.0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('last_tested', sa.DateTime(), nullable=True),
        sa.Column('next_test_date', sa.DateTime(), nullable=True),
        sa.Column('call_tree', sa.JSON(), nullable=True),
        sa.Column('recovery_steps', sa.JSON(), nullable=True),
        sa.Column('approved_by', sa.String(length=100), nullable=True),
        sa.Column('approved_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('bcm_plans', schema=None) as batch_op:
        batch_op.create_index('ix_bcm_plans_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_bcm_plans_plan_type', ['plan_type'], unique=False)
        batch_op.create_index('ix_bcm_plans_status', ['status'], unique=False)

    # --------------------------------------------------------------------------
    # bcm_test_exercises
    # --------------------------------------------------------------------------
    op.create_table(
        'bcm_test_exercises',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('plan_id', sa.String(length=36), nullable=False),
        sa.Column('exercise_name', sa.String(length=255), nullable=False),
        sa.Column('exercise_type', sa.String(length=20), nullable=False),
        sa.Column('scheduled_date', sa.DateTime(), nullable=True),
        sa.Column('completed_date', sa.DateTime(), nullable=True),
        sa.Column('facilitator', sa.String(length=100), nullable=True),
        sa.Column('participants', sa.JSON(), nullable=True),
        sa.Column('outcome', sa.String(length=20), nullable=True),
        sa.Column('findings', sa.Text(), nullable=True),
        sa.Column('lessons_learned', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('bcm_test_exercises', schema=None) as batch_op:
        batch_op.create_index('ix_bcm_test_exercises_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_bcm_test_exercises_plan_id', ['plan_id'], unique=False)

    # --------------------------------------------------------------------------
    # incident_activations
    # --------------------------------------------------------------------------
    op.create_table(
        'incident_activations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('activation_name', sa.String(length=255), nullable=False),
        sa.Column('plan_id', sa.String(length=36), nullable=False),
        sa.Column('activated_by', sa.String(length=100), nullable=False),
        sa.Column('activation_reason', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('activated_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('impacted_processes', sa.JSON(), nullable=True),
        sa.Column('timeline_events', sa.JSON(), nullable=True),
        sa.Column('communications_log', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('incident_activations', schema=None) as batch_op:
        batch_op.create_index('ix_incident_activations_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_incident_activations_plan_id', ['plan_id'], unique=False)
        batch_op.create_index('ix_incident_activations_severity', ['severity'], unique=False)
        batch_op.create_index('ix_incident_activations_status', ['status'], unique=False)

    # ==========================================================================
    # WHISTLEBLOWER
    # ==========================================================================

    # --------------------------------------------------------------------------
    # whistleblower_cases
    # --------------------------------------------------------------------------
    op.create_table(
        'whistleblower_cases',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('case_reference', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=30), nullable=False),
        sa.Column('submission_channel', sa.String(length=50), nullable=True),
        sa.Column('summary', sa.String(length=1000), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('is_anonymous', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('submitter_email', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('assigned_to', sa.String(length=100), nullable=True),
        sa.Column('priority', sa.String(length=10), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_reference', name='uq_whistleblower_cases_case_reference'),
    )
    with op.batch_alter_table('whistleblower_cases', schema=None) as batch_op:
        batch_op.create_index('ix_whistleblower_cases_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_whistleblower_cases_case_reference', ['case_reference'], unique=True)
        batch_op.create_index('ix_whistleblower_cases_category', ['category'], unique=False)
        batch_op.create_index('ix_whistleblower_cases_status', ['status'], unique=False)

    # --------------------------------------------------------------------------
    # whistleblower_messages
    # --------------------------------------------------------------------------
    op.create_table(
        'whistleblower_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('case_id', sa.String(length=36), nullable=False),
        sa.Column('sender', sa.String(length=20), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('whistleblower_messages', schema=None) as batch_op:
        batch_op.create_index('ix_whistleblower_messages_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_whistleblower_messages_case_id', ['case_id'], unique=False)

    # ==========================================================================
    # SURVEY (STANDALONE)
    # ==========================================================================

    # --------------------------------------------------------------------------
    # standalone_surveys
    # --------------------------------------------------------------------------
    op.create_table(
        'standalone_surveys',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('survey_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('survey_type', sa.String(length=40), nullable=False),
        sa.Column('questions', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('survey_created_at', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('allow_anonymous', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('standalone_surveys', schema=None) as batch_op:
        batch_op.create_index('ix_standalone_surveys_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_standalone_surveys_survey_type', ['survey_type'], unique=False)
        batch_op.create_index('ix_standalone_surveys_status', ['status'], unique=False)

    # --------------------------------------------------------------------------
    # survey_distributions
    # --------------------------------------------------------------------------
    op.create_table(
        'survey_distributions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('survey_id', sa.String(length=36), nullable=False),
        sa.Column('recipient_id', sa.String(length=100), nullable=True),
        sa.Column('recipient_email', sa.String(length=255), nullable=True),
        sa.Column('recipient_name', sa.String(length=255), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('reminder_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_reminder_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('survey_distributions', schema=None) as batch_op:
        batch_op.create_index('ix_survey_distributions_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_survey_distributions_survey_id', ['survey_id'], unique=False)
        batch_op.create_index('ix_survey_distributions_recipient_id', ['recipient_id'], unique=False)
        batch_op.create_index('ix_survey_distributions_status', ['status'], unique=False)

    # --------------------------------------------------------------------------
    # survey_answers
    # --------------------------------------------------------------------------
    op.create_table(
        'survey_answers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('distribution_id', sa.String(length=36), nullable=False),
        sa.Column('survey_id', sa.String(length=36), nullable=False),
        sa.Column('respondent_id', sa.String(length=100), nullable=True),
        sa.Column('respondent_email', sa.String(length=255), nullable=True),
        sa.Column('responses', sa.JSON(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('is_anonymous', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('survey_answers', schema=None) as batch_op:
        batch_op.create_index('ix_survey_answers_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_survey_answers_distribution_id', ['distribution_id'], unique=False)
        batch_op.create_index('ix_survey_answers_survey_id', ['survey_id'], unique=False)
        batch_op.create_index('ix_survey_answers_respondent_id', ['respondent_id'], unique=False)


def downgrade() -> None:
    # Drop in strict reverse dependency order

    # Survey
    with op.batch_alter_table('survey_answers', schema=None) as batch_op:
        batch_op.drop_index('ix_survey_answers_respondent_id')
        batch_op.drop_index('ix_survey_answers_survey_id')
        batch_op.drop_index('ix_survey_answers_distribution_id')
        batch_op.drop_index('ix_survey_answers_tenant_id')
    op.drop_table('survey_answers')

    with op.batch_alter_table('survey_distributions', schema=None) as batch_op:
        batch_op.drop_index('ix_survey_distributions_status')
        batch_op.drop_index('ix_survey_distributions_recipient_id')
        batch_op.drop_index('ix_survey_distributions_survey_id')
        batch_op.drop_index('ix_survey_distributions_tenant_id')
    op.drop_table('survey_distributions')

    with op.batch_alter_table('standalone_surveys', schema=None) as batch_op:
        batch_op.drop_index('ix_standalone_surveys_status')
        batch_op.drop_index('ix_standalone_surveys_survey_type')
        batch_op.drop_index('ix_standalone_surveys_tenant_id')
    op.drop_table('standalone_surveys')

    # Whistleblower
    with op.batch_alter_table('whistleblower_messages', schema=None) as batch_op:
        batch_op.drop_index('ix_whistleblower_messages_case_id')
        batch_op.drop_index('ix_whistleblower_messages_tenant_id')
    op.drop_table('whistleblower_messages')

    with op.batch_alter_table('whistleblower_cases', schema=None) as batch_op:
        batch_op.drop_index('ix_whistleblower_cases_status')
        batch_op.drop_index('ix_whistleblower_cases_category')
        batch_op.drop_index('ix_whistleblower_cases_case_reference')
        batch_op.drop_index('ix_whistleblower_cases_tenant_id')
    op.drop_table('whistleblower_cases')

    # BCM
    with op.batch_alter_table('incident_activations', schema=None) as batch_op:
        batch_op.drop_index('ix_incident_activations_status')
        batch_op.drop_index('ix_incident_activations_severity')
        batch_op.drop_index('ix_incident_activations_plan_id')
        batch_op.drop_index('ix_incident_activations_tenant_id')
    op.drop_table('incident_activations')

    with op.batch_alter_table('bcm_test_exercises', schema=None) as batch_op:
        batch_op.drop_index('ix_bcm_test_exercises_plan_id')
        batch_op.drop_index('ix_bcm_test_exercises_tenant_id')
    op.drop_table('bcm_test_exercises')

    with op.batch_alter_table('bcm_plans', schema=None) as batch_op:
        batch_op.drop_index('ix_bcm_plans_status')
        batch_op.drop_index('ix_bcm_plans_plan_type')
        batch_op.drop_index('ix_bcm_plans_tenant_id')
    op.drop_table('bcm_plans')

    with op.batch_alter_table('bia_records', schema=None) as batch_op:
        batch_op.drop_index('ix_bia_records_criticality')
        batch_op.drop_index('ix_bia_records_tenant_id')
    op.drop_table('bia_records')

    # Fraud Detection
    with op.batch_alter_table('fraud_cases', schema=None) as batch_op:
        batch_op.drop_index('ix_fraud_cases_status')
        batch_op.drop_index('ix_fraud_cases_severity')
        batch_op.drop_index('ix_fraud_cases_case_reference')
        batch_op.drop_index('ix_fraud_cases_tenant_id')
    op.drop_table('fraud_cases')

    with op.batch_alter_table('fraud_alerts', schema=None) as batch_op:
        batch_op.drop_index('ix_fraud_alerts_case_id')
        batch_op.drop_index('ix_fraud_alerts_status')
        batch_op.drop_index('ix_fraud_alerts_user_id')
        batch_op.drop_index('ix_fraud_alerts_rule_id')
        batch_op.drop_index('ix_fraud_alerts_tenant_id')
    op.drop_table('fraud_alerts')

    with op.batch_alter_table('fraud_rules', schema=None) as batch_op:
        batch_op.drop_index('ix_fraud_rules_rule_type')
        batch_op.drop_index('ix_fraud_rules_tenant_id')
    op.drop_table('fraud_rules')

    # TPRM
    with op.batch_alter_table('vendor_contracts', schema=None) as batch_op:
        batch_op.drop_index('ix_vendor_contracts_status')
        batch_op.drop_index('ix_vendor_contracts_vendor_id')
        batch_op.drop_index('ix_vendor_contracts_tenant_id')
    op.drop_table('vendor_contracts')

    with op.batch_alter_table('vendor_issues', schema=None) as batch_op:
        batch_op.drop_index('ix_vendor_issues_status')
        batch_op.drop_index('ix_vendor_issues_severity')
        batch_op.drop_index('ix_vendor_issues_vendor_id')
        batch_op.drop_index('ix_vendor_issues_tenant_id')
    op.drop_table('vendor_issues')

    with op.batch_alter_table('vendor_assessments', schema=None) as batch_op:
        batch_op.drop_index('ix_vendor_assessments_status')
        batch_op.drop_index('ix_vendor_assessments_questionnaire_id')
        batch_op.drop_index('ix_vendor_assessments_vendor_id')
        batch_op.drop_index('ix_vendor_assessments_tenant_id')
    op.drop_table('vendor_assessments')

    with op.batch_alter_table('vendors', schema=None) as batch_op:
        batch_op.drop_index('ix_vendors_status')
        batch_op.drop_index('ix_vendors_vendor_code')
        batch_op.drop_index('ix_vendors_tenant_id')
    op.drop_table('vendors')

    # JML
    with op.batch_alter_table('jml_events', schema=None) as batch_op:
        batch_op.drop_index('ix_jml_events_matched_policy_id')
        batch_op.drop_index('ix_jml_events_status')
        batch_op.drop_index('ix_jml_events_employee_id')
        batch_op.drop_index('ix_jml_events_event_type')
        batch_op.drop_index('ix_jml_events_tenant_id')
    op.drop_table('jml_events')

    with op.batch_alter_table('jml_policies', schema=None) as batch_op:
        batch_op.drop_index('ix_jml_policies_event_type')
        batch_op.drop_index('ix_jml_policies_tenant_id')
    op.drop_table('jml_policies')
