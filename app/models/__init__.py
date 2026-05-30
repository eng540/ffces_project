# ============================================================
# SQLAlchemy Models - All Entities
# ============================================================

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, DECIMAL, ForeignKey, Text, ARRAY, JSONB, UUID as SA_UUID, func, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID, INET
import uuid

Base = declarative_base()

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(50))
    settings = Column(JSONB, default={})
    default_currency = Column(String(3), default="USD")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="organization")
    projects = relationship("Project", back_populates="organization")
    parties = relationship("Party", back_populates="organization")
    accounts = relationship("Account", back_populates="organization")

class User(Base):
    __tablename__ = "users"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20))
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    mfa_enabled = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="users")
    held_custodies = relationship("Custody", foreign_keys="Custody.holder_id", back_populates="holder")
    issued_custodies = relationship("Custody", foreign_keys="Custody.issued_by", back_populates="issuer")

class Project(Base):
    __tablename__ = "projects"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(100), nullable=False)
    budget_limit = Column(DECIMAL(15, 2))
    status = Column(String(50), default="active")
    manager_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    location = Column(JSONB)
    start_date = Column(Date)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="projects")
    custodies = relationship("Custody", back_populates="project")
    expenses = relationship("Expense", back_populates="project")

class Party(Base):
    __tablename__ = "parties"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    type = Column(String(50), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20))
    id_number = Column(String(50))
    bank_info = Column(JSONB, default={})
    default_daily_rate = Column(DECIMAL(10, 2))
    default_monthly_salary = Column(DECIMAL(12, 2))
    default_hourly_rate = Column(DECIMAL(10, 2))
    unit_prices = Column(JSONB, default={})
    metadata = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="parties")
    entitlement_rules = relationship("EntitlementRule", back_populates="party")
    work_records = relationship("WorkRecord", back_populates="party")

class EntitlementRule(Base):
    __tablename__ = "entitlement_rules"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    party_id = Column(SA_UUID(as_uuid=True), ForeignKey("parties.id"), nullable=False)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id"))
    calc_type = Column(String(50), nullable=False)
    rate = Column(DECIMAL(12, 4), nullable=False)
    unit = Column(String(50))
    components = Column(JSONB, default=[])
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    min_quantity = Column(DECIMAL(10, 2))
    max_quantity = Column(DECIMAL(10, 2))
    is_active = Column(Boolean, default=True)
    created_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    party = relationship("Party", back_populates="entitlement_rules")

class Custody(Base):
    __tablename__ = "custodies"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    custody_number = Column(String(100), unique=True, nullable=False)
    holder_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    issued_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id"))
    amount = Column(DECIMAL(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    purpose = Column(Text, nullable=False)
    status = Column(String(50), default="open")
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(Date)
    closed_at = Column(DateTime(timezone=True))
    closed_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    holder = relationship("User", foreign_keys=[holder_id], back_populates="held_custodies")
    issuer = relationship("User", foreign_keys=[issued_by], back_populates="issued_custodies")
    project = relationship("Project", back_populates="custodies")
    expenses = relationship("Expense", back_populates="custody")

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    custody_id = Column(SA_UUID(as_uuid=True), ForeignKey("custodies.id"), nullable=False)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    expense_date = Column(Date, nullable=False)
    beneficiary_type = Column(String(50))
    party_id = Column(SA_UUID(as_uuid=True), ForeignKey("parties.id"))
    beneficiary_name = Column(String(255))
    attachment_ids = Column(ARRAY(SA_UUID(as_uuid=True)), default=[])
    status = Column(String(50), default="draft")
    approved_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    location = Column(JSONB)
    created_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    custody = relationship("Custody", back_populates="expenses")
    project = relationship("Project", back_populates="expenses")

class WorkRecord(Base):
    __tablename__ = "work_records"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    party_id = Column(SA_UUID(as_uuid=True), ForeignKey("parties.id"), nullable=False)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    record_date = Column(Date, nullable=False)
    quantity = Column(DECIMAL(10, 2), nullable=False)
    unit = Column(String(50), nullable=False)
    description = Column(Text)
    location = Column(JSONB)
    verified_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    verified_at = Column(DateTime(timezone=True))
    verification_method = Column(String(50))
    photo_ids = Column(ARRAY(SA_UUID(as_uuid=True)), default=[])
    status = Column(String(50), default="pending")
    rejection_reason = Column(Text)
    created_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    party = relationship("Party", back_populates="work_records")

class Entitlement(Base):
    __tablename__ = "entitlements"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    party_id = Column(SA_UUID(as_uuid=True), ForeignKey("parties.id"), nullable=False)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    rule_id = Column(SA_UUID(as_uuid=True), ForeignKey("entitlement_rules.id"))
    work_record_id = Column(SA_UUID(as_uuid=True), ForeignKey("work_records.id"))
    amount = Column(DECIMAL(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    calculation_details = Column(JSONB, nullable=False, default={})
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(String(50), default="calculated")
    paid_amount = Column(DECIMAL(15, 2), default=0)
    remaining_amount = Column(DECIMAL(15, 2))
    created_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Payment(Base):
    __tablename__ = "payments"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    party_id = Column(SA_UUID(as_uuid=True), ForeignKey("parties.id"), nullable=False)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id"))
    custody_id = Column(SA_UUID(as_uuid=True), ForeignKey("custodies.id"))
    amount = Column(DECIMAL(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    payment_type = Column(String(50), nullable=False)
    payment_method = Column(String(50))
    reference_number = Column(String(255))
    entitlement_ids = Column(ARRAY(SA_UUID(as_uuid=True)), default=[])
    attachment_ids = Column(ARRAY(SA_UUID(as_uuid=True)), default=[])
    paid_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    custody_id = Column(SA_UUID(as_uuid=True), ForeignKey("custodies.id"), nullable=False)
    settlement_type = Column(String(50), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    target_custody_id = Column(SA_UUID(as_uuid=True), ForeignKey("custodies.id"))
    status = Column(String(50), default="pending")
    settled_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    settled_at = Column(DateTime(timezone=True))
    notes = Column(Text)
    attachment_ids = Column(ARRAY(SA_UUID(as_uuid=True)), default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Account(Base):
    __tablename__ = "accounts"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    code = Column(String(50), nullable=False)
    name_ar = Column(String(255), nullable=False)
    name_en = Column(String(255))
    type = Column(String(50), nullable=False)
    parent_id = Column(SA_UUID(as_uuid=True), ForeignKey("accounts.id"))
    level = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="accounts")

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    entry_type = Column(String(50), nullable=False)
    reference_id = Column(SA_UUID(as_uuid=True), nullable=False)
    reference_type = Column(String(50), nullable=False)
    debit_account_id = Column(SA_UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    credit_account_id = Column(SA_UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    entry_date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    immutable_hash = Column(String(64), nullable=False)
    previous_hash = Column(String(64))
    created_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(50), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(SA_UUID(as_uuid=True), nullable=False)
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    storage_path = Column(String(500), nullable=False)
    file_size = Column(DECIMAL(20, 0))
    checksum = Column(String(64))
    uploaded_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(SA_UUID(as_uuid=True), nullable=False)
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
