"""Add template-library traceability columns to functional content tables.

Every functional-content table that can be created from a library template
gets three new nullable columns:

  source_template_item_id  VARCHAR(36)  – FK → template_items.id
  template_version         VARCHAR(20)  – version of the item when activated
  is_customized            BOOLEAN      – true once the tenant has edited the copy

Target tables (per the implementation guide §"Building it in the current stack"):
  risk_rules, mitigation_controls, process_controls, control_tests,
  certification_campaigns, key_risk_indicators, standalone_surveys,
  jml_policies, fraud_rules

Revision ID: 20261005_100000
Revises: 20261004_200000
Create Date: 2026-10-05
"""

from alembic import op
import sqlalchemy as sa

revision = '20261005_100000'
down_revision = '20261004_200000'
branch_labels = None
depends_on = None

# (table_name, fk_required)
# fk_required=False for tables where we skip the FK constraint to avoid
# cross-DB-engine issues (SQLite does not enforce FK constraints anyway)
_TARGETS = [
    "risk_rules",
    "mitigation_controls",
    "process_controls",
    "control_tests",
    "certification_campaigns",
    "key_risk_indicators",
    "standalone_surveys",
    "jml_policies",
    "fraud_rules",
]


def upgrade():
    for table in _TARGETS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "source_template_item_id",
                    sa.String(36),
                    nullable=True,
                    comment="FK to template_items.id — set when row was created from a library template",
                )
            )
            batch_op.add_column(
                sa.Column(
                    "template_version",
                    sa.String(20),
                    nullable=True,
                    comment="Version of the template item at activation time",
                )
            )
            batch_op.add_column(
                sa.Column(
                    "is_customized",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                    comment="True once the tenant has edited this copy away from the shipped template",
                )
            )
        # Add an index on source_template_item_id for the CoW resolution query
        op.create_index(
            f"ix_{table}_source_template_item_id",
            table,
            ["source_template_item_id"],
            unique=False,
            postgresql_where=sa.text("source_template_item_id IS NOT NULL"),
        )


def downgrade():
    for table in _TARGETS:
        op.drop_index(
            f"ix_{table}_source_template_item_id",
            table_name=table,
        )
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column("is_customized")
            batch_op.drop_column("template_version")
            batch_op.drop_column("source_template_item_id")
