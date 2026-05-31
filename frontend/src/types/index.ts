// ============================================
// FFCES Type Definitions
// ============================================

// --- Auth ---
export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
}

export type UserRole = "admin" | "accountant" | "field_officer" | "manager";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface TokenPayload {
  sub: string;
  email: string;
  role: UserRole;
  exp: number;
}

// --- Custody ---
export type CustodyStatus = "open" | "closed" | "overdue" | "partially_settled" | "under_review";

export interface Custody {
  id: string;
  amount: number;
  remaining_amount: number;
  status: CustodyStatus;
  description: string;
  holder_id: string;
  holder_name: string;
  project_id: string;
  project_name: string;
  issued_date: string;
  due_date: string | null;
  settled_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateCustodyRequest {
  amount: number;
  holder_id: string;
  project_id: string;
  description: string;
  due_date?: string;
}

// --- Expense ---
export type ExpenseStatus = "pending" | "approved" | "rejected";

export interface Expense {
  id: string;
  amount: number;
  description: string;
  category: string;
  receipt_number: string | null;
  expense_date: string;
  status: ExpenseStatus;
  custody_id: string;
  custody_description: string;
  project_id: string;
  project_name: string;
  created_by: string;
  created_by_name: string;
  approved_by: string | null;
  approved_by_name: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateExpenseRequest {
  amount: number;
  description: string;
  category: string;
  receipt_number?: string;
  expense_date: string;
  custody_id: string;
}

// --- Party ---
export type PartyType = "worker" | "supplier" | "contractor";

export interface Party {
  id: string;
  name: string;
  type: PartyType;
  phone: string | null;
  email: string | null;
  address: string | null;
  national_id: string | null;
  notes: string | null;
  total_paid: number;
  total_entitlement: number;
  balance: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreatePartyRequest {
  name: string;
  type: PartyType;
  phone?: string;
  email?: string;
  address?: string;
  national_id?: string;
  notes?: string;
}

// --- Payment ---
export type PaymentType = "advance" | "salary" | "invoice" | "settlement" | "reimbursement";

export interface Payment {
  id: string;
  amount: number;
  payment_type: PaymentType;
  description: string;
  reference_number: string | null;
  payment_date: string;
  party_id: string;
  party_name: string;
  project_id: string;
  project_name: string;
  custody_id: string | null;
  custody_description: string | null;
  created_by: string;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface CreatePaymentRequest {
  amount: number;
  payment_type: PaymentType;
  description: string;
  reference_number?: string;
  payment_date: string;
  party_id: string;
  project_id: string;
  custody_id?: string;
}

// --- Settlement ---
export type SettlementStatus = "pending" | "approved" | "rejected";

export interface Settlement {
  id: string;
  custody_id: string;
  custody_description: string;
  total_expenses: number;
  total_refund: number;
  net_amount: number;
  status: SettlementStatus;
  settlement_date: string;
  notes: string | null;
  created_by: string;
  created_by_name: string;
  approved_by: string | null;
  approved_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateSettlementRequest {
  custody_id: string;
  total_refund: number;
  notes?: string;
}

// --- Work Record ---
export type WorkRecordStatus = "pending" | "verified" | "rejected";

export interface WorkRecord {
  id: string;
  party_id: string;
  party_name: string;
  project_id: string;
  project_name: string;
  work_date: string;
  hours_worked: number;
  rate_per_hour: number;
  total_amount: number;
  description: string | null;
  status: WorkRecordStatus;
  verified_by: string | null;
  verified_by_name: string | null;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateWorkRecordRequest {
  party_id: string;
  project_id: string;
  work_date: string;
  hours_worked: number;
  rate_per_hour: number;
  description?: string;
}

export interface BulkWorkRecordRequest {
  records: Omit<CreateWorkRecordRequest, "project_id">[];
  project_id: string;
}

// --- Entitlement ---
export type EntitlementStatus = "pending" | "calculated" | "paid" | "cancelled";

export interface Entitlement {
  id: string;
  party_id: string;
  party_name: string;
  project_id: string;
  project_name: string;
  period_start: string;
  period_end: string;
  total_work_hours: number;
  total_deductions: number;
  total_additions: number;
  net_amount: number;
  status: EntitlementStatus;
  notes: string | null;
  calculated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateEntitlementRequest {
  party_id: string;
  project_id: string;
  period_start: string;
  period_end: string;
  deductions?: number;
  additions?: number;
  notes?: string;
}

// --- Project ---
export interface Project {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
}

// --- Dashboard ---
export interface DashboardStats {
  total_custodies: number;
  open_custodies: number;
  overdue_custodies: number;
  todays_expenses: number;
  todays_payments: number;
  pending_approvals: number;
  total_parties: number;
  active_projects: number;
}

export interface OverdueCustodyAlert {
  custody_id: string;
  description: string;
  holder_name: string;
  amount: number;
  remaining_amount: number;
  due_date: string;
  days_overdue: number;
}

// --- Reports ---
export interface CustodyStatement {
  custody: Custody;
  expenses: Expense[];
  payments: Payment[];
  settlements: Settlement[];
}

export interface PartyLedger {
  party: Party;
  payments: Payment[];
  entitlements: Entitlement[];
}

export interface ProjectSummary {
  project: Project;
  total_custody_amount: number;
  total_expenses: number;
  total_payments: number;
  custodies: Custody[];
}

// --- Paginated Response ---
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// --- Select Option ---
export interface SelectOption {
  value: string;
  label: string;
}
