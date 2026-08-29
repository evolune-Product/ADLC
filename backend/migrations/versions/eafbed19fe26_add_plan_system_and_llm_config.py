"""add_plan_system_and_llm_config

Revision ID: eafbed19fe26
Revises: c1d2e3f4a5b6
Create Date: 2026-08-11 12:43:42.967545

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eafbed19fe26'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ── Create plan_type ENUMs ────────────────────────────────────────────────
    user_plan_type = sa.Enum('free', 'teams', 'enterprise', name='user_plan_type')
    org_plan_type = sa.Enum('teams', 'enterprise', 'legacy', name='org_plan_type')
    user_plan_type.create(op.get_bind())
    org_plan_type.create(op.get_bind())

    # ── Add columns to users table ────────────────────────────────────────────
    op.add_column('users', sa.Column('plan_type', user_plan_type, nullable=False, server_default='free'))
    op.add_column('users', sa.Column('is_org_member', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('locked_to_org_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('users', sa.Column('llm_provider', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('llm_api_key_encrypted', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('llm_model', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('llm_config', sa.dialects.postgresql.JSONB(), nullable=False, server_default='{}'))

    # Add FK constraint for locked_to_org_id
    op.create_foreign_key(
        'fk_users_locked_to_org_id',
        'users', 'organizations',
        ['locked_to_org_id'], ['id'],
        ondelete='CASCADE'
    )

    # ── Add columns to organizations table ────────────────────────────────────
    op.add_column('organizations', sa.Column('plan_type', org_plan_type, nullable=False, server_default='teams'))
    op.add_column('organizations', sa.Column('llm_provider', sa.String(50), nullable=True))
    op.add_column('organizations', sa.Column('llm_api_key_encrypted', sa.Text(), nullable=True))
    op.add_column('organizations', sa.Column('llm_model', sa.String(100), nullable=True))
    op.add_column('organizations', sa.Column('llm_config', sa.dialects.postgresql.JSONB(), nullable=False, server_default='{}'))

    # ── Create usage_limits table ─────────────────────────────────────────────
    op.create_table(
        'usage_limits',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('projects_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('agents_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pods_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skills_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('github_connections_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('jira_connections_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('deployed_projects_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # ── Data migration ────────────────────────────────────────────────────────
    # Mark all existing organizations as 'legacy'
    op.execute("UPDATE organizations SET plan_type = 'legacy'")

    # Create usage_limits rows for all existing users
    # Initialize counts from current data
    op.execute("""
        INSERT INTO usage_limits (id, user_id, projects_count, agents_count, pods_count, skills_count,
                                  github_connections_count, jira_connections_count, deployed_projects_count)
        SELECT
            gen_random_uuid() as id,
            u.id as user_id,
            COALESCE((SELECT COUNT(*) FROM projects WHERE user_id = u.id AND org_id IS NULL), 0) as projects_count,
            COALESCE((SELECT COUNT(*) FROM agents WHERE user_id = u.id AND org_id IS NULL), 0) as agents_count,
            COALESCE((SELECT COUNT(*) FROM pods WHERE user_id = u.id AND org_id IS NULL), 0) as pods_count,
            COALESCE((SELECT COUNT(*) FROM skills WHERE user_id = u.id AND org_id IS NULL), 0) as skills_count,
            COALESCE((SELECT COUNT(*) FROM connections WHERE user_id = u.id AND org_id IS NULL AND type = 'github'), 0) as github_connections_count,
            COALESCE((SELECT COUNT(*) FROM connections WHERE user_id = u.id AND org_id IS NULL AND type = 'jira'), 0) as jira_connections_count,
            0 as deployed_projects_count
        FROM users u
    """)

    # Mark users who are org members
    op.execute("""
        UPDATE users
        SET is_org_member = TRUE,
            locked_to_org_id = (SELECT org_id FROM org_members WHERE user_id = users.id LIMIT 1)
        WHERE id IN (SELECT user_id FROM org_members)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop usage_limits table
    op.drop_table('usage_limits')

    # Drop columns from organizations
    op.drop_column('organizations', 'llm_config')
    op.drop_column('organizations', 'llm_model')
    op.drop_column('organizations', 'llm_api_key_encrypted')
    op.drop_column('organizations', 'llm_provider')
    op.drop_column('organizations', 'plan_type')

    # Drop FK constraint and columns from users
    op.drop_constraint('fk_users_locked_to_org_id', 'users', type_='foreignkey')
    op.drop_column('users', 'llm_config')
    op.drop_column('users', 'llm_model')
    op.drop_column('users', 'llm_api_key_encrypted')
    op.drop_column('users', 'llm_provider')
    op.drop_column('users', 'locked_to_org_id')
    op.drop_column('users', 'is_org_member')
    op.drop_column('users', 'plan_type')

    # Drop ENUMs
    sa.Enum(name='org_plan_type').drop(op.get_bind())
    sa.Enum(name='user_plan_type').drop(op.get_bind())
