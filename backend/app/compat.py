"""
Database compatibility layer.
Provides column types that work with both PostgreSQL and SQLite.
"""
import json
import uuid as _uuid

from sqlalchemy import String, Text, TypeDecorator


class PortableUUID(TypeDecorator):
    """UUID type that works on both PostgreSQL (native UUID) and SQLite (CHAR(36))."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return _uuid.UUID(value)
        return value


class PortableJSON(TypeDecorator):
    """JSON type that works on both PostgreSQL (JSONB) and SQLite (TEXT with JSON)."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value
