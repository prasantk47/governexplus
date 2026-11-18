"""Add License Intelligence module — 16 tables

Revision ID: 20261118_100000
Revises: 20261112_100000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "20261118_100000"
down_revision = "20261112_100000"
branch_labels = None
depends_on = None


def upgrade():
    # LI-008: Rule Packs
    op.create_table(
        "li_rule_packs",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("target_platform", sa.String(50), server_default="S4HANA"),
        sa.Column("is_base_pack", sa.Boolean, server_default="false"),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("created_by", sa.String(100)),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approved_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "li_rule_pack_versions",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("rule_pack_id", sa.String(50), sa.ForeignKey("li_rule_packs.id"), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date),
        sa.Column("conversion_ratios", JSON, nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("drafted_by", sa.String(100)),
        sa.Column("reviewed_by", sa.String(100)),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approved_at", sa.DateTime),
        sa.Column("mapping_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("rule_pack_id", "version", name="uq_li_rpv_pack_version"),
    )

    op.create_table(
        "li_auth_mappings",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("rule_pack_version_id", sa.String(50), sa.ForeignKey("li_rule_pack_versions.id"), nullable=False),
        sa.Column("auth_object", sa.String(50), nullable=False),
        sa.Column("auth_field", sa.String(50)),
        sa.Column("auth_value", sa.String(200)),
        sa.Column("auth_value_pattern", sa.String(200)),
        sa.Column("mapped_use_type", sa.String(30), nullable=False),
        sa.Column("source_reference", sa.String(500)),
        sa.Column("description", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("priority", sa.Integer, server_default="100"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_li_am_auth", "li_auth_mappings", ["auth_object", "auth_field"])

    op.create_table(
        "li_tenant_overrides",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("base_mapping_id", sa.String(50), sa.ForeignKey("li_auth_mappings.id")),
        sa.Column("auth_object", sa.String(50), nullable=False),
        sa.Column("auth_field", sa.String(50)),
        sa.Column("auth_value", sa.String(200)),
        sa.Column("override_use_type", sa.String(30), nullable=False),
        sa.Column("justification", sa.Text, nullable=False),
        sa.Column("contract_reference", sa.String(200)),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approved_at", sa.DateTime),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # LI-005: Contracts
    op.create_table(
        "li_contracts",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("contract_reference", sa.String(200), nullable=False),
        sa.Column("contract_type", sa.String(50), server_default="S4HANA_FUE"),
        sa.Column("status", sa.String(30), server_default="active"),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date),
        sa.Column("renewal_date", sa.Date),
        sa.Column("contracted_fue", sa.Float, nullable=False),
        sa.Column("price_per_fue", sa.Float),
        sa.Column("currency", sa.String(10), server_default="USD"),
        sa.Column("conversion_ratios", JSON),
        sa.Column("counting_rule", sa.String(50), server_default="highest_across_systems"),
        sa.Column("developer_terms", sa.Text),
        sa.Column("use_type_definitions", JSON),
        sa.Column("system_ids", JSON),
        sa.Column("rule_pack_version_id", sa.String(50), sa.ForeignKey("li_rule_pack_versions.id")),
        sa.Column("alert_threshold_pct", sa.Float, server_default="85.0"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "li_contract_amendments",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("contract_id", sa.String(50), sa.ForeignKey("li_contracts.id"), nullable=False),
        sa.Column("amendment_date", sa.Date, nullable=False),
        sa.Column("amendment_type", sa.String(50)),
        sa.Column("previous_values", JSON),
        sa.Column("new_values", JSON),
        sa.Column("reason", sa.Text),
        sa.Column("amended_by", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "li_entitlement_snapshots",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("contract_id", sa.String(50), sa.ForeignKey("li_contracts.id"), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("contracted_fue", sa.Float, nullable=False),
        sa.Column("conversion_ratios", JSON, nullable=False),
        sa.Column("counting_rule", sa.String(50)),
        sa.Column("system_ids", JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # LI-001: Classifications
    op.create_table(
        "li_classifications",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("system_id", sa.String(50)),
        sa.Column("use_type", sa.String(30), nullable=False),
        sa.Column("fue_value", sa.Float, nullable=False),
        sa.Column("rule_pack_version_id", sa.String(50), sa.ForeignKey("li_rule_pack_versions.id")),
        sa.Column("calculation_date", sa.DateTime, nullable=False),
        sa.Column("is_current", sa.Boolean, server_default="true"),
        sa.Column("previous_use_type", sa.String(30)),
        sa.Column("previous_fue_value", sa.Float),
        sa.Column("change_reason", sa.String(200)),
        sa.Column("is_flagged", sa.Boolean, server_default="false"),
        sa.Column("flag_reason", sa.String(500)),
        sa.Column("department", sa.String(100)),
        sa.Column("business_unit", sa.String(100)),
        sa.Column("cost_center", sa.String(50)),
        sa.Column("last_activity_date", sa.DateTime),
        sa.Column("inactive_days", sa.Integer),
        sa.Column("is_review_candidate", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_li_cls_tenant_user", "li_classifications", ["tenant_id", "username"])
    op.create_index("ix_li_cls_tenant_current", "li_classifications", ["tenant_id", "is_current"])
    op.create_index("ix_li_cls_use_type", "li_classifications", ["tenant_id", "use_type"])

    op.create_table(
        "li_classification_drivers",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("classification_id", sa.String(50), sa.ForeignKey("li_classifications.id"), nullable=False),
        sa.Column("role_name", sa.String(100), nullable=False),
        sa.Column("auth_object", sa.String(50), nullable=False),
        sa.Column("auth_field", sa.String(50)),
        sa.Column("auth_value", sa.String(200)),
        sa.Column("mapped_use_type", sa.String(30), nullable=False),
        sa.Column("mapping_id", sa.String(50)),
        sa.Column("was_used_in_period", sa.Boolean),
        sa.Column("last_used_date", sa.DateTime),
        sa.Column("use_type_without_this", sa.String(30)),
        sa.Column("fue_difference", sa.Float),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # LI-002: Consumption Snapshots
    op.create_table(
        "li_consumption_snapshots",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("contract_id", sa.String(50), sa.ForeignKey("li_contracts.id"), nullable=False),
        sa.Column("snapshot_date", sa.DateTime, nullable=False),
        sa.Column("rule_pack_version_id", sa.String(50)),
        sa.Column("total_users", sa.Integer, server_default="0"),
        sa.Column("advanced_count", sa.Integer, server_default="0"),
        sa.Column("core_count", sa.Integer, server_default="0"),
        sa.Column("self_service_count", sa.Integer, server_default="0"),
        sa.Column("developer_count", sa.Integer, server_default="0"),
        sa.Column("unclassified_count", sa.Integer, server_default="0"),
        sa.Column("consumed_fue", sa.Float, server_default="0"),
        sa.Column("contracted_fue", sa.Float, server_default="0"),
        sa.Column("available_fue", sa.Float, server_default="0"),
        sa.Column("utilisation_pct", sa.Float, server_default="0"),
        sa.Column("over_consumed", sa.Boolean, server_default="false"),
        sa.Column("by_system", JSON),
        sa.Column("by_business_unit", JSON),
        sa.Column("by_department", JSON),
        sa.Column("by_cost_center", JSON),
        sa.Column("calculation_inputs", JSON),
        sa.Column("is_latest", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # LI-003: Usage Data
    op.create_table(
        "li_usage_daily",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("system_id", sa.String(50), nullable=False),
        sa.Column("usage_date", sa.Date, nullable=False),
        sa.Column("transaction_code", sa.String(50)),
        sa.Column("app_component", sa.String(100)),
        sa.Column("execution_count", sa.Integer, server_default="0"),
        sa.Column("is_advanced_mapped", sa.Boolean, server_default="false"),
        sa.Column("source", sa.String(50)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "username", "system_id", "usage_date",
                            "transaction_code", name="uq_li_usage_daily"),
    )

    op.create_table(
        "li_usage_raw",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("system_id", sa.String(50), nullable=False),
        sa.Column("event_timestamp", sa.DateTime, nullable=False),
        sa.Column("event_type", sa.String(50)),
        sa.Column("transaction_code", sa.String(50)),
        sa.Column("program_name", sa.String(200)),
        sa.Column("terminal", sa.String(100)),
        sa.Column("source", sa.String(50)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # LI-007: Reclamation
    op.create_table(
        "li_reclamation_cases",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("user_id", sa.String(100)),
        sa.Column("system_id", sa.String(50)),
        sa.Column("trigger", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), server_default="candidate"),
        sa.Column("current_use_type", sa.String(30)),
        sa.Column("current_fue", sa.Float),
        sa.Column("projected_use_type", sa.String(30)),
        sa.Column("projected_fue", sa.Float),
        sa.Column("fue_released", sa.Float, server_default="0"),
        sa.Column("roles_to_remove", JSON),
        sa.Column("inactive_days", sa.Integer),
        sa.Column("last_activity_date", sa.DateTime),
        sa.Column("exception_reason", sa.Text),
        sa.Column("is_exception", sa.Boolean, server_default="false"),
        sa.Column("reviewer", sa.String(100)),
        sa.Column("reviewed_at", sa.DateTime),
        sa.Column("approval_workflow_id", sa.String(100)),
        sa.Column("access_lifecycle_request_id", sa.String(100)),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("evidence", JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_li_rc_tenant_status", "li_reclamation_cases", ["tenant_id", "status"])

    op.create_table(
        "li_reclamation_actions",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("case_id", sa.String(50), sa.ForeignKey("li_reclamation_cases.id"), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("target_role", sa.String(100)),
        sa.Column("target_system", sa.String(50)),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("executed_at", sa.DateTime),
        sa.Column("executed_by", sa.String(100)),
        sa.Column("result", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # LI-006: Position Snapshots
    op.create_table(
        "li_position_snapshots",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("contract_id", sa.String(50), sa.ForeignKey("li_contracts.id")),
        sa.Column("contracted_fue", sa.Float, nullable=False),
        sa.Column("consumed_fue", sa.Float, nullable=False),
        sa.Column("available_fue", sa.Float, nullable=False),
        sa.Column("utilisation_pct", sa.Float, nullable=False),
        sa.Column("advanced_count", sa.Integer, server_default="0"),
        sa.Column("core_count", sa.Integer, server_default="0"),
        sa.Column("self_service_count", sa.Integer, server_default="0"),
        sa.Column("developer_count", sa.Integer, server_default="0"),
        sa.Column("unclassified_count", sa.Integer, server_default="0"),
        sa.Column("total_users", sa.Integer, server_default="0"),
        sa.Column("reclamation_fue_released", sa.Float, server_default="0"),
        sa.Column("review_candidates", sa.Integer, server_default="0"),
        sa.Column("open_reclamation_cases", sa.Integer, server_default="0"),
        sa.Column("data_freshness", JSON),
        sa.Column("rule_pack_version", sa.String(50)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_li_ps_tenant_date", "li_position_snapshots", ["tenant_id", "snapshot_date"])

    # Collection Status
    op.create_table(
        "li_collection_status",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("system_id", sa.String(50), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("last_collected_at", sa.DateTime),
        sa.Column("last_success_at", sa.DateTime),
        sa.Column("records_collected", sa.Integer, server_default="0"),
        sa.Column("coverage_start", sa.Date),
        sa.Column("coverage_end", sa.Date),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "system_id", "source_type", name="uq_li_cs_sys_source"),
    )


def downgrade():
    op.drop_table("li_collection_status")
    op.drop_table("li_position_snapshots")
    op.drop_table("li_reclamation_actions")
    op.drop_table("li_reclamation_cases")
    op.drop_table("li_usage_raw")
    op.drop_table("li_usage_daily")
    op.drop_table("li_consumption_snapshots")
    op.drop_table("li_classification_drivers")
    op.drop_table("li_classifications")
    op.drop_table("li_entitlement_snapshots")
    op.drop_table("li_contract_amendments")
    op.drop_table("li_contracts")
    op.drop_table("li_tenant_overrides")
    op.drop_table("li_auth_mappings")
    op.drop_table("li_rule_pack_versions")
    op.drop_table("li_rule_packs")
