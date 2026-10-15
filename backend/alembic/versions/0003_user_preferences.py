"""add user preferences

Revision ID: 0003_user_preferences
Revises: 975eaf7fa546
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_user_preferences"
down_revision = "975eaf7fa546"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("theme", sa.String(length=20), nullable=False, server_default="system"),
        sa.Column("accent", sa.String(length=20), nullable=False, server_default="purple"),
        sa.Column("compact_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_user_preference_user"),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"])


def downgrade():
    op.drop_index("ix_user_preferences_user_id", table_name="user_preferences")
    op.drop_table("user_preferences")
