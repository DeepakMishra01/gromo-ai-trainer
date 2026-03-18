"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Categories
    op.create_table(
        "categories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("gromo_category_id", sa.String(255), unique=True, nullable=True),
        sa.Column("is_excluded", sa.Boolean(), default=False),
        sa.Column("synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Products
    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("gromo_product_id", sa.String(255), unique=True, nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("features", JSONB(), nullable=True),
        sa.Column("eligibility", JSONB(), nullable=True),
        sa.Column("fees", JSONB(), nullable=True),
        sa.Column("benefits", JSONB(), nullable=True),
        sa.Column("faqs", JSONB(), nullable=True),
        sa.Column("raw_data", JSONB(), nullable=True),
        sa.Column("synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Avatars
    op.create_table(
        "avatars",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("image_path", sa.String(500), nullable=True),
        sa.Column("is_default", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Voices
    op.create_table(
        "voices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sample_path", sa.String(500), nullable=True),
        sa.Column("language", sa.String(50), default="hinglish"),
        sa.Column("is_default", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # VideoJobs
    op.create_table(
        "video_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("job_type", sa.Enum("single_product", "category_overview", "comparison", "ppt_mode", name="jobtype"), nullable=False),
        sa.Column("product_ids", JSONB(), nullable=True),
        sa.Column("avatar_id", UUID(as_uuid=True), sa.ForeignKey("avatars.id"), nullable=True),
        sa.Column("voice_id", UUID(as_uuid=True), sa.ForeignKey("voices.id"), nullable=True),
        sa.Column("language", sa.String(50), default="hinglish"),
        sa.Column("status", sa.Enum("queued", "generating_script", "generating_audio", "generating_avatar", "compositing", "completed", "failed", name="jobstatus"), default="queued"),
        sa.Column("progress", sa.Integer(), default=0),
        sa.Column("script_text", sa.Text(), nullable=True),
        sa.Column("audio_path", sa.String(500), nullable=True),
        sa.Column("video_path", sa.String(500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("ppt_file_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    # VideoJobLogs
    op.create_table(
        "video_job_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("video_job_id", UUID(as_uuid=True), sa.ForeignKey("video_jobs.id"), nullable=False),
        sa.Column("step", sa.String(100), nullable=False),
        sa.Column("status", sa.Enum("started", "completed", "failed", name="logstatus"), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # KnowledgeBase
    op.create_table(
        "knowledge_base",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("video_job_id", UUID(as_uuid=True), sa.ForeignKey("video_jobs.id"), nullable=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("timestamp_start", sa.Float(), nullable=True),
        sa.Column("timestamp_end", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # RoleplaySessions
    op.create_table(
        "roleplay_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("difficulty", sa.Enum("easy", "medium", "hard", name="difficulty"), nullable=False),
        sa.Column("conversation_log", JSONB(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("skill_scores", JSONB(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("roleplay_sessions")
    op.drop_table("knowledge_base")
    op.drop_table("video_job_logs")
    op.drop_table("video_jobs")
    op.drop_table("voices")
    op.drop_table("avatars")
    op.drop_table("products")
    op.drop_table("categories")
    op.execute("DROP TYPE IF EXISTS jobtype")
    op.execute("DROP TYPE IF EXISTS jobstatus")
    op.execute("DROP TYPE IF EXISTS logstatus")
    op.execute("DROP TYPE IF EXISTS difficulty")
