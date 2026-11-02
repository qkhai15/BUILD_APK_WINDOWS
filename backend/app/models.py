from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Index, Text, JSON, CheckConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .db import Base

def utcnow(): return datetime.now(timezone.utc)

class SchoolYear(Base):
    __tablename__ = 'school_years'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

class SchoolClass(Base):
    __tablename__ = 'classes'
    __table_args__ = (UniqueConstraint('school_year_id','name'), CheckConstraint('grade IN (10,11,12)',name='ck_class_grade'))
    id: Mapped[int] = mapped_column(primary_key=True)
    school_year_id: Mapped[int] = mapped_column(ForeignKey('school_years.id', ondelete='RESTRICT'), index=True)
    name: Mapped[str] = mapped_column(String(20), index=True)
    grade: Mapped[int] = mapped_column(Integer)

class Student(Base):
    __tablename__ = 'students'
    __table_args__ = (CheckConstraint("gender IN ('Nam','Nữ')",name='ck_student_gender'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey('classes.id'), index=True)
    school_year_id: Mapped[int] = mapped_column(ForeignKey('school_years.id'), index=True)
    birth_date: Mapped[datetime] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(String(12))
    school_class = relationship('SchoolClass')

class Role(Base):
    __tablename__ = 'roles'
    name: Mapped[str] = mapped_column(String(20), primary_key=True)
    description: Mapped[str] = mapped_column(String(100))

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(150))
    role: Mapped[str] = mapped_column(ForeignKey('roles.name'),index=True)  # admin, leadership, homeroom, recorder
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class UserClassAssignment(Base):
    __tablename__ = 'user_class_assignments'
    __table_args__ = (UniqueConstraint('user_id','class_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey('classes.id', ondelete='CASCADE'), index=True)

class ViolationType(Base):
    __tablename__ = 'violation_types'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(90), unique=True)
    display_order: Mapped[int] = mapped_column(Integer, unique=True)
    severe: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Violation(Base):
    __tablename__ = 'violations'
    __table_args__ = (Index('ix_violations_date_class', 'happened_on', 'class_id'), CheckConstraint("status IN ('active','void')",name='ck_violation_status'))
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('students.id'), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey('classes.id'), index=True)  # snapshot at entry
    school_year_id: Mapped[int] = mapped_column(ForeignKey('school_years.id'), index=True)
    violation_type_id: Mapped[int] = mapped_column(ForeignKey('violation_types.id'), index=True)
    happened_on: Mapped[datetime] = mapped_column(Date, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    recorded_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default='active', index=True)
    void_reason: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    student = relationship('Student')
    violation_type = relationship('ViolationType')
    recorder = relationship('User')
    school_class = relationship('SchoolClass')

class WarningRule(Base):
    __tablename__ = 'warning_rules'
    __table_args__ = (CheckConstraint('min_count >= 0',name='ck_warning_min'),
                      CheckConstraint('max_count IS NULL OR max_count >= min_count',name='ck_warning_max'))
    id: Mapped[int] = mapped_column(primary_key=True)
    min_count: Mapped[int] = mapped_column(Integer)
    max_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    label: Mapped[str] = mapped_column(String(50))
    recommendation: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    previous: Mapped[dict | None] = mapped_column(JSON)
    current: Mapped[dict | None] = mapped_column(JSON)
    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ip_address: Mapped[str | None] = mapped_column(String(100))

class ImportJob(Base):
    __tablename__ = 'import_jobs'
    id: Mapped[int] = mapped_column(primary_key=True)
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    school_year_id: Mapped[int | None] = mapped_column(ForeignKey('school_years.id'))
    created: Mapped[int] = mapped_column(Integer, default=0)
    unchanged: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16))
    notes: Mapped[str | None] = mapped_column(Text)
    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ViolationPhoto(Base):
    """Private evidence metadata. Binary images are stored outside public web paths."""
    __tablename__ = 'violation_photos'
    __table_args__ = (UniqueConstraint('violation_id', 'sha256', name='uq_violation_photo_hash'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    violation_id: Mapped[int] = mapped_column(ForeignKey('violations.id', ondelete='RESTRICT'), index=True)
    file_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), default='image/jpeg', nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    violation = relationship('Violation', back_populates='photos')

Violation.photos = relationship('ViolationPhoto', back_populates='violation', order_by='ViolationPhoto.id')
