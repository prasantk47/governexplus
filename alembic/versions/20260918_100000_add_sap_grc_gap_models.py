"""Add SAP GRC feature-gap models (24-gap closure)

Revision ID: 20260918_100000
Revises: 20260904_150000
Create Date: 2026-09-18

Closes 24 SAP GRC feature gaps by:

New tables in Risk Management:
  - business_objectives      : link risks to strategic/operational goals (RM-SAP-GAP-01)
  - risk_scenarios           : multi-driver cascading scenarios (RM-SAP-GAP-02)
  - monte_carlo_simulations  : Monte Carlo simulation run results (RM-SAP-GAP-03)
  - risk_opportunities       : positive risk / opportunity tracking (RM-SAP-GAP-04)

New columns on existing Risk Management tables:
  - enterprise_risks.velocity               : speed of risk materialisation
  - enterprise_risks.business_objective_id  : link to business_objectives
  - risk_incidents.recovery_amount          : total recovered amount
  - risk_incidents.insurance_claim          : gross insurance claim filed
  - risk_incidents.insurance_recovery       : amount received from insurer

New tables in Process Control:
  - control_objectives       : formal control objective entity (PC-SAP-GAP-05)
  - subprocesses             : formal subprocess hierarchy (PC-SAP-GAP-06)
  - policy_documents         : full policy lifecycle (PC-SAP-GAP-07)
  - question_library         : reusable assessment questions (PC-SAP-GAP-08)
  - questionnaires           : assembled questionnaires (PC-SAP-GAP-09)
  - questionnaire_responses  : filled questionnaire responses (PC-SAP-GAP-10)

New tables in Audit Management:
  - audit_dimensions         : multi-perspective audit dimensions (AM-SAP-GAP-11)
  - audit_announcements      : formal auditee notifications (AM-SAP-GAP-12)

New columns on existing Audit Management tables:
  - audit_engagements.opinion            : formal audit opinion
  - audit_engagements.opinion_rationale  : rationale for the opinion
  - audit_plans.is_rolling               : rolling plan flag
  - audit_plans.predecessor_plan_id      : FK to previous rolling plan

New columns on users/roles:
  - roles.prerequisites        : list of prerequisite descriptions (JSON)
  - roles.reaffirmation_days   : days until reaffirmation required
  - roles.methodology_stage    : role engineering methodology stage
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260918_100000'
down_revision: Union[str, None] = '20260904_150000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ==========================================================================
    # RISK MANAGEMENT — New tables
    # ==========================================================================

    # business_objectives
    op.create_table(
        'business_objectives',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True, server_default='tenant_default'),
        sa.Column('objective_id', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('org_unit_id', sa.Integer(), sa.ForeignKey('org_units.id'), nullable=True),
        sa.Column('owner_id', sa.String(100), nullable=True),
        sa.Column('owner_name', sa.String(255), nullable=True),
        sa.Column('target_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('linked_risk_ids', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_business_objectives_tenant_id', 'business_objectives', ['tenant_id'])
    op.create_index('ix_business_objectives_objective_id', 'business_objectives', ['objective_id'])

    # risk_scenarios
    op.create_table(
        'risk_scenarios',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, server_default='tenant_default'),
        sa.Column('scenario_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scenario_type', sa.String(30), nullable=False),
        sa.Column('risk_ids', sa.JSON(), nullable=True),
        sa.Column('trigger_events', sa.JSON(), nullable=True),
        sa.Column('cascading_effects', sa.JSON(), nullable=True),
        sa.Column('probability', sa.Float(), nullable=True),
        sa.Column('impact_low', sa.Float(), nullable=False, server_default='0'),
        sa.Column('impact_mid', sa.Float(), nullable=False, server_default='0'),
        sa.Column('impact_high', sa.Float(), nullable=False, server_default='0'),
        sa.Column('time_horizon', sa.String(50), nullable=True),
        sa.Column('velocity', sa.String(20), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('last_simulated_at', sa.DateTime(), nullable=True),
        sa.Column('simulation_results', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_risk_scenarios_tenant_id', 'risk_scenarios', ['tenant_id'])
    op.create_index('ix_risk_scenarios_scenario_id', 'risk_scenarios', ['scenario_id'])

    # monte_carlo_simulations
    op.create_table(
        'monte_carlo_simulations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, server_default='tenant_default'),
        sa.Column('simulation_id', sa.String(100), nullable=False),
        sa.Column('scenario_id', sa.Integer(), sa.ForeignKey('risk_scenarios.id'), nullable=True),
        sa.Column('risk_id', sa.Integer(), sa.ForeignKey('enterprise_risks.id'), nullable=True),
        sa.Column('distribution_type', sa.String(20), nullable=False),
        sa.Column('iterations', sa.Integer(), nullable=False, server_default='10000'),
        sa.Column('input_parameters', sa.JSON(), nullable=False),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=False),
        sa.Column('executed_by', sa.String(100), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_monte_carlo_simulations_tenant_id', 'monte_carlo_simulations', ['tenant_id'])
    op.create_index('ix_monte_carlo_simulations_simulation_id', 'monte_carlo_simulations', ['simulation_id'])
    op.create_index('ix_monte_carlo_simulations_scenario_id', 'monte_carlo_simulations', ['scenario_id'])
    op.create_index('ix_monte_carlo_simulations_risk_id', 'monte_carlo_simulations', ['risk_id'])

    # risk_opportunities
    op.create_table(
        'risk_opportunities',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, server_default='tenant_default'),
        sa.Column('opportunity_id', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(30), nullable=False),
        sa.Column('org_unit_id', sa.Integer(), sa.ForeignKey('org_units.id'), nullable=True),
        sa.Column('owner_id', sa.String(100), nullable=True),
        sa.Column('owner_name', sa.String(255), nullable=True),
        sa.Column('probability', sa.Float(), nullable=True),
        sa.Column('potential_upside', sa.Float(), nullable=True),
        sa.Column('investment_required', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('time_horizon', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='identified'),
        sa.Column('linked_risk_ids', sa.JSON(), nullable=True),
        sa.Column('actions', sa.JSON(), nullable=True),
        sa.Column('realized_value', sa.Float(), nullable=True),
        sa.Column('realized_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_risk_opportunities_tenant_id', 'risk_opportunities', ['tenant_id'])
    op.create_index('ix_risk_opportunities_opportunity_id', 'risk_opportunities', ['opportunity_id'])

    # ------------------------------------------------------------------
    # RISK MANAGEMENT — ALTER existing tables
    # ------------------------------------------------------------------

    # enterprise_risks: velocity + business_objective_id
    with op.batch_alter_table('enterprise_risks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('velocity', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('business_objective_id', sa.String(100), nullable=True))

    # risk_incidents: loss management / insurance recovery columns
    with op.batch_alter_table('risk_incidents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('recovery_amount', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('insurance_claim', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('insurance_recovery', sa.Float(), nullable=True))

    # ==========================================================================
    # PROCESS CONTROL — New tables
    # ==========================================================================

    # control_objectives
    op.create_table(
        'control_objectives',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, server_default='tenant_default'),
        sa.Column('objective_id', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('process_name', sa.String(255), nullable=True),
        sa.Column('subprocess_name', sa.String(255), nullable=True),
        sa.Column('framework_requirement_id', sa.Integer(), sa.ForeignKey('framework_requirements.id'), nullable=True),
        sa.Column('risk_ids', sa.JSON(), nullable=True),
        sa.Column('control_ids', sa.JSON(), nullable=True),
        sa.Column('owner_id', sa.String(100), nullable=True),
        sa.Column('owner_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_control_objectives_tenant_id', 'control_objectives', ['tenant_id'])
    op.create_index('ix_control_objectives_objective_id', 'control_objectives', ['objective_id'])
    op.create_index('ix_control_objectives_framework_req', 'control_objectives', ['framework_requirement_id'])

    # subprocesses
    op.create_table(
        'subprocesses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, server_default='tenant_default'),
        sa.Column('subprocess_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('process_name', sa.String(255), nullable=False),
        sa.Column('parent_subprocess_id', sa.Integer(), sa.ForeignKey('subprocesses.id'), nullable=True),
        sa.Column('org_unit_id', sa.Integer(), sa.ForeignKey('org_units.id'), nullable=True),
        sa.Column('owner_id', sa.String(100), nullable=True),
        sa.Column('owner_name', sa.String(255), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('risk_ids', sa.JSON(), nullable=True),
        sa.Column('control_ids', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_subprocesses_tenant_id', 'subprocesses', ['tenant_id'])
    op.create_index('ix_subprocesses_subprocess_id', 'subprocesses', ['subprocess_id'])
    op.create_index('ix_subprocesses_parent_subprocess_id', 'subprocesses', ['parent_subprocess_id'])

    # policy_documents
    op.create_table(
        'policy_documents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, server_default='tenant_default'),
        sa.Column('policy_id', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('policy_type', sa.String(30), nullable=False),
        sa.Column('regulation_id', sa.String(100), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('version_history', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('author_id', sa.String(100), nullable=True),
        sa.Column('author_name', sa.String(255), nullable=True),
        sa.Column('approved_by', sa.String(100), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('effective_date', sa.DateTime(), nullable=True),
        sa.Column('expiry_date', sa.DateTime(), nullable=True),
        sa.Column('review_frequency', sa.String(50), nullable=True),
        sa.Column('next_review_date', sa.DateTime(), nullable=True),
        sa.Column('last_reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledgment_required', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('acknowledgment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_recipients', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('attachments', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_policy_documents_tenant_id', 'policy_documents', ['tenant_id'])
    op.create_index('ix_policy_documents_policy_id', 'policy_documents', ['policy_id'])

    # question_library
    op.create_table(
        'question_library',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, server_default='tenant_default'),
        sa.Column('question_id', sa.String(100), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('question_type', sa.String(30), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('scale_min', sa.Integer(), nullable=True),
        sa.Column('scale_max', sa.Integer(), nullable=True),
        sa.Column('required', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('applicable_modules', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_question_library_tenant_id', 'question_library', ['tenant_id'])
    op.create_index('ix_question_library_question_id', 'question_library', ['question_id'])

    # questionnaires
    op.create_table(
        'questionnaires',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, server_default='tenant_default'),
        sa.Column('questionnaire_id', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('questionnaire_type', sa.String(30), nullable=False),
        sa.Column('questions', sa.JSON(), nullable=True),
        sa.Column('target_module', sa.String(10), nullable=True),
        sa.Column('linked_object_type', sa.String(100), nullable=True),
        sa.Column('linked_object_id', sa.String(100), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('is_template', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_questionnaires_tenant_id', 'questionnaires', ['tenant_id'])
    op.create_index('ix_questionnaires_questionnaire_id', 'questionnaires', ['questionnaire_id'])

    # questionnaire_responses
    op.create_table(
        'questionnaire_responses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, server_default='tenant_default'),
        sa.Column('response_id', sa.String(100), nullable=False),
        sa.Column('questionnaire_id', sa.Integer(), sa.ForeignKey('questionnaires.id'), nullable=False),
        sa.Column('respondent_id', sa.String(100), nullable=False),
        sa.Column('respondent_name', sa.String(255), nullable=True),
        sa.Column('respondent_email', sa.String(255), nullable=True),
        sa.Column('responses', sa.JSON(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.String(100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_questionnaire_responses_tenant_id', 'questionnaire_responses', ['tenant_id'])
    op.create_index('ix_questionnaire_responses_response_id', 'questionnaire_responses', ['response_id'])
    op.create_index('ix_questionnaire_responses_questionnaire_id', 'questionnaire_responses', ['questionnaire_id'])

    # ==========================================================================
    # AUDIT MANAGEMENT — New tables
    # ==========================================================================

    # audit_dimensions
    op.create_table(
        'audit_dimensions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, server_default='tenant_default'),
        sa.Column('dimension_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dimension_type', sa.String(30), nullable=False),
        sa.Column('hierarchy', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_audit_dimensions_tenant_id', 'audit_dimensions', ['tenant_id'])
    op.create_index('ix_audit_dimensions_dimension_id', 'audit_dimensions', ['dimension_id'])

    # audit_announcements
    op.create_table(
        'audit_announcements',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, server_default='tenant_default'),
        sa.Column('announcement_id', sa.String(100), nullable=False),
        sa.Column('engagement_id', sa.Integer(), sa.ForeignKey('audit_engagements.id'), nullable=False),
        sa.Column('recipients', sa.JSON(), nullable=True),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('sent_by', sa.String(100), nullable=True),
        sa.Column('acknowledgments', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_audit_announcements_tenant_id', 'audit_announcements', ['tenant_id'])
    op.create_index('ix_audit_announcements_announcement_id', 'audit_announcements', ['announcement_id'])
    op.create_index('ix_audit_announcements_engagement_id', 'audit_announcements', ['engagement_id'])

    # ------------------------------------------------------------------
    # AUDIT MANAGEMENT — ALTER existing tables
    # ------------------------------------------------------------------

    # audit_engagements: opinion + opinion_rationale
    with op.batch_alter_table('audit_engagements', schema=None) as batch_op:
        batch_op.add_column(sa.Column('opinion', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('opinion_rationale', sa.Text(), nullable=True))

    # audit_plans: is_rolling + predecessor_plan_id
    with op.batch_alter_table('audit_plans', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('is_rolling', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column('predecessor_plan_id', sa.Integer(), nullable=True)
        )

    # ==========================================================================
    # ROLES — ALTER existing table
    # ==========================================================================

    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prerequisites', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('reaffirmation_days', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('methodology_stage', sa.String(50), nullable=True))


def downgrade() -> None:

    # Roles
    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.drop_column('methodology_stage')
        batch_op.drop_column('reaffirmation_days')
        batch_op.drop_column('prerequisites')

    # Audit Management — altered columns
    with op.batch_alter_table('audit_plans', schema=None) as batch_op:
        batch_op.drop_column('predecessor_plan_id')
        batch_op.drop_column('is_rolling')

    with op.batch_alter_table('audit_engagements', schema=None) as batch_op:
        batch_op.drop_column('opinion_rationale')
        batch_op.drop_column('opinion')

    # Audit Management — new tables
    op.drop_index('ix_audit_announcements_engagement_id', table_name='audit_announcements')
    op.drop_index('ix_audit_announcements_announcement_id', table_name='audit_announcements')
    op.drop_index('ix_audit_announcements_tenant_id', table_name='audit_announcements')
    op.drop_table('audit_announcements')

    op.drop_index('ix_audit_dimensions_dimension_id', table_name='audit_dimensions')
    op.drop_index('ix_audit_dimensions_tenant_id', table_name='audit_dimensions')
    op.drop_table('audit_dimensions')

    # Process Control — new tables (responses before questionnaires due to FK)
    op.drop_index('ix_questionnaire_responses_questionnaire_id', table_name='questionnaire_responses')
    op.drop_index('ix_questionnaire_responses_response_id', table_name='questionnaire_responses')
    op.drop_index('ix_questionnaire_responses_tenant_id', table_name='questionnaire_responses')
    op.drop_table('questionnaire_responses')

    op.drop_index('ix_questionnaires_questionnaire_id', table_name='questionnaires')
    op.drop_index('ix_questionnaires_tenant_id', table_name='questionnaires')
    op.drop_table('questionnaires')

    op.drop_index('ix_question_library_question_id', table_name='question_library')
    op.drop_index('ix_question_library_tenant_id', table_name='question_library')
    op.drop_table('question_library')

    op.drop_index('ix_policy_documents_policy_id', table_name='policy_documents')
    op.drop_index('ix_policy_documents_tenant_id', table_name='policy_documents')
    op.drop_table('policy_documents')

    op.drop_index('ix_subprocesses_parent_subprocess_id', table_name='subprocesses')
    op.drop_index('ix_subprocesses_subprocess_id', table_name='subprocesses')
    op.drop_index('ix_subprocesses_tenant_id', table_name='subprocesses')
    op.drop_table('subprocesses')

    op.drop_index('ix_control_objectives_framework_req', table_name='control_objectives')
    op.drop_index('ix_control_objectives_objective_id', table_name='control_objectives')
    op.drop_index('ix_control_objectives_tenant_id', table_name='control_objectives')
    op.drop_table('control_objectives')

    # Risk Management — altered columns
    with op.batch_alter_table('risk_incidents', schema=None) as batch_op:
        batch_op.drop_column('insurance_recovery')
        batch_op.drop_column('insurance_claim')
        batch_op.drop_column('recovery_amount')

    with op.batch_alter_table('enterprise_risks', schema=None) as batch_op:
        batch_op.drop_column('business_objective_id')
        batch_op.drop_column('velocity')

    # Risk Management — new tables (simulations before scenarios due to FK)
    op.drop_index('ix_monte_carlo_simulations_risk_id', table_name='monte_carlo_simulations')
    op.drop_index('ix_monte_carlo_simulations_scenario_id', table_name='monte_carlo_simulations')
    op.drop_index('ix_monte_carlo_simulations_simulation_id', table_name='monte_carlo_simulations')
    op.drop_index('ix_monte_carlo_simulations_tenant_id', table_name='monte_carlo_simulations')
    op.drop_table('monte_carlo_simulations')

    op.drop_index('ix_risk_opportunities_opportunity_id', table_name='risk_opportunities')
    op.drop_index('ix_risk_opportunities_tenant_id', table_name='risk_opportunities')
    op.drop_table('risk_opportunities')

    op.drop_index('ix_risk_scenarios_scenario_id', table_name='risk_scenarios')
    op.drop_index('ix_risk_scenarios_tenant_id', table_name='risk_scenarios')
    op.drop_table('risk_scenarios')

    op.drop_index('ix_business_objectives_objective_id', table_name='business_objectives')
    op.drop_index('ix_business_objectives_tenant_id', table_name='business_objectives')
    op.drop_table('business_objectives')
