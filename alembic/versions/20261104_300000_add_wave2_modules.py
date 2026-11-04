"""Add Wave 2 GRC modules: SOX/ICFR, Privacy/GDPR, Governance Extended

Revision ID: 20261104_300000
Revises: 20261104_200000
Create Date: 2026-11-04

New tables:
  - icfr_controls
  - sox_signoffs
  - financial_close_tasks
  - data_processing_activities
  - dsar_requests
  - dpia_assessments
  - data_breach_incidents
  - regulatory_changes
  - operational_loss_events
  - sod_remediations
  - it_change_risks
  - insurance_policies
  - sanctions_screenings
"""

from alembic import op
import sqlalchemy as sa


revision = '20261104_300000'
down_revision = '20261104_200000'
branch_labels = None
depends_on = None


def upgrade():
    # ── icfr_controls ──────────────────────────────────────────────────────
    op.create_table(
        'icfr_controls',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('control_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('control_type', sa.String(50), nullable=False, server_default='process_level'),
        sa.Column('frequency', sa.String(50), nullable=False, server_default='monthly'),
        sa.Column('financial_statement_area', sa.String(255), nullable=True),
        sa.Column('assertions', sa.JSON(), nullable=True),
        sa.Column('account_codes', sa.JSON(), nullable=True),
        sa.Column('process_name', sa.String(255), nullable=True),
        sa.Column('sub_process', sa.String(255), nullable=True),
        sa.Column('control_owner', sa.String(255), nullable=True),
        sa.Column('control_performer', sa.String(255), nullable=True),
        sa.Column('reviewer', sa.String(255), nullable=True),
        sa.Column('design_effectiveness', sa.String(50), nullable=True),
        sa.Column('operating_effectiveness', sa.String(50), nullable=True),
        sa.Column('overall_effectiveness', sa.String(50), nullable=True, server_default='not_tested'),
        sa.Column('deficiency_type', sa.String(50), nullable=True),
        sa.Column('deficiency_description', sa.Text(), nullable=True),
        sa.Column('remediation_plan', sa.Text(), nullable=True),
        sa.Column('remediation_due_date', sa.DateTime(), nullable=True),
        sa.Column('remediation_status', sa.String(50), nullable=True),
        sa.Column('sox_section', sa.String(20), nullable=True),
        sa.Column('is_key_control', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_automated', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('evidence_requirements', sa.Text(), nullable=True),
        sa.Column('evidence_links', sa.JSON(), nullable=True),
        sa.Column('last_tested_at', sa.DateTime(), nullable=True),
        sa.Column('last_tested_by', sa.String(255), nullable=True),
        sa.Column('next_test_date', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── sox_signoffs ───────────────────────────────────────────────────────
    op.create_table(
        'sox_signoffs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('signoff_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('period', sa.String(50), nullable=False),
        sa.Column('sox_section', sa.String(10), nullable=False),
        sa.Column('signoff_type', sa.String(50), nullable=False),
        sa.Column('signer_name', sa.String(255), nullable=False),
        sa.Column('signer_title', sa.String(255), nullable=True),
        sa.Column('signer_email', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('signed_at', sa.DateTime(), nullable=True),
        sa.Column('total_key_controls', sa.Integer(), nullable=True),
        sa.Column('effective_controls', sa.Integer(), nullable=True),
        sa.Column('deficiencies', sa.Integer(), nullable=True),
        sa.Column('significant_deficiencies', sa.Integer(), nullable=True),
        sa.Column('material_weaknesses', sa.Integer(), nullable=True),
        sa.Column('conclusion', sa.String(50), nullable=True),
        sa.Column('conclusion_notes', sa.Text(), nullable=True),
        sa.Column('exceptions_noted', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── financial_close_tasks ──────────────────────────────────────────────
    op.create_table(
        'financial_close_tasks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('task_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('period', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_type', sa.String(50), nullable=True),
        sa.Column('sequence_order', sa.Integer(), nullable=True),
        sa.Column('assigned_to', sa.String(255), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('completed_by', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='open'),
        sa.Column('is_critical_path', sa.Boolean(), server_default='0'),
        sa.Column('linked_control_id', sa.String(100), nullable=True, index=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── data_processing_activities ─────────────────────────────────────────
    op.create_table(
        'data_processing_activities',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('activity_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('purpose', sa.Text(), nullable=False),
        sa.Column('legal_basis', sa.String(100), nullable=True),
        sa.Column('legitimate_interest_assessment', sa.Text(), nullable=True),
        sa.Column('personal_data_categories', sa.JSON(), nullable=True),
        sa.Column('special_categories', sa.JSON(), nullable=True),
        sa.Column('data_subjects', sa.JSON(), nullable=True),
        sa.Column('controller_name', sa.String(255), nullable=True),
        sa.Column('processor_name', sa.String(255), nullable=True),
        sa.Column('third_party_recipients', sa.JSON(), nullable=True),
        sa.Column('transfers_outside_eea', sa.Boolean(), server_default='0'),
        sa.Column('transfer_safeguards', sa.String(500), nullable=True),
        sa.Column('retention_period', sa.String(255), nullable=True),
        sa.Column('retention_justification', sa.Text(), nullable=True),
        sa.Column('security_measures', sa.Text(), nullable=True),
        sa.Column('dpia_required', sa.Boolean(), server_default='0'),
        sa.Column('dpia_id', sa.String(100), nullable=True),
        sa.Column('business_owner', sa.String(255), nullable=True),
        sa.Column('system_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── dsar_requests ──────────────────────────────────────────────────────
    op.create_table(
        'dsar_requests',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('dsar_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('request_type', sa.String(50), nullable=False),
        sa.Column('subject_name', sa.String(255), nullable=False),
        sa.Column('subject_email', sa.String(255), nullable=False),
        sa.Column('subject_id_verified', sa.Boolean(), server_default='0'),
        sa.Column('verification_method', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('extended_deadline', sa.DateTime(), nullable=True),
        sa.Column('assigned_to', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='received'),
        sa.Column('response_summary', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('completed_by', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── dpia_assessments ───────────────────────────────────────────────────
    op.create_table(
        'dpia_assessments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('dpia_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('processing_activity_id', sa.String(100), nullable=True, index=True),
        sa.Column('project_name', sa.String(255), nullable=True),
        sa.Column('necessity_assessment', sa.Text(), nullable=True),
        sa.Column('proportionality_assessment', sa.Text(), nullable=True),
        sa.Column('risk_assessment', sa.JSON(), nullable=True),
        sa.Column('risk_measures', sa.JSON(), nullable=True),
        sa.Column('dpo_consulted', sa.Boolean(), server_default='0'),
        sa.Column('dpo_opinion', sa.Text(), nullable=True),
        sa.Column('dpo_consulted_at', sa.DateTime(), nullable=True),
        sa.Column('regulator_consulted', sa.Boolean(), server_default='0'),
        sa.Column('regulator_response', sa.Text(), nullable=True),
        sa.Column('overall_risk_level', sa.String(50), nullable=True),
        sa.Column('conclusion', sa.String(50), nullable=True),
        sa.Column('conclusion_notes', sa.Text(), nullable=True),
        sa.Column('conducted_by', sa.String(255), nullable=True),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('review_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── data_breach_incidents ──────────────────────────────────────────────
    op.create_table(
        'data_breach_incidents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('breach_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(50), nullable=False, server_default='medium'),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(), nullable=True),
        sa.Column('contained_at', sa.DateTime(), nullable=True),
        sa.Column('breach_type', sa.String(100), nullable=True),
        sa.Column('data_categories_affected', sa.JSON(), nullable=True),
        sa.Column('subjects_affected_count', sa.Integer(), nullable=True),
        sa.Column('systems_affected', sa.JSON(), nullable=True),
        sa.Column('regulator_notification_required', sa.Boolean(), server_default='0'),
        sa.Column('regulator_notified_at', sa.DateTime(), nullable=True),
        sa.Column('regulator_reference', sa.String(255), nullable=True),
        sa.Column('regulator_deadline', sa.DateTime(), nullable=True),
        sa.Column('subjects_notification_required', sa.Boolean(), server_default='0'),
        sa.Column('subjects_notified_at', sa.DateTime(), nullable=True),
        sa.Column('lead_investigator', sa.String(255), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('remediation_actions', sa.Text(), nullable=True),
        sa.Column('lessons_learned', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='detected'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── regulatory_changes ─────────────────────────────────────────────────
    op.create_table(
        'regulatory_changes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('change_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('regulator', sa.String(255), nullable=True),
        sa.Column('jurisdiction', sa.String(100), nullable=True),
        sa.Column('regulation_name', sa.String(255), nullable=True),
        sa.Column('change_type', sa.String(100), nullable=True),
        sa.Column('effective_date', sa.DateTime(), nullable=True),
        sa.Column('comment_deadline', sa.DateTime(), nullable=True),
        sa.Column('source_url', sa.String(1000), nullable=True),
        sa.Column('impact_level', sa.String(50), nullable=False, server_default='medium'),
        sa.Column('impact_description', sa.Text(), nullable=True),
        sa.Column('affected_obligations', sa.JSON(), nullable=True),
        sa.Column('affected_controls', sa.JSON(), nullable=True),
        sa.Column('affected_policies', sa.JSON(), nullable=True),
        sa.Column('assigned_to', sa.String(255), nullable=True),
        sa.Column('action_plan', sa.Text(), nullable=True),
        sa.Column('action_due_date', sa.DateTime(), nullable=True),
        sa.Column('implementation_notes', sa.Text(), nullable=True),
        sa.Column('implemented_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='new'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── operational_loss_events ────────────────────────────────────────────
    op.create_table(
        'operational_loss_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=True),
        sa.Column('business_line', sa.String(255), nullable=True),
        sa.Column('org_unit', sa.String(255), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('reported_by', sa.String(255), nullable=True),
        sa.Column('gross_loss', sa.Float(), nullable=True),
        sa.Column('recoveries', sa.Float(), nullable=True),
        sa.Column('net_loss', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(10), nullable=True, server_default='USD'),
        sa.Column('is_near_miss', sa.Boolean(), server_default='0'),
        sa.Column('root_cause_category', sa.String(100), nullable=True),
        sa.Column('root_cause_description', sa.Text(), nullable=True),
        sa.Column('contributing_factors', sa.JSON(), nullable=True),
        sa.Column('corrective_actions', sa.Text(), nullable=True),
        sa.Column('preventive_actions', sa.Text(), nullable=True),
        sa.Column('linked_risk_ids', sa.JSON(), nullable=True),
        sa.Column('linked_control_ids', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='reported'),
        sa.Column('reviewed_by', sa.String(255), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── sod_remediations ───────────────────────────────────────────────────
    op.create_table(
        'sod_remediations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('remediation_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('violation_id', sa.String(100), nullable=False, index=True),
        sa.Column('user_id', sa.String(100), nullable=False, index=True),
        sa.Column('rule_id', sa.String(100), nullable=False),
        sa.Column('rule_description', sa.String(500), nullable=True),
        sa.Column('severity', sa.String(50), nullable=True),
        sa.Column('remediation_type', sa.String(50), nullable=True),
        sa.Column('remediation_description', sa.Text(), nullable=True),
        sa.Column('assigned_to', sa.String(255), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('actions_taken', sa.JSON(), nullable=True),
        sa.Column('evidence_links', sa.JSON(), nullable=True),
        sa.Column('validated_by', sa.String(255), nullable=True),
        sa.Column('validated_at', sa.DateTime(), nullable=True),
        sa.Column('validation_notes', sa.Text(), nullable=True),
        sa.Column('exception_requested', sa.Boolean(), server_default='0'),
        sa.Column('exception_rationale', sa.Text(), nullable=True),
        sa.Column('exception_approved_by', sa.String(255), nullable=True),
        sa.Column('exception_expiry', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='open'),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── it_change_risks ────────────────────────────────────────────────────
    op.create_table(
        'it_change_risks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('change_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('change_type', sa.String(100), nullable=True),
        sa.Column('system_name', sa.String(255), nullable=True),
        sa.Column('systems_affected', sa.JSON(), nullable=True),
        sa.Column('requested_by', sa.String(255), nullable=True),
        sa.Column('assigned_to', sa.String(255), nullable=True),
        sa.Column('planned_date', sa.DateTime(), nullable=True),
        sa.Column('actual_date', sa.DateTime(), nullable=True),
        sa.Column('risk_level', sa.String(50), nullable=False, server_default='medium'),
        sa.Column('risk_description', sa.Text(), nullable=True),
        sa.Column('rollback_plan', sa.Text(), nullable=True),
        sa.Column('testing_evidence', sa.Text(), nullable=True),
        sa.Column('approval_status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('post_change_review', sa.Text(), nullable=True),
        sa.Column('post_change_status', sa.String(50), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('linked_sox_control_ids', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── insurance_policies ─────────────────────────────────────────────────
    op.create_table(
        'insurance_policies',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('policy_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('policy_number', sa.String(255), nullable=False),
        sa.Column('insurer_name', sa.String(255), nullable=False),
        sa.Column('policy_type', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('coverage_amount', sa.Float(), nullable=True),
        sa.Column('deductible', sa.Float(), nullable=True),
        sa.Column('annual_premium', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(10), nullable=True, server_default='USD'),
        sa.Column('effective_date', sa.DateTime(), nullable=True),
        sa.Column('expiry_date', sa.DateTime(), nullable=True),
        sa.Column('renewal_reminder_days', sa.Integer(), server_default='60'),
        sa.Column('policy_owner', sa.String(255), nullable=True),
        sa.Column('broker_name', sa.String(255), nullable=True),
        sa.Column('broker_contact', sa.String(255), nullable=True),
        sa.Column('covered_risk_categories', sa.JSON(), nullable=True),
        sa.Column('linked_risk_ids', sa.JSON(), nullable=True),
        sa.Column('exclusions', sa.Text(), nullable=True),
        sa.Column('coverage_conditions', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ── sanctions_screenings ───────────────────────────────────────────────
    op.create_table(
        'sanctions_screenings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('screening_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('entity_name', sa.String(500), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', sa.String(100), nullable=True, index=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('lists_checked', sa.JSON(), nullable=True),
        sa.Column('screened_at', sa.DateTime(), nullable=False),
        sa.Column('screened_by', sa.String(255), nullable=True),
        sa.Column('next_screening_date', sa.DateTime(), nullable=True),
        sa.Column('screening_frequency', sa.String(50), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('match_details', sa.JSON(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolved_by', sa.String(255), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('sanctions_screenings')
    op.drop_table('insurance_policies')
    op.drop_table('it_change_risks')
    op.drop_table('sod_remediations')
    op.drop_table('operational_loss_events')
    op.drop_table('regulatory_changes')
    op.drop_table('data_breach_incidents')
    op.drop_table('dpia_assessments')
    op.drop_table('dsar_requests')
    op.drop_table('data_processing_activities')
    op.drop_table('financial_close_tasks')
    op.drop_table('sox_signoffs')
    op.drop_table('icfr_controls')
