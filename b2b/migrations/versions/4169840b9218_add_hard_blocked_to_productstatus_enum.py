"""add_hard_blocked_to_productstatus_enum

Revision ID: 4169840b9218
Revises: 270bc3b1c63a
Create Date: 2026-05-10 15:14:23.243677

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4169840b9218'
down_revision: Union[str, Sequence[str], None] = '270bc3b1c63a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE productstatus ADD VALUE 'HARD_BLOCKED'")
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE productstatus RENAME TO productstatus_old")
    op.execute("CREATE TYPE productstatus AS ENUM('CREATED', 'ON_MODERATION', 'MODERATED', 'BLOCKED')")
    op.execute("ALTER TABLE products ALTER COLUMN status TYPE productstatus USING status::text::productstatus")
    op.execute("DROP TYPE productstatus_old")
    pass
