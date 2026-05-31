# ============================================
# FFCES - مخططات Pydantic (Pydantic Schemas / DTOs)
# ============================================
"""
مخططات البيانات للإدخال والإخراج
Input/Output data schemas for all entities
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# =============================================
# Common / عام
# =============================================
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    page_size: int
    pages: int


# =============================================
# Organization / المؤسسة
# =============================================
class OrganizationBase(BaseModel):
    name: str
    name_en: Optional[str] = None
    code: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    fiscal_year_start: Optional[int] = None
    fiscal_year_end: Optional[int] = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    fiscal_year_start: Optional[int] = None
    fiscal_year_end: Optional[int] = None
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    id: uuid.UUID
    is_active: bool
    logo_url: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# User / المستخدم
# =============================================
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str = "employee"
    department: Optional[str] = None
    job_title: Optional[str] = None


class UserCreate(UserBase):
    password: str
    organization_id: uuid.UUID
    employee_number: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: uuid.UUID
    employee_number: Optional[str] = None
    is_active: bool
    organization_id: uuid.UUID
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Project / المشروع
# =============================================
class ProjectBase(BaseModel):
    name: str
    name_en: Optional[str] = None
    code: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_budget: Decimal = Decimal("0")
    location: Optional[str] = None


class ProjectCreate(ProjectBase):
    organization_id: uuid.UUID
    manager_id: Optional[uuid.UUID] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_budget: Optional[Decimal] = None
    status: Optional[str] = None
    manager_id: Optional[uuid.UUID] = None
    location: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    manager_id: Optional[uuid.UUID] = None
    spent_amount: Decimal = Decimal("0")
    status: str = "active"
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectSummary(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    status: str
    total_budget: Decimal
    spent_amount: Decimal
    remaining_budget: Decimal

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Party / الجهة
# =============================================
class PartyBase(BaseModel):
    name: str
    name_en: Optional[str] = None
    type: str  # employee, vendor, contractor, client, other
    code: str
    national_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    iban: Optional[str] = None


class PartyCreate(PartyBase):
    organization_id: uuid.UUID


class PartyUpdate(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    type: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    iban: Optional[str] = None
    is_active: Optional[bool] = None


class PartyResponse(PartyBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    is_active: bool = True
    created_at: Optional[datetime] = None
    total_balance: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Entitlement Rule / قاعدة الاستحقاق
# =============================================
class EntitlementRuleBase(BaseModel):
    name: str
    name_en: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    entitlement_type: str
    amount: Decimal = Decimal("0")
    currency: str = "SAR"
    unit: Optional[str] = None
    conditions: Optional[str] = None
    max_amount: Optional[Decimal] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None


class EntitlementRuleCreate(EntitlementRuleBase):
    organization_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None


class EntitlementRuleUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    conditions: Optional[str] = None
    is_active: Optional[bool] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None


class EntitlementRuleResponse(EntitlementRuleBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Custody / العهدة
# =============================================
class CustodyBase(BaseModel):
    holder_id: uuid.UUID
    custodian_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    amount: Decimal
    currency: str = "SAR"
    purpose: str
    custody_type: str = "general"
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class CustodyCreate(CustodyBase):
    pass


class CustodyUpdate(BaseModel):
    purpose: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class CustodyResponse(CustodyBase):
    id: uuid.UUID
    status: str = "active"
    issued_date: Optional[datetime] = None
    settled_amount: Decimal = Decimal("0")
    remaining_amount: Decimal = Decimal("0")
    holder_name: Optional[str] = None
    custodian_name: Optional[str] = None
    project_name: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CustodySummary(BaseModel):
    id: uuid.UUID
    purpose: str
    amount: Decimal
    remaining_amount: Decimal
    status: str
    holder_name: str

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Expense / المصروف
# =============================================
class ExpenseBase(BaseModel):
    custody_id: uuid.UUID
    amount: Decimal
    currency: str = "SAR"
    category: str
    description: str
    expense_date: datetime
    receipt_number: Optional[str] = None
    vendor: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    amount: Optional[Decimal] = None
    category: Optional[str] = None
    description: Optional[str] = None
    expense_date: Optional[datetime] = None
    receipt_number: Optional[str] = None
    vendor: Optional[str] = None
    status: Optional[str] = None


class ExpenseResponse(ExpenseBase):
    id: uuid.UUID
    created_by: uuid.UUID
    status: str = "pending"
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Work Record / سجل العمل
# =============================================
class WorkRecordBase(BaseModel):
    user_id: uuid.UUID
    project_id: uuid.UUID
    date: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    hours_worked: float = 0
    location: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None


class WorkRecordCreate(WorkRecordBase):
    pass


class WorkRecordUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    hours_worked: Optional[float] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class WorkRecordResponse(WorkRecordBase):
    id: uuid.UUID
    status: str = "draft"
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Entitlement / الاستحقاق
# =============================================
class EntitlementBase(BaseModel):
    user_id: uuid.UUID
    project_id: uuid.UUID
    rule_id: uuid.UUID
    work_record_id: Optional[uuid.UUID] = None
    amount: Decimal = Decimal("0")
    currency: str = "SAR"
    period_start: datetime
    period_end: datetime
    calculation_basis: Optional[str] = None
    notes: Optional[str] = None


class EntitlementCreate(EntitlementBase):
    pass


class EntitlementUpdate(BaseModel):
    amount: Optional[Decimal] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class EntitlementResponse(EntitlementBase):
    id: uuid.UUID
    status: str = "calculated"
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    payment_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Payment / الدفعة
# =============================================
class PaymentBase(BaseModel):
    payee_id: Optional[uuid.UUID] = None
    payer_id: Optional[uuid.UUID] = None
    amount: Decimal
    currency: str = "SAR"
    payment_method: str  # bank_transfer, cash, check, wire
    payment_date: datetime
    reference_number: Optional[str] = None
    description: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None


class PaymentCreate(PaymentBase):
    organization_id: uuid.UUID


class PaymentUpdate(BaseModel):
    amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    payment_date: Optional[datetime] = None
    reference_number: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class PaymentResponse(PaymentBase):
    id: uuid.UUID
    status: str = "pending"
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    organization_id: uuid.UUID
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Settlement / التسوية
# =============================================
class SettlementBase(BaseModel):
    custody_id: uuid.UUID
    user_id: uuid.UUID
    amount: Decimal
    currency: str = "SAR"
    settlement_date: datetime
    description: Optional[str] = None
    refund_amount: Decimal = Decimal("0")
    notes: Optional[str] = None


class SettlementCreate(SettlementBase):
    pass


class SettlementUpdate(BaseModel):
    amount: Optional[Decimal] = None
    settlement_date: Optional[datetime] = None
    description: Optional[str] = None
    status: Optional[str] = None
    refund_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class SettlementResponse(SettlementBase):
    id: uuid.UUID
    status: str = "pending"
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Account / الحساب
# =============================================
class AccountBase(BaseModel):
    code: str
    name: str
    name_en: Optional[str] = None
    account_type: str  # asset, liability, equity, revenue, expense
    parent_id: Optional[uuid.UUID] = None
    description: Optional[str] = None


class AccountCreate(AccountBase):
    organization_id: uuid.UUID


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class AccountResponse(AccountBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    is_active: bool = True
    balance: Decimal = Decimal("0")
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Ledger Entry / قيد دفتر الأستاذ
# =============================================
class LedgerEntryBase(BaseModel):
    debit_account_id: uuid.UUID
    credit_account_id: uuid.UUID
    amount: Decimal
    currency: str = "SAR"
    description: str
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    journal_number: Optional[str] = None


class LedgerEntryCreate(LedgerEntryBase):
    created_by: uuid.UUID
    organization_id: uuid.UUID


class LedgerEntryResponse(LedgerEntryBase):
    id: uuid.UUID
    entry_date: Optional[datetime] = None
    created_by: uuid.UUID
    organization_id: uuid.UUID
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Audit Log / سجل التدقيق
# =============================================
class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    entity_type: str
    entity_id: uuid.UUID
    old_values: Optional[str] = None
    new_values: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Attachment / المرفق
# =============================================
class AttachmentBase(BaseModel):
    file_name: str
    file_path: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    mime_type: Optional[str] = None
    entity_type: str
    entity_id: uuid.UUID
    description: Optional[str] = None


class AttachmentResponse(AttachmentBase):
    id: uuid.UUID
    uploaded_by: uuid.UUID
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Approval Workflow / سير الموافقة
# =============================================
class ApprovalWorkflowBase(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    approver_id: uuid.UUID
    approval_level: int = 1
    threshold_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class ApprovalWorkflowCreate(ApprovalWorkflowBase):
    pass


class ApprovalWorkflowUpdate(BaseModel):
    status: str  # approved, rejected
    notes: Optional[str] = None


class ApprovalWorkflowResponse(ApprovalWorkflowBase):
    id: uuid.UUID
    status: str = "pending"
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================
# Dashboard / لوحة القيادة
# =============================================
class DashboardStats(BaseModel):
    total_custodies: int = 0
    active_custodies: int = 0
    total_custody_amount: Decimal = Decimal("0")
    pending_expenses: int = 0
    pending_settlements: int = 0
    pending_approvals: int = 0
    total_payments_this_month: Decimal = Decimal("0")
    overdue_custodies: int = 0


class DashboardChart(BaseModel):
    labels: List[str]
    data: List[float]


# =============================================
# Report / التقرير
# =============================================
class ReportRequest(BaseModel):
    report_type: str  # custody_summary, expense_report, settlement_report, entitlement_report, project_report
    project_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    format: str = "json"  # json, pdf, excel


class ReportResponse(BaseModel):
    report_type: str
    generated_at: datetime
    data: dict
    summary: Optional[dict] = None
