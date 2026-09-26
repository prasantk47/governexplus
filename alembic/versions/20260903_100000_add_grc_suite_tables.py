"""Add GRC Suite tables (Risk Management, Process Control, Audit Management)

Revision ID: 20260903_100000
Revises: 20260826_100000
Create Date: 2026-09-03

Creates all tables for the three new GRC modules plus the shared foundation:

GRC Foundation:
  - org_units
  - framework_definitions
  - framework_requirements

Risk Management (RM-01 through RM-22):
  - enterprise_risks
  - risk_assessments
  - risk_appetites
  - key_risk_indicators
  - kri_measurements
  - risk_responses
  - risk_incidents

Process Control (PC-01 through PC-22):
  - process_controls
  - control_tests
  - control_deficiencies
  - control_self_assessments
  - ccm_rules
  - ccm_executions
  - grc_evidence
  - signoff_certifications

Audit Management (AM-01 through AM-32):
  - auditable_entities
  - audit_plans
  - audit_engagements
  - audit_work_programs
  - audit_procedures
  - audit_workpapers
  - audit_findings
  - audit_actions
  - auditor_time_entries
  - auditor_resources
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260903_100000'
down_revision: Union[str, None] = '20260826_100000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ==========================================================================
    # GRC FOUNDATION — must come first because downstream tables FK into these
    # ==========================================================================

    # --------------------------------------------------------------------------
    # org_units
    # Self-referential hierarchy; parent_id FK added after table creation to
    # avoid forward-reference issues with batch_alter (SQLite-safe).
    # --------------------------------------------------------------------------
    op.create_table(
        'org_units',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('unit_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('unit_type', sa.String(length=50), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('path', sa.String(length=1000), nullable=True),
        sa.Column('manager_user_id', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('org_units', schema=None) as batch_op:
        batch_op.create_index('ix_org_units_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_org_units_unit_id', ['unit_id'], unique=False)
        batch_op.create_index('ix_org_units_parent_id', ['parent_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_org_units_parent_id', 'org_units', ['parent_id'], ['id']
        )

    # --------------------------------------------------------------------------
    # framework_definitions
    # --------------------------------------------------------------------------
    op.create_table(
        'framework_definitions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('framework_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('framework_type', sa.String(length=50), nullable=False),
        sa.Column('structure', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('framework_definitions', schema=None) as batch_op:
        batch_op.create_index('ix_framework_definitions_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_framework_definitions_framework_id', ['framework_id'], unique=False)

    # --------------------------------------------------------------------------
    # framework_requirements
    # Self-referential hierarchy (parent_requirement_id).
    # --------------------------------------------------------------------------
    op.create_table(
        'framework_requirements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('framework_id', sa.Integer(), nullable=False),
        sa.Column('requirement_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_requirement_id', sa.Integer(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['framework_id'], ['framework_definitions.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('framework_requirements', schema=None) as batch_op:
        batch_op.create_index('ix_framework_requirements_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_framework_requirements_framework_id', ['framework_id'], unique=False)
        batch_op.create_index('ix_framework_requirements_requirement_id', ['requirement_id'], unique=False)
        batch_op.create_index('ix_framework_requirements_parent_requirement_id', ['parent_requirement_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_framework_requirements_parent',
            'framework_requirements', ['parent_requirement_id'], ['id']
        )

    # ==========================================================================
    # RISK MANAGEMENT MODULE
    # ==========================================================================

    # --------------------------------------------------------------------------
    # enterprise_risks  (RM-01)
    # --------------------------------------------------------------------------
    op.create_table(
        'enterprise_risks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('risk_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('description_ar', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('org_unit_id', sa.Integer(), nullable=True),
        sa.Column('risk_owner_id', sa.String(length=100), nullable=True),
        sa.Column('risk_owner_name', sa.String(length=255), nullable=True),
        sa.Column('inherent_likelihood', sa.Integer(), nullable=True),
        sa.Column('inherent_impact', sa.Integer(), nullable=True),
        sa.Column('inherent_score', sa.Float(), nullable=True),
        sa.Column('residual_likelihood', sa.Integer(), nullable=True),
        sa.Column('residual_impact', sa.Integer(), nullable=True),
        sa.Column('residual_score', sa.Float(), nullable=True),
        sa.Column('risk_appetite', sa.Float(), nullable=True),
        sa.Column('risk_tolerance', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='identified'),
        sa.Column('last_assessed_at', sa.DateTime(), nullable=True),
        sa.Column('next_review_date', sa.DateTime(), nullable=True),
        sa.Column('review_frequency', sa.String(length=50), nullable=True),
        sa.Column('related_control_ids', sa.JSON(), nullable=True),
        sa.Column('related_finding_ids', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['org_unit_id'], ['org_units.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('enterprise_risks', schema=None) as batch_op:
        batch_op.create_index('ix_enterprise_risks_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_enterprise_risks_risk_id', ['risk_id'], unique=False)
        batch_op.create_index('ix_enterprise_risks_org_unit_id', ['org_unit_id'], unique=False)

    # --------------------------------------------------------------------------
    # risk_assessments  (RM-10, RM-11)
    # --------------------------------------------------------------------------
    op.create_table(
        'risk_assessments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('assessment_id', sa.String(length=100), nullable=False),
        sa.Column('risk_id', sa.Integer(), nullable=False),
        sa.Column('assessor_id', sa.String(length=100), nullable=True),
        sa.Column('assessor_name', sa.String(length=255), nullable=True),
        sa.Column('likelihood_score', sa.Integer(), nullable=False),
        sa.Column('impact_score', sa.Integer(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('assessment_type', sa.String(length=50), nullable=False, server_default='periodic'),
        sa.Column('likelihood_rationale', sa.Text(), nullable=True),
        sa.Column('impact_rationale', sa.Text(), nullable=True),
        sa.Column('monetary_impact', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['risk_id'], ['enterprise_risks.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('risk_assessments', schema=None) as batch_op:
        batch_op.create_index('ix_risk_assessments_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_risk_assessments_assessment_id', ['assessment_id'], unique=False)
        batch_op.create_index('ix_risk_assessments_risk_id', ['risk_id'], unique=False)

    # --------------------------------------------------------------------------
    # risk_appetites  (RM-03)
    # --------------------------------------------------------------------------
    op.create_table(
        'risk_appetites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('org_unit_id', sa.Integer(), nullable=True),
        sa.Column('appetite_score', sa.Float(), nullable=False),
        sa.Column('tolerance_score', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('approved_by', sa.String(length=100), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('effective_from', sa.DateTime(), nullable=True),
        sa.Column('effective_to', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['org_unit_id'], ['org_units.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('risk_appetites', schema=None) as batch_op:
        batch_op.create_index('ix_risk_appetites_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_risk_appetites_org_unit_id', ['org_unit_id'], unique=False)

    # --------------------------------------------------------------------------
    # key_risk_indicators  (RM-13)
    # --------------------------------------------------------------------------
    op.create_table(
        'key_risk_indicators',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('kri_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('risk_id', sa.Integer(), nullable=True),
        sa.Column('data_source', sa.String(length=100), nullable=True),
        sa.Column('unit_of_measure', sa.String(length=100), nullable=True),
        sa.Column('frequency', sa.String(length=50), nullable=True),
        sa.Column('threshold_green', sa.Float(), nullable=True),
        sa.Column('threshold_amber', sa.Float(), nullable=True),
        sa.Column('threshold_red', sa.Float(), nullable=True),
        sa.Column('current_value', sa.Float(), nullable=True),
        sa.Column('last_measured_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='normal'),
        sa.Column('owner_id', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['risk_id'], ['enterprise_risks.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('key_risk_indicators', schema=None) as batch_op:
        batch_op.create_index('ix_key_risk_indicators_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_key_risk_indicators_kri_id', ['kri_id'], unique=False)
        batch_op.create_index('ix_key_risk_indicators_risk_id', ['risk_id'], unique=False)

    # --------------------------------------------------------------------------
    # kri_measurements
    # --------------------------------------------------------------------------
    op.create_table(
        'kri_measurements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('kri_id', sa.Integer(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('measured_at', sa.DateTime(), nullable=False),
        sa.Column('measured_by', sa.String(length=100), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['kri_id'], ['key_risk_indicators.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('kri_measurements', schema=None) as batch_op:
        batch_op.create_index('ix_kri_measurements_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_kri_measurements_kri_id', ['kri_id'], unique=False)

    # --------------------------------------------------------------------------
    # risk_responses  (RM-20)
    # --------------------------------------------------------------------------
    op.create_table(
        'risk_responses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('response_id', sa.String(length=100), nullable=False),
        sa.Column('risk_id', sa.Integer(), nullable=False),
        sa.Column('response_type', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.String(length=100), nullable=True),
        sa.Column('owner_name', sa.String(length=255), nullable=True),
        sa.Column('actions', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='planned'),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('effectiveness_rating', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['risk_id'], ['enterprise_risks.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('risk_responses', schema=None) as batch_op:
        batch_op.create_index('ix_risk_responses_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_risk_responses_response_id', ['response_id'], unique=False)
        batch_op.create_index('ix_risk_responses_risk_id', ['risk_id'], unique=False)

    # --------------------------------------------------------------------------
    # risk_incidents  (RM-22)
    # --------------------------------------------------------------------------
    op.create_table(
        'risk_incidents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('incident_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('risk_id', sa.Integer(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('financial_impact', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('corrective_actions', sa.JSON(), nullable=True),
        sa.Column('reported_by', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='reported'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['risk_id'], ['enterprise_risks.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('risk_incidents', schema=None) as batch_op:
        batch_op.create_index('ix_risk_incidents_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_risk_incidents_incident_id', ['incident_id'], unique=False)
        batch_op.create_index('ix_risk_incidents_risk_id', ['risk_id'], unique=False)

    # ==========================================================================
    # PROCESS CONTROL MODULE
    # ==========================================================================

    # --------------------------------------------------------------------------
    # process_controls  (PC-01)
    # --------------------------------------------------------------------------
    op.create_table(
        'process_controls',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('control_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('objective', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('control_type', sa.String(length=30), nullable=False),
        sa.Column('control_nature', sa.String(length=30), nullable=False),
        sa.Column('frequency', sa.String(length=30), nullable=False),
        sa.Column('org_unit_id', sa.Integer(), nullable=True),
        sa.Column('process_name', sa.String(length=255), nullable=True),
        sa.Column('subprocess_name', sa.String(length=255), nullable=True),
        sa.Column('owner_id', sa.String(length=100), nullable=True),
        sa.Column('owner_name', sa.String(length=255), nullable=True),
        sa.Column('owner_email', sa.String(length=255), nullable=True),
        sa.Column('framework_mappings', sa.JSON(), nullable=True),
        sa.Column('risk_ids', sa.JSON(), nullable=True),
        sa.Column('regulation_ids', sa.JSON(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('effective_date', sa.DateTime(), nullable=True),
        sa.Column('review_date', sa.DateTime(), nullable=True),
        sa.Column('next_review_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('key_control', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('change_history', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['org_unit_id'], ['org_units.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('process_controls', schema=None) as batch_op:
        batch_op.create_index('ix_process_controls_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_process_controls_control_id', ['control_id'], unique=False)
        batch_op.create_index('ix_process_controls_org_unit_id', ['org_unit_id'], unique=False)

    # --------------------------------------------------------------------------
    # control_tests  (PC-11)
    # --------------------------------------------------------------------------
    op.create_table(
        'control_tests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('test_id', sa.String(length=100), nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('test_type', sa.String(length=40), nullable=False),
        sa.Column('testing_period_start', sa.DateTime(), nullable=True),
        sa.Column('testing_period_end', sa.DateTime(), nullable=True),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.Column('population_size', sa.Integer(), nullable=True),
        sa.Column('tester_id', sa.String(length=100), nullable=True),
        sa.Column('tester_name', sa.String(length=255), nullable=True),
        sa.Column('test_steps', sa.JSON(), nullable=True),
        sa.Column('result', sa.String(length=30), nullable=True),
        sa.Column('exceptions_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('exception_details', sa.JSON(), nullable=True),
        sa.Column('conclusion', sa.Text(), nullable=True),
        sa.Column('evidence_ids', sa.JSON(), nullable=True),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='planned'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['control_id'], ['process_controls.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('control_tests', schema=None) as batch_op:
        batch_op.create_index('ix_control_tests_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_control_tests_test_id', ['test_id'], unique=False)
        batch_op.create_index('ix_control_tests_control_id', ['control_id'], unique=False)

    # --------------------------------------------------------------------------
    # control_deficiencies  (PC-13)
    # --------------------------------------------------------------------------
    op.create_table(
        'control_deficiencies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('deficiency_id', sa.String(length=100), nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('test_id', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='test'),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=40), nullable=False),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('remediation_plan', sa.Text(), nullable=True),
        sa.Column('remediation_owner_id', sa.String(length=100), nullable=True),
        sa.Column('remediation_owner_name', sa.String(length=255), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='open'),
        sa.Column('verified_by', sa.String(length=100), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('related_risk_ids', sa.JSON(), nullable=True),
        sa.Column('related_finding_ids', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['control_id'], ['process_controls.id'], ),
        sa.ForeignKeyConstraint(['test_id'], ['control_tests.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('control_deficiencies', schema=None) as batch_op:
        batch_op.create_index('ix_control_deficiencies_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_control_deficiencies_deficiency_id', ['deficiency_id'], unique=False)
        batch_op.create_index('ix_control_deficiencies_control_id', ['control_id'], unique=False)
        batch_op.create_index('ix_control_deficiencies_test_id', ['test_id'], unique=False)

    # --------------------------------------------------------------------------
    # control_self_assessments  (PC-12)
    # --------------------------------------------------------------------------
    op.create_table(
        'control_self_assessments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('assessment_id', sa.String(length=100), nullable=False),
        sa.Column('campaign_name', sa.String(length=255), nullable=False),
        sa.Column('campaign_type', sa.String(length=50), nullable=True),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('assessor_id', sa.String(length=100), nullable=True),
        sa.Column('assessor_name', sa.String(length=255), nullable=True),
        sa.Column('design_adequate', sa.Boolean(), nullable=True),
        sa.Column('operating_effectively', sa.Boolean(), nullable=True),
        sa.Column('questionnaire_responses', sa.JSON(), nullable=True),
        sa.Column('attestation', sa.Text(), nullable=True),
        sa.Column('attested_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('reviewer_id', sa.String(length=100), nullable=True),
        sa.Column('reviewer_comments', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['control_id'], ['process_controls.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('control_self_assessments', schema=None) as batch_op:
        batch_op.create_index('ix_control_self_assessments_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_control_self_assessments_assessment_id', ['assessment_id'], unique=False)
        batch_op.create_index('ix_control_self_assessments_control_id', ['control_id'], unique=False)

    # --------------------------------------------------------------------------
    # ccm_rules  (PC-20, PC-22)
    # --------------------------------------------------------------------------
    op.create_table(
        'ccm_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('rule_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('control_id', sa.Integer(), nullable=True),
        sa.Column('source_system', sa.String(length=100), nullable=True),
        sa.Column('rule_type', sa.String(length=30), nullable=False),
        sa.Column('rule_definition', sa.JSON(), nullable=False),
        sa.Column('threshold_operator', sa.String(length=20), nullable=True),
        sa.Column('threshold_value', sa.String(length=255), nullable=True),
        sa.Column('frequency', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_result', sa.String(length=50), nullable=True),
        sa.Column('auto_create_deficiency', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('severity_on_breach', sa.String(length=50), nullable=False, server_default='observation'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['control_id'], ['process_controls.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('ccm_rules', schema=None) as batch_op:
        batch_op.create_index('ix_ccm_rules_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_ccm_rules_rule_id', ['rule_id'], unique=False)
        batch_op.create_index('ix_ccm_rules_control_id', ['control_id'], unique=False)

    # --------------------------------------------------------------------------
    # ccm_executions  (PC-22)
    # --------------------------------------------------------------------------
    op.create_table(
        'ccm_executions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=False),
        sa.Column('execution_duration_ms', sa.Integer(), nullable=True),
        sa.Column('result', sa.String(length=20), nullable=False),
        sa.Column('findings_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('findings_detail', sa.JSON(), nullable=True),
        sa.Column('deficiency_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['rule_id'], ['ccm_rules.id'], ),
        sa.ForeignKeyConstraint(['deficiency_id'], ['control_deficiencies.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('ccm_executions', schema=None) as batch_op:
        batch_op.create_index('ix_ccm_executions_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_ccm_executions_rule_id', ['rule_id'], unique=False)
        batch_op.create_index('ix_ccm_executions_deficiency_id', ['deficiency_id'], unique=False)

    # --------------------------------------------------------------------------
    # grc_evidence  (PC-15)
    # Self-referential previous_version_id FK added via batch_alter.
    # --------------------------------------------------------------------------
    op.create_table(
        'grc_evidence',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('evidence_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('evidence_type', sa.String(length=100), nullable=True),
        sa.Column('file_name', sa.String(length=500), nullable=True),
        sa.Column('file_path', sa.String(length=2000), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('source_module', sa.String(length=20), nullable=True),
        sa.Column('linked_object_type', sa.String(length=100), nullable=True),
        sa.Column('linked_object_id', sa.String(length=100), nullable=True),
        sa.Column('uploaded_by', sa.String(length=100), nullable=True),
        sa.Column('upload_date', sa.DateTime(), nullable=True),
        sa.Column('retention_until', sa.DateTime(), nullable=True),
        sa.Column('legal_hold', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('previous_version_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('grc_evidence', schema=None) as batch_op:
        batch_op.create_index('ix_grc_evidence_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_grc_evidence_evidence_id', ['evidence_id'], unique=False)
        batch_op.create_index('ix_grc_evidence_linked_object_id', ['linked_object_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_grc_evidence_previous_version',
            'grc_evidence', ['previous_version_id'], ['id']
        )

    # --------------------------------------------------------------------------
    # signoff_certifications  (PC-14)
    # Self-referential parent_certification_id FK added via batch_alter.
    # --------------------------------------------------------------------------
    op.create_table(
        'signoff_certifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('certification_id', sa.String(length=100), nullable=False),
        sa.Column('period', sa.String(length=50), nullable=False),
        sa.Column('org_unit_id', sa.Integer(), nullable=True),
        sa.Column('certifier_id', sa.String(length=100), nullable=False),
        sa.Column('certifier_name', sa.String(length=255), nullable=True),
        sa.Column('certifier_role', sa.String(length=100), nullable=True),
        sa.Column('parent_certification_id', sa.Integer(), nullable=True),
        sa.Column('scope_summary', sa.Text(), nullable=True),
        sa.Column('controls_in_scope', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('controls_effective', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('deficiencies_open', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('statement', sa.Text(), nullable=True),
        sa.Column('certified_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='pending'),
        sa.Column('exceptions', sa.JSON(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['org_unit_id'], ['org_units.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('signoff_certifications', schema=None) as batch_op:
        batch_op.create_index('ix_signoff_certifications_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_signoff_certifications_certification_id', ['certification_id'], unique=False)
        batch_op.create_index('ix_signoff_certifications_org_unit_id', ['org_unit_id'], unique=False)
        batch_op.create_index('ix_signoff_certifications_parent_certification_id', ['parent_certification_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_signoff_certifications_parent',
            'signoff_certifications', ['parent_certification_id'], ['id']
        )

    # ==========================================================================
    # AUDIT MANAGEMENT MODULE
    # ==========================================================================

    # --------------------------------------------------------------------------
    # auditable_entities  (AM-01)
    # --------------------------------------------------------------------------
    op.create_table(
        'auditable_entities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('entity_type', sa.String(length=30), nullable=False),
        sa.Column('org_unit_id', sa.Integer(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('last_audited_at', sa.DateTime(), nullable=True),
        sa.Column('audit_frequency', sa.String(length=50), nullable=True),
        sa.Column('primary_auditor_id', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['org_unit_id'], ['org_units.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('auditable_entities', schema=None) as batch_op:
        batch_op.create_index('ix_auditable_entities_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_auditable_entities_entity_id', ['entity_id'], unique=False)
        batch_op.create_index('ix_auditable_entities_org_unit_id', ['org_unit_id'], unique=False)

    # --------------------------------------------------------------------------
    # audit_plans  (AM-02)
    # --------------------------------------------------------------------------
    op.create_table(
        'audit_plans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('plan_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('plan_type', sa.String(length=20), nullable=False),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=True),
        sa.Column('period_end', sa.DateTime(), nullable=True),
        sa.Column('total_audit_hours', sa.Integer(), nullable=True),
        sa.Column('allocated_budget', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('prepared_by', sa.String(length=100), nullable=True),
        sa.Column('approved_by', sa.String(length=100), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('risk_methodology', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('audit_plans', schema=None) as batch_op:
        batch_op.create_index('ix_audit_plans_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_audit_plans_plan_id', ['plan_id'], unique=False)

    # --------------------------------------------------------------------------
    # audit_engagements  (AM-10)
    # --------------------------------------------------------------------------
    op.create_table(
        'audit_engagements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('engagement_id', sa.String(length=100), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('objective', sa.Text(), nullable=True),
        sa.Column('scope', sa.Text(), nullable=True),
        sa.Column('engagement_type', sa.String(length=30), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='planned'),
        sa.Column('lead_auditor_id', sa.String(length=100), nullable=True),
        sa.Column('lead_auditor_name', sa.String(length=255), nullable=True),
        sa.Column('team_members', sa.JSON(), nullable=True),
        sa.Column('planned_start', sa.DateTime(), nullable=True),
        sa.Column('planned_end', sa.DateTime(), nullable=True),
        sa.Column('actual_start', sa.DateTime(), nullable=True),
        sa.Column('actual_end', sa.DateTime(), nullable=True),
        sa.Column('budget_hours', sa.Float(), nullable=True),
        sa.Column('actual_hours', sa.Float(), nullable=True),
        sa.Column('risk_rating', sa.String(length=20), nullable=True),
        sa.Column('methodology', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['audit_plans.id'], ),
        sa.ForeignKeyConstraint(['entity_id'], ['auditable_entities.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('audit_engagements', schema=None) as batch_op:
        batch_op.create_index('ix_audit_engagements_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_audit_engagements_engagement_id', ['engagement_id'], unique=False)
        batch_op.create_index('ix_audit_engagements_plan_id', ['plan_id'], unique=False)
        batch_op.create_index('ix_audit_engagements_entity_id', ['entity_id'], unique=False)

    # --------------------------------------------------------------------------
    # audit_work_programs  (AM-11)
    # --------------------------------------------------------------------------
    op.create_table(
        'audit_work_programs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('program_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('audit_type', sa.String(length=50), nullable=True),
        sa.Column('procedures', sa.JSON(), nullable=True),
        sa.Column('is_template', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('source_engagement_id', sa.Integer(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['source_engagement_id'], ['audit_engagements.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('audit_work_programs', schema=None) as batch_op:
        batch_op.create_index('ix_audit_work_programs_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_audit_work_programs_program_id', ['program_id'], unique=False)
        batch_op.create_index('ix_audit_work_programs_source_engagement_id', ['source_engagement_id'], unique=False)

    # --------------------------------------------------------------------------
    # audit_procedures  (AM-11)
    # --------------------------------------------------------------------------
    op.create_table(
        'audit_procedures',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('procedure_id', sa.String(length=100), nullable=False),
        sa.Column('engagement_id', sa.Integer(), nullable=False),
        sa.Column('work_program_id', sa.Integer(), nullable=True),
        sa.Column('ref_number', sa.String(length=50), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('assigned_to_id', sa.String(length=100), nullable=True),
        sa.Column('assigned_to_name', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='not_started'),
        sa.Column('conclusion', sa.Text(), nullable=True),
        sa.Column('hours_spent', sa.Float(), nullable=False, server_default='0'),
        sa.Column('preparer_id', sa.String(length=100), nullable=True),
        sa.Column('prepared_at', sa.DateTime(), nullable=True),
        sa.Column('reviewer_id', sa.String(length=100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('evidence_ids', sa.JSON(), nullable=True),
        sa.Column('cross_references', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['engagement_id'], ['audit_engagements.id'], ),
        sa.ForeignKeyConstraint(['work_program_id'], ['audit_work_programs.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('audit_procedures', schema=None) as batch_op:
        batch_op.create_index('ix_audit_procedures_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_audit_procedures_procedure_id', ['procedure_id'], unique=False)
        batch_op.create_index('ix_audit_procedures_engagement_id', ['engagement_id'], unique=False)
        batch_op.create_index('ix_audit_procedures_work_program_id', ['work_program_id'], unique=False)

    # --------------------------------------------------------------------------
    # audit_workpapers  (AM-12)
    # Self-referential previous_version_id FK added via batch_alter.
    # --------------------------------------------------------------------------
    op.create_table(
        'audit_workpapers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('workpaper_id', sa.String(length=100), nullable=False),
        sa.Column('engagement_id', sa.Integer(), nullable=False),
        sa.Column('procedure_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('document_type', sa.String(length=100), nullable=True),
        sa.Column('file_name', sa.String(length=500), nullable=True),
        sa.Column('file_path', sa.String(length=2000), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('previous_version_id', sa.Integer(), nullable=True),
        sa.Column('preparer_id', sa.String(length=100), nullable=True),
        sa.Column('prepared_at', sa.DateTime(), nullable=True),
        sa.Column('reviewer_id', sa.String(length=100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_status', sa.String(length=30), nullable=False, server_default='pending_review'),
        sa.Column('review_notes', sa.JSON(), nullable=True),
        sa.Column('cross_references', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['engagement_id'], ['audit_engagements.id'], ),
        sa.ForeignKeyConstraint(['procedure_id'], ['audit_procedures.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('audit_workpapers', schema=None) as batch_op:
        batch_op.create_index('ix_audit_workpapers_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_audit_workpapers_workpaper_id', ['workpaper_id'], unique=False)
        batch_op.create_index('ix_audit_workpapers_engagement_id', ['engagement_id'], unique=False)
        batch_op.create_index('ix_audit_workpapers_procedure_id', ['procedure_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_audit_workpapers_previous_version',
            'audit_workpapers', ['previous_version_id'], ['id']
        )

    # --------------------------------------------------------------------------
    # audit_findings  (AM-20)
    # prior_finding_id FK added via batch_alter.
    # --------------------------------------------------------------------------
    op.create_table(
        'audit_findings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('finding_id', sa.String(length=100), nullable=False),
        sa.Column('engagement_id', sa.Integer(), nullable=False),
        sa.Column('procedure_id', sa.Integer(), nullable=True),
        sa.Column('ref_number', sa.String(length=50), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('condition', sa.Text(), nullable=True),
        sa.Column('criteria', sa.Text(), nullable=True),
        sa.Column('cause', sa.Text(), nullable=True),
        sa.Column('effect', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('risk_id', sa.Integer(), nullable=True),
        sa.Column('control_id', sa.Integer(), nullable=True),
        sa.Column('violation_id', sa.Integer(), nullable=True),
        sa.Column('management_response', sa.Text(), nullable=True),
        sa.Column('management_action_owner', sa.String(length=100), nullable=True),
        sa.Column('management_target_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='draft'),
        sa.Column('repeat_finding', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('prior_finding_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['engagement_id'], ['audit_engagements.id'], ),
        sa.ForeignKeyConstraint(['procedure_id'], ['audit_procedures.id'], ),
        sa.ForeignKeyConstraint(['risk_id'], ['enterprise_risks.id'], ),
        sa.ForeignKeyConstraint(['control_id'], ['process_controls.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('audit_findings', schema=None) as batch_op:
        batch_op.create_index('ix_audit_findings_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_audit_findings_finding_id', ['finding_id'], unique=False)
        batch_op.create_index('ix_audit_findings_engagement_id', ['engagement_id'], unique=False)
        batch_op.create_index('ix_audit_findings_procedure_id', ['procedure_id'], unique=False)
        batch_op.create_index('ix_audit_findings_risk_id', ['risk_id'], unique=False)
        batch_op.create_index('ix_audit_findings_control_id', ['control_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_audit_findings_prior_finding',
            'audit_findings', ['prior_finding_id'], ['id']
        )

    # --------------------------------------------------------------------------
    # audit_actions  (AM-21)
    # Maps to AuditManagementAction model (renamed to avoid collision).
    # --------------------------------------------------------------------------
    op.create_table(
        'audit_actions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('action_id', sa.String(length=100), nullable=False),
        sa.Column('finding_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('owner_id', sa.String(length=100), nullable=True),
        sa.Column('owner_name', sa.String(length=255), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('extended_due_date', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('evidence_of_closure', sa.Text(), nullable=True),
        sa.Column('evidence_ids', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='open'),
        sa.Column('verified_by', sa.String(length=100), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('escalation_level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_escalated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['finding_id'], ['audit_findings.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('audit_actions', schema=None) as batch_op:
        batch_op.create_index('ix_audit_actions_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_audit_actions_action_id', ['action_id'], unique=False)
        batch_op.create_index('ix_audit_actions_finding_id', ['finding_id'], unique=False)

    # --------------------------------------------------------------------------
    # auditor_time_entries  (AM-14)
    # --------------------------------------------------------------------------
    op.create_table(
        'auditor_time_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('engagement_id', sa.Integer(), nullable=False),
        sa.Column('procedure_id', sa.Integer(), nullable=True),
        sa.Column('auditor_id', sa.String(length=100), nullable=False),
        sa.Column('auditor_name', sa.String(length=255), nullable=True),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('hours', sa.Float(), nullable=False),
        sa.Column('activity_type', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['engagement_id'], ['audit_engagements.id'], ),
        sa.ForeignKeyConstraint(['procedure_id'], ['audit_procedures.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('auditor_time_entries', schema=None) as batch_op:
        batch_op.create_index('ix_auditor_time_entries_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_auditor_time_entries_engagement_id', ['engagement_id'], unique=False)
        batch_op.create_index('ix_auditor_time_entries_procedure_id', ['procedure_id'], unique=False)
        batch_op.create_index('ix_auditor_time_entries_auditor_id', ['auditor_id'], unique=False)

    # --------------------------------------------------------------------------
    # auditor_resources  (AM-03)
    # --------------------------------------------------------------------------
    op.create_table(
        'auditor_resources',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('auditor_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('skills', sa.JSON(), nullable=True),
        sa.Column('certifications', sa.JSON(), nullable=True),
        sa.Column('available_hours_per_month', sa.Float(), nullable=False, server_default='160'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_external', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('auditor_resources', schema=None) as batch_op:
        batch_op.create_index('ix_auditor_resources_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_auditor_resources_auditor_id', ['auditor_id'], unique=False)


def downgrade() -> None:
    # Drop in strict reverse dependency order

    # Audit Management
    with op.batch_alter_table('auditor_resources', schema=None) as batch_op:
        batch_op.drop_index('ix_auditor_resources_auditor_id')
        batch_op.drop_index('ix_auditor_resources_tenant_id')
    op.drop_table('auditor_resources')

    with op.batch_alter_table('auditor_time_entries', schema=None) as batch_op:
        batch_op.drop_index('ix_auditor_time_entries_auditor_id')
        batch_op.drop_index('ix_auditor_time_entries_procedure_id')
        batch_op.drop_index('ix_auditor_time_entries_engagement_id')
        batch_op.drop_index('ix_auditor_time_entries_tenant_id')
    op.drop_table('auditor_time_entries')

    with op.batch_alter_table('audit_actions', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_actions_finding_id')
        batch_op.drop_index('ix_audit_actions_action_id')
        batch_op.drop_index('ix_audit_actions_tenant_id')
    op.drop_table('audit_actions')

    with op.batch_alter_table('audit_findings', schema=None) as batch_op:
        batch_op.drop_constraint('fk_audit_findings_prior_finding', type_='foreignkey')
        batch_op.drop_index('ix_audit_findings_control_id')
        batch_op.drop_index('ix_audit_findings_risk_id')
        batch_op.drop_index('ix_audit_findings_procedure_id')
        batch_op.drop_index('ix_audit_findings_engagement_id')
        batch_op.drop_index('ix_audit_findings_finding_id')
        batch_op.drop_index('ix_audit_findings_tenant_id')
    op.drop_table('audit_findings')

    with op.batch_alter_table('audit_workpapers', schema=None) as batch_op:
        batch_op.drop_constraint('fk_audit_workpapers_previous_version', type_='foreignkey')
        batch_op.drop_index('ix_audit_workpapers_procedure_id')
        batch_op.drop_index('ix_audit_workpapers_engagement_id')
        batch_op.drop_index('ix_audit_workpapers_workpaper_id')
        batch_op.drop_index('ix_audit_workpapers_tenant_id')
    op.drop_table('audit_workpapers')

    with op.batch_alter_table('audit_procedures', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_procedures_work_program_id')
        batch_op.drop_index('ix_audit_procedures_engagement_id')
        batch_op.drop_index('ix_audit_procedures_procedure_id')
        batch_op.drop_index('ix_audit_procedures_tenant_id')
    op.drop_table('audit_procedures')

    with op.batch_alter_table('audit_work_programs', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_work_programs_source_engagement_id')
        batch_op.drop_index('ix_audit_work_programs_program_id')
        batch_op.drop_index('ix_audit_work_programs_tenant_id')
    op.drop_table('audit_work_programs')

    with op.batch_alter_table('audit_engagements', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_engagements_entity_id')
        batch_op.drop_index('ix_audit_engagements_plan_id')
        batch_op.drop_index('ix_audit_engagements_engagement_id')
        batch_op.drop_index('ix_audit_engagements_tenant_id')
    op.drop_table('audit_engagements')

    with op.batch_alter_table('audit_plans', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_plans_plan_id')
        batch_op.drop_index('ix_audit_plans_tenant_id')
    op.drop_table('audit_plans')

    with op.batch_alter_table('auditable_entities', schema=None) as batch_op:
        batch_op.drop_index('ix_auditable_entities_org_unit_id')
        batch_op.drop_index('ix_auditable_entities_entity_id')
        batch_op.drop_index('ix_auditable_entities_tenant_id')
    op.drop_table('auditable_entities')

    # Process Control
    with op.batch_alter_table('signoff_certifications', schema=None) as batch_op:
        batch_op.drop_constraint('fk_signoff_certifications_parent', type_='foreignkey')
        batch_op.drop_index('ix_signoff_certifications_parent_certification_id')
        batch_op.drop_index('ix_signoff_certifications_org_unit_id')
        batch_op.drop_index('ix_signoff_certifications_certification_id')
        batch_op.drop_index('ix_signoff_certifications_tenant_id')
    op.drop_table('signoff_certifications')

    with op.batch_alter_table('grc_evidence', schema=None) as batch_op:
        batch_op.drop_constraint('fk_grc_evidence_previous_version', type_='foreignkey')
        batch_op.drop_index('ix_grc_evidence_linked_object_id')
        batch_op.drop_index('ix_grc_evidence_evidence_id')
        batch_op.drop_index('ix_grc_evidence_tenant_id')
    op.drop_table('grc_evidence')

    with op.batch_alter_table('ccm_executions', schema=None) as batch_op:
        batch_op.drop_index('ix_ccm_executions_deficiency_id')
        batch_op.drop_index('ix_ccm_executions_rule_id')
        batch_op.drop_index('ix_ccm_executions_tenant_id')
    op.drop_table('ccm_executions')

    with op.batch_alter_table('ccm_rules', schema=None) as batch_op:
        batch_op.drop_index('ix_ccm_rules_control_id')
        batch_op.drop_index('ix_ccm_rules_rule_id')
        batch_op.drop_index('ix_ccm_rules_tenant_id')
    op.drop_table('ccm_rules')

    with op.batch_alter_table('control_self_assessments', schema=None) as batch_op:
        batch_op.drop_index('ix_control_self_assessments_control_id')
        batch_op.drop_index('ix_control_self_assessments_assessment_id')
        batch_op.drop_index('ix_control_self_assessments_tenant_id')
    op.drop_table('control_self_assessments')

    with op.batch_alter_table('control_deficiencies', schema=None) as batch_op:
        batch_op.drop_index('ix_control_deficiencies_test_id')
        batch_op.drop_index('ix_control_deficiencies_control_id')
        batch_op.drop_index('ix_control_deficiencies_deficiency_id')
        batch_op.drop_index('ix_control_deficiencies_tenant_id')
    op.drop_table('control_deficiencies')

    with op.batch_alter_table('control_tests', schema=None) as batch_op:
        batch_op.drop_index('ix_control_tests_control_id')
        batch_op.drop_index('ix_control_tests_test_id')
        batch_op.drop_index('ix_control_tests_tenant_id')
    op.drop_table('control_tests')

    with op.batch_alter_table('process_controls', schema=None) as batch_op:
        batch_op.drop_index('ix_process_controls_org_unit_id')
        batch_op.drop_index('ix_process_controls_control_id')
        batch_op.drop_index('ix_process_controls_tenant_id')
    op.drop_table('process_controls')

    # Risk Management
    with op.batch_alter_table('risk_incidents', schema=None) as batch_op:
        batch_op.drop_index('ix_risk_incidents_risk_id')
        batch_op.drop_index('ix_risk_incidents_incident_id')
        batch_op.drop_index('ix_risk_incidents_tenant_id')
    op.drop_table('risk_incidents')

    with op.batch_alter_table('risk_responses', schema=None) as batch_op:
        batch_op.drop_index('ix_risk_responses_risk_id')
        batch_op.drop_index('ix_risk_responses_response_id')
        batch_op.drop_index('ix_risk_responses_tenant_id')
    op.drop_table('risk_responses')

    with op.batch_alter_table('kri_measurements', schema=None) as batch_op:
        batch_op.drop_index('ix_kri_measurements_kri_id')
        batch_op.drop_index('ix_kri_measurements_tenant_id')
    op.drop_table('kri_measurements')

    with op.batch_alter_table('key_risk_indicators', schema=None) as batch_op:
        batch_op.drop_index('ix_key_risk_indicators_risk_id')
        batch_op.drop_index('ix_key_risk_indicators_kri_id')
        batch_op.drop_index('ix_key_risk_indicators_tenant_id')
    op.drop_table('key_risk_indicators')

    with op.batch_alter_table('risk_appetites', schema=None) as batch_op:
        batch_op.drop_index('ix_risk_appetites_org_unit_id')
        batch_op.drop_index('ix_risk_appetites_tenant_id')
    op.drop_table('risk_appetites')

    with op.batch_alter_table('risk_assessments', schema=None) as batch_op:
        batch_op.drop_index('ix_risk_assessments_risk_id')
        batch_op.drop_index('ix_risk_assessments_assessment_id')
        batch_op.drop_index('ix_risk_assessments_tenant_id')
    op.drop_table('risk_assessments')

    with op.batch_alter_table('enterprise_risks', schema=None) as batch_op:
        batch_op.drop_index('ix_enterprise_risks_org_unit_id')
        batch_op.drop_index('ix_enterprise_risks_risk_id')
        batch_op.drop_index('ix_enterprise_risks_tenant_id')
    op.drop_table('enterprise_risks')

    # GRC Foundation
    with op.batch_alter_table('framework_requirements', schema=None) as batch_op:
        batch_op.drop_constraint('fk_framework_requirements_parent', type_='foreignkey')
        batch_op.drop_index('ix_framework_requirements_parent_requirement_id')
        batch_op.drop_index('ix_framework_requirements_requirement_id')
        batch_op.drop_index('ix_framework_requirements_framework_id')
        batch_op.drop_index('ix_framework_requirements_tenant_id')
    op.drop_table('framework_requirements')

    with op.batch_alter_table('framework_definitions', schema=None) as batch_op:
        batch_op.drop_index('ix_framework_definitions_framework_id')
        batch_op.drop_index('ix_framework_definitions_tenant_id')
    op.drop_table('framework_definitions')

    with op.batch_alter_table('org_units', schema=None) as batch_op:
        batch_op.drop_constraint('fk_org_units_parent_id', type_='foreignkey')
        batch_op.drop_index('ix_org_units_parent_id')
        batch_op.drop_index('ix_org_units_unit_id')
        batch_op.drop_index('ix_org_units_tenant_id')
    op.drop_table('org_units')
