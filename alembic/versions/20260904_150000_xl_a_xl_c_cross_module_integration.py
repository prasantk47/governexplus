"""XL-A and XL-C cross-module integration columns

Revision ID: 20260904_150000
Revises: 20260904_120000
Create Date: 2026-09-04

XL-A — Control-Failure → Residual Risk Feedback (Loop A)
  Adds three columns to enterprise_risks:
    control_coverage          VARCHAR(20) DEFAULT 'effective'
    system_indicated_residual FLOAT       NULLABLE
    coverage_computed_at      DATETIME    NULLABLE

  These fields are written by the recompute-coverage endpoint and allow
  auditors to see the system-inferred coverage signal without ever touching
  the assessor-owned residual_score.

XL-C — Unified Mitigation Register (Loop C)
  Adds one column to mitigation_controls:
    process_control_id        VARCHAR(100) NULLABLE

  Stores the control_id (business key) of the backing ProcessControl in the
  PC module.  Used by the /backing-status and /unlinked-report endpoints to
  surface testing and sign-off gaps.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '20260904_150000'
down_revision = '20260904_120000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # XL-A: enterprise_risks — control coverage feedback columns
    # ------------------------------------------------------------------
    with op.batch_alter_table('enterprise_risks', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'control_coverage',
                sa.String(length=20),
                nullable=True,
                server_default='effective',
            )
        )
        batch_op.add_column(
            sa.Column('system_indicated_residual', sa.Float(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('coverage_computed_at', sa.DateTime(), nullable=True)
        )

    # ------------------------------------------------------------------
    # XL-C: mitigation_controls — process control FK column
    # ------------------------------------------------------------------
    with op.batch_alter_table('mitigation_controls', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('process_control_id', sa.String(length=100), nullable=True)
        )


def downgrade() -> None:
    # XL-C rollback
    with op.batch_alter_table('mitigation_controls', schema=None) as batch_op:
        batch_op.drop_column('process_control_id')

    # XL-A rollback
    with op.batch_alter_table('enterprise_risks', schema=None) as batch_op:
        batch_op.drop_column('coverage_computed_at')
        batch_op.drop_column('system_indicated_residual')
        batch_op.drop_column('control_coverage')
