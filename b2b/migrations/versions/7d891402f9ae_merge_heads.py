"""merge heads

Revision ID: 7d891402f9ae
Revises: 9cb1e73e7ed1, fd48d403b123
Create Date: 2026-06-11 11:14:16.969517

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d891402f9ae'
down_revision: Union[str, Sequence[str], None] = ('9cb1e73e7ed1', 'fd48d403b123')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
