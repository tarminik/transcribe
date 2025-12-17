"""add transcription history table"""

from alembic import op
import sqlalchemy as sa

revision = "0002_transcription_history"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transcription_history",
        sa.Column("id", sa.String(length=36), nullable=False, primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("transcriptionjob.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint(
        "uq_transcription_history_job_id", "transcription_history", ["job_id"]
    )
    op.create_index(
        "ix_transcription_history_user_created",
        "transcription_history",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_transcription_history_user_created", table_name="transcription_history"
    )
    op.drop_constraint(
        "uq_transcription_history_job_id",
        "transcription_history",
        type_="unique",
    )
    op.drop_table("transcription_history")
