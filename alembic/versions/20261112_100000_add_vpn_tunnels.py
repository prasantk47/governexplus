"""Add VPN tunnel configs table

Revision ID: 20261112_100000
Revises: 20261108_100000
"""
revision = '20261112_100000'
down_revision = '20261108_100000'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'vpn_tunnel_configs',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False, server_default='cisco_anyconnect'),
        sa.Column('gateway', sa.String(255), nullable=False),
        sa.Column('group', sa.String(200), server_default=''),
        sa.Column('username', sa.String(200), server_default=''),
        sa.Column('password_encrypted', sa.Text, server_default=''),
        sa.Column('certificate_path', sa.String(500), server_default=''),
        sa.Column('auth_type', sa.String(50), server_default='password'),
        sa.Column('split_tunnel', sa.Boolean, server_default='1'),
        sa.Column('routes', sa.JSON, nullable=True),
        sa.Column('dns_servers', sa.JSON, nullable=True),
        sa.Column('mtu', sa.Integer, server_default='1406'),
        sa.Column('idle_timeout', sa.Integer, server_default='3600'),
        sa.Column('reconnect_attempts', sa.Integer, server_default='3'),
        sa.Column('reconnect_delay', sa.Integer, server_default='10'),
        sa.Column('pre_connect_script', sa.Text, server_default=''),
        sa.Column('post_connect_script', sa.Text, server_default=''),
        sa.Column('linked_connector_ids', sa.JSON, nullable=True),
        sa.Column('enabled', sa.Boolean, server_default='1'),
        sa.Column('status', sa.String(50), server_default='disconnected'),
        sa.Column('last_connected_at', sa.String(50), server_default=''),
        sa.Column('last_error', sa.Text, server_default=''),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('vpn_tunnel_configs')
