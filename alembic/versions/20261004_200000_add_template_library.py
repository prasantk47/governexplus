"""Add Template Library tables (packs, items, tenant activations)

Revision ID: 20261004_200000
Revises: 20261004_100000
Create Date: 2026-10-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20261004_200000'
down_revision = '20261004_100000'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'template_packs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('pack_code', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('module', sa.String(50)),
        sa.Column('tags', sa.JSON),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('author', sa.String(100)),
        sa.Column('license_note', sa.String(500)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('pack_code', name='uq_template_packs_code'),
    )

    op.create_table(
        'template_pack_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('pack_id', sa.String(36), sa.ForeignKey('template_packs.id'), nullable=False),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('changelog', sa.Text),
        sa.Column('published_at', sa.DateTime),
        sa.Column('checksum', sa.String(64)),
        sa.Column('item_count', sa.Integer, server_default='0'),
        sa.Column('is_latest', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('pack_id', 'version', name='uq_pack_version'),
    )

    op.create_table(
        'template_items',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('item_code', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('module', sa.String(50), nullable=False),
        sa.Column('item_type', sa.String(50), nullable=False),
        sa.Column('compliance_frameworks', sa.JSON),
        sa.Column('industry_tags', sa.JSON),
        sa.Column('payload', sa.JSON, nullable=False),
        sa.Column('version', sa.String(20), nullable=False, server_default='1.0.0'),
        sa.Column('checksum', sa.String(64)),
        sa.Column('status', sa.String(20), nullable=False, server_default='published'),
        sa.Column('pack_id', sa.String(36), sa.ForeignKey('template_packs.id'), nullable=True),
        sa.Column('pack_version', sa.String(20)),
        sa.Column('severity', sa.String(20)),
        sa.Column('activation_count', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('item_code', name='uq_template_items_code'),
    )
    op.create_index('ix_template_items_module', 'template_items', ['module'])
    op.create_index('ix_template_items_item_type', 'template_items', ['item_type'])
    op.create_index('ix_template_items_status', 'template_items', ['status'])

    op.create_table(
        'tenant_item_activations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('template_item_id', sa.String(36), sa.ForeignKey('template_items.id'), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('activated_at', sa.DateTime),
        sa.Column('activated_by', sa.String(100)),
        sa.Column('copy_payload', sa.JSON, nullable=True),
        sa.Column('customized_at', sa.DateTime, nullable=True),
        sa.Column('customized_by', sa.String(100), nullable=True),
        sa.Column('mappings', sa.JSON, nullable=True),
        sa.Column('pending_update_version', sa.String(20), nullable=True),
        sa.Column('update_reviewed_at', sa.DateTime, nullable=True),
        sa.Column('update_review_decision', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'template_item_id', name='uq_tenant_activation'),
    )
    op.create_index('ix_tenant_item_activations_tenant', 'tenant_item_activations', ['tenant_id'])
    op.create_index('ix_tenant_item_activations_active', 'tenant_item_activations', ['tenant_id', 'is_active'])


def downgrade():
    op.drop_index('ix_tenant_item_activations_active', table_name='tenant_item_activations')
    op.drop_index('ix_tenant_item_activations_tenant', table_name='tenant_item_activations')
    op.drop_table('tenant_item_activations')
    op.drop_index('ix_template_items_status', table_name='template_items')
    op.drop_index('ix_template_items_item_type', table_name='template_items')
    op.drop_index('ix_template_items_module', table_name='template_items')
    op.drop_table('template_items')
    op.drop_table('template_pack_versions')
    op.drop_table('template_packs')
