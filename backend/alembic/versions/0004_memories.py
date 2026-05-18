"""Add memories table

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("scope", sa.String(200), nullable=False),
        sa.Column("memory_type", sa.String(20), nullable=False),
        sa.Column("key", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "importance",
            sa.Float(),
            nullable=False,
            server_default="0.5",
        ),
        sa.Column(
            "access_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index(
        "idx_memories_scope",
        "memories",
        ["scope", "memory_type"],
    )


def downgrade() -> None:
    op.drop_index("idx_memories_scope", table_name="memories")
    op.drop_table("memories")
