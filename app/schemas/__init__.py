# ============================================================
# Pydantic Schemas - Request/Response DTOs
# ============================================================

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

# ------------------- Organization -------------------
class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: Optional[str] = None
    default_currency: str = "USD"

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationResponse(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    is_active: bool
    created_at: datetime

# ------------------- User -------------------
class UserBase(BaseModel):
    email: str
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = None
    role: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    organization_id: UUID

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

# ------------------- Project -------------------
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=100)
    budget_limit: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class ProjectCreate(ProjectBase):
    organization_id: UUID

class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    status: str
    manager_id: Optional[UUID] = None
    created_at: datetime

# ------------------- Party -------------------
class PartyBase(BaseModel):
    type: str
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = None
    id_number: Optional[str] = None
    default_daily_rate: Optional[Decimal] = None
    default_monthly_salary: Optional[Decimal] = None
    default_hourly_rate: Optional[Decimal] = None
    unit_prices: Optional[Dict[str, Any]] = None
    bank_info: Optional[Dict[str, Any]] = None

class PartyCreate(PartyBase):
    organization_id: UUID

class PartyResponse(PartyBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime

class PartyBalance(BaseModel):
    total_entitlements: Decimal
    total_payments: Decimal
    total_advances: Decimal
    total_deductions: Decimal
    net_balance: Decimal

class PartyStatement(BaseModel):
    party: PartyResponse
    balance: PartyBalance
    recent_transactions: List[Dict[str, Any]]

# ------------------- Entitlement Rule -------------------
class EntitlementRuleBase(BaseModel):
    calc_type: str = Field(..., pattern="^(daily|monthly|hourly|quantity|lump_sum|mixed)$")
    rate: Decimal = Field(..., gt=0)
    unit: Optional[str] = None
    components: Optional[List[Dict[str, Any]]] = None
    effective_from: date
    effective_to: Optional[date] = None
    min_quantity: Optional[Decimal] = None
    max_quantity: Optional[Decimal] = None

class EntitlementRuleCreate(EntitlementRuleBase):
    party_id: UUID
    project_id: Optional[UUID] = None

class EntitlementRuleResponse(EntitlementRuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    party_id: UUID
    project_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime

# ------------------- Custody -------------------
class CustodyBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    purpose: str = Field(..., min_length=1)
    due_date: Optional[date] = None
    notes: Optional[str] = None

class CustodyCreate(CustodyBase):
    holder_id: UUID
    project_id: Optional[UUID] = None

class CustodyResponse(CustodyBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    custody_number: str
    holder_id: UUID
    issued_by: UUID
    project_id: Optional[UUID] = None
    status: str
    issued_at: datetime
    closed_at: Optional[datetime] = None
    total_expenses: Optional[Decimal] = None
    total_settlements: Optional[Decimal] = None
    remaining_balance: Optional[Decimal] = None

class CustodyBalanceResponse(BaseModel):
    original_amount: Decimal
    total_expenses: Decimal
    total_settlements: Decimal
    remaining_balance: Decimal
    status: str

# ------------------- Expense -------------------
class ExpenseBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    category: str
    description: str = Field(..., min_length=1)
    expense_date: date
    beneficiary_type: Optional[str] = "anonymous"
    party_id: Optional[UUID] = None
    beneficiary_name: Optional[str] = None
    location: Optional[Dict[str, Any]] = None

class ExpenseCreate(ExpenseBase):
    custody_id: UUID
    project_id: UUID

class ExpenseResponse(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    custody_id: UUID
    project_id: UUID
    status: str
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_by: UUID
    created_at: datetime

class ExpenseApproval(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    rejection_reason: Optional[str] = None

# ------------------- Work Record -------------------
class WorkRecordBase(BaseModel):
    record_date: date
    quantity: Decimal = Field(..., gt=0)
    unit: str
    description: Optional[str] = None
    location: Optional[Dict[str, Any]] = None

class WorkRecordCreate(WorkRecordBase):
    party_id: UUID
    project_id: UUID

class WorkRecordResponse(WorkRecordBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    party_id: UUID
    project_id: UUID
    status: str
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    created_by: UUID
    created_at: datetime

class WorkRecordVerification(BaseModel):
    status: str = Field(..., pattern="^(verified|rejected)$")
    verification_method: str = "manual"
    rejection_reason: Optional[str] = None

# ------------------- Entitlement -------------------
class EntitlementBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    period_start: date
    period_end: date
    calculation_details: Dict[str, Any]

class EntitlementCreate(EntitlementBase):
    party_id: UUID
    project_id: UUID
    rule_id: Optional[UUID] = None
    work_record_id: Optional[UUID] = None

class EntitlementResponse(EntitlementBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    party_id: UUID
    project_id: UUID
    rule_id: Optional[UUID] = None
    work_record_id: Optional[UUID] = None
    status: str
    paid_amount: Decimal
    remaining_amount: Decimal
    created_at: datetime

class EntitlementCalculationRequest(BaseModel):
    party_id: UUID
    project_id: UUID
    period_start: date
    period_end: date

# ------------------- Payment -------------------
class PaymentBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    payment_type: str
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    entitlement_ids: Optional[List[UUID]] = None
    notes: Optional[str] = None
    paid_at: datetime

class PaymentCreate(PaymentBase):
    party_id: UUID
    project_id: Optional[UUID] = None
    custody_id: Optional[UUID] = None

class PaymentResponse(PaymentBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    party_id: UUID
    project_id: Optional[UUID] = None
    custody_id: Optional[UUID] = None
    paid_by: UUID
    created_at: datetime

# ------------------- Settlement -------------------
class SettlementBase(BaseModel):
    settlement_type: str
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    target_custody_id: Optional[UUID] = None
    notes: Optional[str] = None

class SettlementCreate(SettlementBase):
    custody_id: UUID

class SettlementResponse(SettlementBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    custody_id: UUID
    status: str
    settled_by: UUID
    settled_at: Optional[datetime] = None
    created_at: datetime

# ------------------- Report Filters -------------------
class ReportFilter(BaseModel):
    organization_id: UUID
    project_id: Optional[UUID] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    format: str = "json"  # json, pdf, excel

class CustodyStatementFilter(ReportFilter):
    custody_id: UUID

class PartyLedgerFilter(ReportFilter):
    party_id: UUID

class ProjectSummaryFilter(ReportFilter):
    pass

# ------------------- Dashboard -------------------
class DashboardSummary(BaseModel):
    total_custodies: int
    open_custodies: int
    overdue_custodies: int
    total_expenses_today: Decimal
    total_payments_today: Decimal
    pending_approvals: int
    total_parties: int
    active_projects: int

class DashboardAlert(BaseModel):
    type: str
    severity: str
    message: str
    entity_type: str
    entity_id: UUID
    created_at: datetime

# ------------------- Pagination -------------------
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
