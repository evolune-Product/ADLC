"""add_default_branch_to_projects

Revision ID: 4545de715245
Revises: eafbed19fe26
Create Date: 2026-08-11 17:06:16.456135

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4545de715245'
down_revision: Union[str, Sequence[str], None] = 'eafbed19fe26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('projects', sa.Column('default_branch', sa.String(100), nullable=True, server_default='main'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('projects', 'default_branch')
