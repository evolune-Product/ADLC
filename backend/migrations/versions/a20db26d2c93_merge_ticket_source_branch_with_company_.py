"""merge ticket source branch with company os branch

Revision ID: a20db26d2c93
Revises: c4d5e6f7a8b9, d0e1f2a3b4c5
Create Date: 2026-08-29 19:53:20.939478

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a20db26d2c93'
down_revision: Union[str, Sequence[str], None] = ('c4d5e6f7a8b9', 'd0e1f2a3b4c5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
