# ============================================
# FFCES - نماذج قاعدة البيانات (Database Models)
# ============================================
"""
جميع نماذج SQLAlchemy للنظام
All SQLAlchemy ORM models for the FFCES system
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, Numeric as DECIMAL, Enum, CheckConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID as SA_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Single source of truth for Base - from database module
from app.core.database import Base


# =============================================
# 1. المؤسسة / Organization
# =============================================
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    name_en = Column(String(255))
    code = Column(String(50), unique=True, nullable=False)
    address = Column(Text)
    phone = Column(String(50))
    email = Column(String(255))
    logo_url = Column(String(500))
    fiscal_year_start = Column(Integer)  # Month number 1-12
    fiscal_year_end = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="organization")
    projects = relationship("Project", back_populates="organization")
    entitlement_rules = relationship("EntitlementRule", back_populates="organization")
    accounts = relationship("Account", back_populates="organization")


# =============================================
# 2. المستخدم / User
# =============================================
class User(Base):
    __tablename__ = "users"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    employee_number = Column(String(50), unique=True)
    phone = Column(String(50))
    role = Column(String(50), nullable=False, default="employee")  # admin, accountant, manager, employee
    department = Column(String(100))
    job_title = Column(String(200))
    is_active = Column(Boolean, default=True)
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="users")
    custodies_as_holder = relationship("Custody", foreign_keys="Custody.holder_id", back_populates="holder")
    custodies_as_custodian = relationship("Custody", foreign_keys="Custody.custodian_id", back_populates="custodian")
    expenses = relationship("Expense", foreign_keys="Expense.created_by", back_populates="created_by_user")
    work_records = relationship("WorkRecord", foreign_keys="WorkRecord.user_id", back_populates="user")
    settlements = relationship("Settlement", foreign_keys="Settlement.user_id", back_populates="user")
    approvals_requested = relationship("ApprovalWorkflow", foreign_keys="ApprovalWorkflow.approver_id", back_populates="approver")


# =============================================
# 3. المشروع / Project
# =============================================
class Project(Base):
    __tablename__ = "projects"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    name_en = Column(String(255))
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    total_budget = Column(DECIMAL(15, 2), default=0)
    spent_amount = Column(DECIMAL(15, 2), default=0)
    status = Column(String(50), default="active")  # active, completed, paused, cancelled
    manager_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    location = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="projects")
    manager = relationship("User", foreign_keys=[manager_id])
    custodies = relationship("Custody", back_populates="project")
    work_records = relationship("WorkRecord", back_populates="project")
    entitlements = relationship("Entitlement", back_populates="project")


# =============================================
# 4. الجهة / Party
# =============================================
class Party(Base):
    __tablename__ = "parties"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    name_en = Column(String(255))
    type = Column(String(50), nullable=False)  # employee, vendor, contractor, client, other
    code = Column(String(50), unique=True, nullable=False)
    national_id = Column(String(50))
    phone = Column(String(50))
    email = Column(String(255))
    address = Column(Text)
    bank_name = Column(String(255))
    bank_account = Column(String(100))
    iban = Column(String(50))
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship("Organization")
    payments_received = relationship("Payment", foreign_keys="Payment.payee_id", back_populates="payee")
    payments_made = relationship("Payment", foreign_keys="Payment.payer_id", back_populates="payer")


# =============================================
# 5. قواعد الاستحقاق / Entitlement Rule
# =============================================
class EntitlementRule(Base):
    __tablename__ = "entitlement_rules"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    name_en = Column(String(255))
    description = Column(Text)
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id"))
    role = Column(String(50))  # applicable to which role
    entitlement_type = Column(String(50), nullable=False)  # transportation, housing, meals, etc.
    amount = Column(DECIMAL(15, 2), nullable=False, default=0)
    currency = Column(String(10), default="SAR")
    unit = Column(String(50))  # daily, monthly, per_km, per_stay
    conditions = Column(Text)  # JSON conditions
    max_amount = Column(DECIMAL(15, 2))
    is_active = Column(Boolean, default=True)
    effective_date = Column(DateTime(timezone=True))
    expiry_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="entitlement_rules")
    project = relationship("Project")
    entitlements = relationship("Entitlement", back_populates="rule")


# =============================================
# 6. العهدة / Custody
# =============================================
class Custody(Base):
    __tablename__ = "custodies"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    holder_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    custodian_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id"))
    amount = Column(DECIMAL(15, 2), nullable=False, default=0)
    currency = Column(String(10), default="SAR")
    purpose = Column(Text, nullable=False)
    custody_type = Column(String(50), default="general")  # general, project, travel, emergency
    status = Column(String(50), default="active")  # active, partially_settled, settled, overdue
    issued_date = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True))
    settled_amount = Column(DECIMAL(15, 2), default=0)
    remaining_amount = Column(DECIMAL(15, 2), default=0)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    holder = relationship("User", foreign_keys=[holder_id], back_populates="custodies_as_holder")
    custodian = relationship("User", foreign_keys=[custodian_id], back_populates="custodies_as_custodian")
    project = relationship("Project", back_populates="custodies")
    expenses = relationship("Expense", back_populates="custody")
    settlements = relationship("Settlement", back_populates="custody")

    # Check constraint
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_custody_amount_positive"),
        CheckConstraint(
            "settled_amount >= 0 AND settled_amount <= amount",
            name="ck_custody_settled_range",
        ),
    )


# =============================================
# 7. المصروف / Expense
# =============================================
class Expense(Base):
    __tablename__ = "expenses"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    custody_id = Column(SA_UUID(as_uuid=True), ForeignKey("custodies.id"), nullable=False)
    created_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False, default=0)
    currency = Column(String(10), default="SAR")
    category = Column(String(100), nullable=False)  # transportation, meals, accommodation, etc.
    description = Column(Text, nullable=False)
    expense_date = Column(DateTime(timezone=True), nullable=False)
    receipt_number = Column(String(100))
    vendor = Column(String(255))
    status = Column(String(50), default="pending")  # pending, approved, rejected, verified
    approved_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    custody = relationship("Custody", back_populates="expenses")
    created_by_user = relationship("User", foreign_keys=[created_by], back_populates="expenses")
    approver = relationship("User", foreign_keys=[approved_by])

    # Indexes
    __table_args__ = (
        Index("ix_expense_custody_id", "custody_id"),
        Index("ix_expense_category", "category"),
        Index("ix_expense_status", "status"),
    )


# =============================================
# 8. سجل العمل / Work Record
# =============================================
class WorkRecord(Base):
    __tablename__ = "work_records"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    hours_worked = Column(Float, default=0)
    location = Column(String(500))
    description = Column(Text)
    status = Column(String(50), default="draft")  # draft, submitted, approved, rejected
    approved_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="work_records")
    project = relationship("Project", back_populates="work_records")
    approver = relationship("User", foreign_keys=[approved_by])


# =============================================
# 9. الاستحقاق / Entitlement
# =============================================
class Entitlement(Base):
    __tablename__ = "entitlements"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(SA_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    rule_id = Column(SA_UUID(as_uuid=True), ForeignKey("entitlement_rules.id"), nullable=False)
    work_record_id = Column(SA_UUID(as_uuid=True), ForeignKey("work_records.id"))
    amount = Column(DECIMAL(15, 2), nullable=False, default=0)
    currency = Column(String(10), default="SAR")
    status = Column(String(50), default="calculated")  # calculated, approved, paid, rejected
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    calculation_basis = Column(Text)  # JSON: how the amount was calculated
    approved_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    paid_at = Column(DateTime(timezone=True))
    payment_id = Column(SA_UUID(as_uuid=True))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    project = relationship("Project", back_populates="entitlements")
    rule = relationship("EntitlementRule", back_populates="entitlements")
    work_record = relationship("WorkRecord")
    approver = relationship("User", foreign_keys=[approved_by])


# =============================================
# 10. الدفعة / Payment
# =============================================
class Payment(Base):
    __tablename__ = "payments"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payee_id = Column(SA_UUID(as_uuid=True), ForeignKey("parties.id"))
    payer_id = Column(SA_UUID(as_uuid=True), ForeignKey("parties.id"))
    amount = Column(DECIMAL(15, 2), nullable=False, default=0)
    currency = Column(String(10), default="SAR")
    payment_method = Column(String(50), nullable=False)  # bank_transfer, cash, check, wire
    payment_date = Column(DateTime(timezone=True), nullable=False)
    reference_number = Column(String(100))
    description = Column(Text)
    status = Column(String(50), default="pending")  # pending, processing, completed, failed, cancelled
    bank_name = Column(String(255))
    bank_account = Column(String(100))
    created_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    payee = relationship("Party", foreign_keys=[payee_id], back_populates="payments_received")
    payer = relationship("Party", foreign_keys=[payer_id], back_populates="payments_made")
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    organization = relationship("Organization")

    __table_args__ = (
        Index("ix_payment_status", "status"),
        Index("ix_payment_date", "payment_date"),
    )


# =============================================
# 11. التسوية / Settlement
# =============================================
class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    custody_id = Column(SA_UUID(as_uuid=True), ForeignKey("custodies.id"), nullable=False)
    user_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False, default=0)
    currency = Column(String(10), default="SAR")
    settlement_date = Column(DateTime(timezone=True), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="pending")  # pending, approved, rejected, completed
    approved_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    refund_amount = Column(DECIMAL(15, 2), default=0)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    custody = relationship("Custody", back_populates="settlements")
    user = relationship("User", foreign_keys=[user_id], back_populates="settlements")
    approver = relationship("User", foreign_keys=[approved_by])


# =============================================
# 12. الحساب / Account (Chart of Accounts)
# =============================================
class Account(Base):
    __tablename__ = "accounts"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    name_en = Column(String(255))
    account_type = Column(String(50), nullable=False)  # asset, liability, equity, revenue, expense
    parent_id = Column(SA_UUID(as_uuid=True), ForeignKey("accounts.id"))
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    balance = Column(DECIMAL(15, 2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="accounts")
    parent = relationship("Account", remote_side=[id])
    children = relationship("Account", back_populates="parent")
    ledger_entries_debit = relationship("LedgerEntry", foreign_keys="LedgerEntry.debit_account_id", back_populates="debit_account")
    ledger_entries_credit = relationship("LedgerEntry", foreign_keys="LedgerEntry.credit_account_id", back_populates="credit_account")

    __table_args__ = (
        Index("ix_account_code", "code"),
        Index("ix_account_type", "account_type"),
    )


# =============================================
# 13. قيد دفتر الأستاذ / Ledger Entry
# =============================================
class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    debit_account_id = Column(SA_UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    credit_account_id = Column(SA_UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False, default=0)
    currency = Column(String(10), default="SAR")
    description = Column(Text, nullable=False)
    reference_type = Column(String(100))  # custody, expense, settlement, payment, entitlement
    reference_id = Column(SA_UUID(as_uuid=True))
    created_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(SA_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    journal_number = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    debit_account = relationship("Account", foreign_keys=[debit_account_id], back_populates="ledger_entries_debit")
    credit_account = relationship("Account", foreign_keys=[credit_account_id], back_populates="ledger_entries_credit")
    creator = relationship("User", foreign_keys=[created_by])
    organization = relationship("Organization")

    __table_args__ = (
        Index("ix_ledger_reference", "reference_type", "reference_id"),
        Index("ix_ledger_date", "entry_date"),
    )


# =============================================
# 14. سجل التدقيق / Audit Log
# =============================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(100), nullable=False)  # create, update, delete, approve, reject, etc.
    entity_type = Column(String(100), nullable=False)  # custody, expense, settlement, etc.
    entity_id = Column(SA_UUID(as_uuid=True), nullable=False)
    old_values = Column(Text)  # JSON
    new_values = Column(Text)  # JSON
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_user", "user_id"),
        Index("ix_audit_date", "created_at"),
    )


# =============================================
# 15. المرفق / Attachment
# =============================================
class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(100))
    mime_type = Column(String(100))
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(SA_UUID(as_uuid=True), nullable=False)
    uploaded_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    uploader = relationship("User", foreign_keys=[uploaded_by])

    __table_args__ = (
        Index("ix_attachment_entity", "entity_type", "entity_id"),
    )


# =============================================
# 16. سير الموافقة / Approval Workflow
# =============================================
class ApprovalWorkflow(Base):
    __tablename__ = "approval_workflows"

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(SA_UUID(as_uuid=True), nullable=False)
    approver_id = Column(SA_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approval_level = Column(Integer, nullable=False, default=1)
    status = Column(String(50), default="pending")  # pending, approved, rejected, skipped
    threshold_amount = Column(DECIMAL(15, 2))
    approved_at = Column(DateTime(timezone=True))
    rejected_at = Column(DateTime(timezone=True))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    approver = relationship("User", foreign_keys=[approver_id], back_populates="approvals_requested")

    __table_args__ = (
        Index("ix_approval_entity", "entity_type", "entity_id"),
        Index("ix_approval_approver", "approver_id"),
        Index("ix_approval_status", "status"),
    )
