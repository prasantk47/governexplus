"""Add orchestration_contexts and shopping_carts tables

Revision ID: 20260826_100000
Revises: abd0e2efd983
Create Date: 2026-08-26

Adds tables that were previously only created via create_all() at runtime:
- orchestration_contexts: persisted workflow orchestration contexts
  (OrchestrationContextRecord in db/models/operations.py)
- shopping_carts: ARM shopping cart persistence
  (ShoppingCartModel in db/models/operations.py)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260826_100000'
down_revision: Union[str, None] = 'abd0e2efd983'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ======================================================================
    # ORCHESTRATION CONTEXTS
    # Stores serialised OrchestrationContext instances so they survive
    # process restarts.  Lookup is by (tenant_id, context_id).
    # ======================================================================
    op.create_table(
        'orchestration_contexts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('context_id', sa.String(length=100), nullable=False),
        sa.Column('process_type', sa.String(length=50), nullable=False),
        sa.Column('workflow_status', sa.String(length=30), nullable=True),
        sa.Column('context_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('orchestration_contexts', schema=None) as batch_op:
        batch_op.create_index('ix_orchestration_contexts_tenant_id', ['tenant_id'], unique=False)
        batch_op.create_index('ix_orchestration_contexts_context_id', ['context_id'], unique=False)

    # ======================================================================
    # SHOPPING CARTS
    # ARM shopping cart persistence — survives process restarts.
    # Items are stored as a JSON text blob (CartItem.to_dict() list).
    # Lifecycle statuses: open | submitted | cancelled
    # ======================================================================
    op.create_table(
        'shopping_carts',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('requester_id', sa.String(length=100), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('items_json', sa.Text(), nullable=False),
        sa.Column('cart_created_at', sa.String(length=50), nullable=True),
        sa.Column('cart_updated_at', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('shopping_carts', schema=None) as batch_op:
        batch_op.create_index('ix_shopping_carts_requester_id', ['requester_id'], unique=False)
        batch_op.create_index('ix_shopping_carts_tenant_id', ['tenant_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('shopping_carts', schema=None) as batch_op:
        batch_op.drop_index('ix_shopping_carts_tenant_id')
        batch_op.drop_index('ix_shopping_carts_requester_id')

    op.drop_table('shopping_carts')

    with op.batch_alter_table('orchestration_contexts', schema=None) as batch_op:
        batch_op.drop_index('ix_orchestration_contexts_context_id')
        batch_op.drop_index('ix_orchestration_contexts_tenant_id')

    op.drop_table('orchestration_contexts')
