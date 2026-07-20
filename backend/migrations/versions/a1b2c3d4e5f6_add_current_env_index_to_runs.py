"""add current_env_index to runs

Revision ID: a1b2c3d4e5f6
Revises: b48d141e700e
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'b48d141e700e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'runs',
        sa.Column('current_env_index', sa.Integer(), nullable=False, server_default='-1'),
    )


def downgrade() -> None:
    op.drop_column('runs', 'current_env_index')
