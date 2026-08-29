"""merge local plan/llm-config branch with phase 11 commercial branch

Revision ID: b363c8b2fee8
Revises: 4545de715245, a7b8c9d0e1f2
Create Date: 2026-08-28 00:16:20.066136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b363c8b2fee8'
down_revision: Union[str, Sequence[str], None] = ('4545de715245', 'a7b8c9d0e1f2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
