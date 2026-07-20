"""add organizations

Revision ID: c1d2e3f4a5b6
Revises: a1b2c3d4e5f6
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── New tables ────────────────────────────────────────────────────────────
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    op.create_table(
        'org_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("role IN ('owner','admin','member','viewer')", name='org_members_role_check'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_id', 'user_id'),
    )

    op.create_table(
        'org_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('token', sa.String(64), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role IN ('admin','member','viewer')", name='org_invitations_role_check'),
        sa.CheckConstraint("status IN ('pending','accepted','expired','revoked')", name='org_invitations_status_check'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )

    # ── Add org_id FK to 5 resource tables ───────────────────────────────────
    for table in ('connections', 'skills', 'agents', 'pods', 'projects'):
        op.add_column(table, sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            f'fk_{table}_org_id',
            table, 'organizations',
            ['org_id'], ['id'],
            ondelete='CASCADE',
        )

    # ── Composite indexes ─────────────────────────────────────────────────────
    op.create_index('ix_connections_user_org', 'connections', ['user_id', 'org_id'])
    op.create_index('ix_skills_user_org',      'skills',      ['user_id', 'org_id'])
    op.create_index('ix_agents_user_org',       'agents',      ['user_id', 'org_id'])
    op.create_index('ix_pods_user_org',         'pods',        ['user_id', 'org_id'])
    op.create_index('ix_projects_user_org',     'projects',    ['user_id', 'org_id'])


def downgrade() -> None:
    op.drop_index('ix_projects_user_org',  table_name='projects')
    op.drop_index('ix_pods_user_org',       table_name='pods')
    op.drop_index('ix_agents_user_org',     table_name='agents')
    op.drop_index('ix_skills_user_org',     table_name='skills')
    op.drop_index('ix_connections_user_org',table_name='connections')

    for table in ('connections', 'skills', 'agents', 'pods', 'projects'):
        op.drop_constraint(f'fk_{table}_org_id', table, type_='foreignkey')
        op.drop_column(table, 'org_id')

    op.drop_table('org_invitations')
    op.drop_table('org_members')
    op.drop_table('organizations')
