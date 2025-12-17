"""create initial tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Check if enum type already exists (PostgreSQL specific)
    if bind.dialect.name == "postgresql":
        result = bind.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'transcription_status'")
        )
        if not result.fetchone():
            bind.execute(
                text("CREATE TYPE transcription_status AS ENUM ('pending', 'processing', 'completed', 'failed')")
            )
        transcription_status = postgresql.ENUM(
            "pending", "processing", "completed", "failed",
            name="transcription_status",
            create_type=False,
        )
    else:
        # SQLite and others
        transcription_status = sa.Enum(
            "pending", "processing", "completed", "failed",
            name="transcription_status",
        )

    op.create_table(
        "user",
        sa.Column(
            "id",
            sa.String(length=36),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)

    op.create_table(
        "transcriptionjob",
        sa.Column(
            "id",
            sa.String(length=36),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", transcription_status, nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("source_object_key", sa.String(length=1024), nullable=False),
        sa.Column("result_object_key", sa.String(length=1024), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_transcription_job_user_created",
        "transcriptionjob",
        ["user_id", "created_at"],
    )

    op.create_table(
        "transcript",
        sa.Column(
            "job_id",
            sa.String(length=36),
            sa.ForeignKey("transcriptionjob.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("plain_text", sa.Text(), nullable=False),
        sa.Column("diarized_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("transcript")
    op.drop_index("ix_transcription_job_user_created", table_name="transcriptionjob")
    op.drop_table("transcriptionjob")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(text("DROP TYPE IF EXISTS transcription_status"))
    else:
        sa.Enum(name="transcription_status").drop(bind, checkfirst=True)
