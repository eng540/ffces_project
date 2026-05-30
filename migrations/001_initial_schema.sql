-- ============================================================
-- FFCES - Field Financial Custody & Entitlements System
-- Complete Database Schema
-- PostgreSQL 15+ Required
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- 1. CORE TABLES
-- ============================================================

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) CHECK (type IN ('contracting', 'ngo', 'government', 'private', 'other')),
    settings JSONB DEFAULT '{}',
    default_currency VARCHAR(3) DEFAULT 'USD',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN (
        'super_admin', 'financial_manager', 'accountant', 
        'custodian', 'field_supervisor', 'auditor', 'viewer'
    )),
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT true,
    mfa_enabled BOOLEAN DEFAULT false,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_org ON users(organization_id);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_email ON users(email);

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(100) NOT NULL,
    budget_limit DECIMAL(15,2) CHECK (budget_limit >= 0),
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'cancelled')),
    manager_id UUID REFERENCES users(id),
    location JSONB,
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, code)
);

CREATE INDEX idx_projects_org ON projects(organization_id);
CREATE INDEX idx_projects_status ON projects(status);

-- ============================================================
-- 2. PARTIES (Workers, Suppliers, Contractors, Beneficiaries)
-- ============================================================

CREATE TABLE parties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (type IN (
        'worker_daily', 'worker_monthly', 'worker_hourly',
        'contractor_qty', 'contractor_lump_sum', 'supplier',
        'consultant', 'beneficiary', 'other'
    )),
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    id_number VARCHAR(50),
    bank_info JSONB DEFAULT '{}',

    -- Default rates (can be overridden by entitlement_rules)
    default_daily_rate DECIMAL(10,2),
    default_monthly_salary DECIMAL(12,2),
    default_hourly_rate DECIMAL(10,2),
    unit_prices JSONB DEFAULT '{}', -- {"meter_block": 5.00, "ton_cement": 120.00}

    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_parties_org ON parties(organization_id);
CREATE INDEX idx_parties_type ON parties(type);
CREATE INDEX idx_parties_name ON parties(full_name);

-- ============================================================
-- 3. ENTITLEMENT RULES (Calculation Rules)
-- ============================================================

CREATE TABLE entitlement_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    party_id UUID NOT NULL REFERENCES parties(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    calc_type VARCHAR(50) NOT NULL CHECK (calc_type IN (
        'daily', 'monthly', 'hourly', 'quantity', 'lump_sum', 'mixed'
    )),

    rate DECIMAL(12,4) NOT NULL,
    unit VARCHAR(50), -- meter, day, hour, piece, m2, m3, lump_sum

    -- For mixed calculations
    components JSONB DEFAULT '[]', -- [{"type": "base_salary", "amount": 300}, {"type": "transport", "amount": 50}]

    effective_from DATE NOT NULL,
    effective_to DATE,

    min_quantity DECIMAL(10,2),
    max_quantity DECIMAL(10,2),

    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_date_range CHECK (effective_to IS NULL OR effective_to > effective_from)
);

CREATE INDEX idx_rules_party ON entitlement_rules(party_id);
CREATE INDEX idx_rules_project ON entitlement_rules(project_id);
CREATE INDEX idx_rules_active ON entitlement_rules(is_active);

-- ============================================================
-- 4. CUSTODIES (Financial Custody)
-- ============================================================

CREATE TABLE custodies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    custody_number VARCHAR(100) UNIQUE NOT NULL,
    holder_id UUID NOT NULL REFERENCES users(id),
    issued_by UUID NOT NULL REFERENCES users(id),
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) DEFAULT 'USD',
    purpose TEXT NOT NULL,

    status VARCHAR(50) DEFAULT 'open' CHECK (status IN (
        'open', 'under_review', 'partially_settled', 'closed', 'overdue', 'over_spent'
    )),

    issued_at TIMESTAMPTZ DEFAULT NOW(),
    due_date DATE,
    closed_at TIMESTAMPTZ,
    closed_by UUID REFERENCES users(id),

    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_custodies_holder ON custodies(holder_id);
CREATE INDEX idx_custodies_status ON custodies(status);
CREATE INDEX idx_custodies_project ON custodies(project_id);
CREATE INDEX idx_custodies_number ON custodies(custody_number);

-- ============================================================
-- 5. EXPENSES
-- ============================================================

CREATE TABLE expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    custody_id UUID NOT NULL REFERENCES custodies(id) ON DELETE RESTRICT,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,

    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) DEFAULT 'USD',

    category VARCHAR(100) NOT NULL CHECK (category IN (
        'materials', 'transport', 'labor', 'equipment', 'services',
        'accommodation', 'food', 'fuel', 'maintenance', 'medical', 'other'
    )),

    description TEXT NOT NULL,
    expense_date DATE NOT NULL,

    beneficiary_type VARCHAR(50) CHECK (beneficiary_type IN ('party', 'anonymous')),
    party_id UUID REFERENCES parties(id) ON DELETE SET NULL,
    beneficiary_name VARCHAR(255),

    attachment_ids UUID[] DEFAULT '{}',

    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN (
        'draft', 'pending_approval', 'approved', 'rejected', 'cancelled'
    )),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,

    location JSONB,

    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_expenses_custody ON expenses(custody_id);
CREATE INDEX idx_expenses_project ON expenses(project_id);
CREATE INDEX idx_expenses_date ON expenses(expense_date);
CREATE INDEX idx_expenses_status ON expenses(status);
CREATE INDEX idx_expenses_party ON expenses(party_id);

-- ============================================================
-- 6. WORK RECORDS (Achievements/Attendance)
-- ============================================================

CREATE TABLE work_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    party_id UUID NOT NULL REFERENCES parties(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    record_date DATE NOT NULL,

    quantity DECIMAL(10,2) NOT NULL CHECK (quantity > 0),
    unit VARCHAR(50) NOT NULL,

    description TEXT,
    location JSONB,

    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    verification_method VARCHAR(50) CHECK (verification_method IN (
        'manual', 'photo', 'gps', 'supervisor', 'biometric'
    )),

    photo_ids UUID[] DEFAULT '{}',

    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN (
        'pending', 'verified', 'disputed', 'approved', 'rejected'
    )),
    rejection_reason TEXT,

    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_work_records_party ON work_records(party_id);
CREATE INDEX idx_work_records_project ON work_records(project_id);
CREATE INDEX idx_work_records_date ON work_records(record_date);
CREATE INDEX idx_work_records_status ON work_records(status);

-- ============================================================
-- 7. ENTITLEMENTS (Calculated Payables)
-- ============================================================

CREATE TABLE entitlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    party_id UUID NOT NULL REFERENCES parties(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    rule_id UUID REFERENCES entitlement_rules(id) ON DELETE SET NULL,
    work_record_id UUID REFERENCES work_records(id) ON DELETE SET NULL,

    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',

    calculation_details JSONB NOT NULL DEFAULT '{}',

    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    status VARCHAR(50) DEFAULT 'calculated' CHECK (status IN (
        'calculated', 'pending_payment', 'partially_paid', 'fully_paid', 'cancelled'
    )),

    paid_amount DECIMAL(15,2) DEFAULT 0 CHECK (paid_amount <= amount),
    remaining_amount DECIMAL(15,2) GENERATED ALWAYS AS (amount - paid_amount) STORED,

    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_entitlements_party ON entitlements(party_id);
CREATE INDEX idx_entitlements_project ON entitlements(project_id);
CREATE INDEX idx_entitlements_status ON entitlements(status);
CREATE INDEX idx_entitlements_period ON entitlements(period_start, period_end);

-- ============================================================
-- 8. PAYMENTS
-- ============================================================

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    party_id UUID NOT NULL REFERENCES parties(id) ON DELETE RESTRICT,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    custody_id UUID REFERENCES custodies(id) ON DELETE SET NULL,

    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) DEFAULT 'USD',

    payment_type VARCHAR(50) NOT NULL CHECK (payment_type IN (
        'salary', 'advance', 'entitlement_settlement', 'reimbursement',
        'bonus', 'deduction', 'final_settlement', 'other'
    )),

    payment_method VARCHAR(50) CHECK (payment_method IN (
        'cash', 'bank_transfer', 'check', 'mobile_money', 'other'
    )),

    reference_number VARCHAR(255),
    entitlement_ids UUID[] DEFAULT '{}',

    attachment_ids UUID[] DEFAULT '{}',

    paid_by UUID NOT NULL REFERENCES users(id),
    paid_at TIMESTAMPTZ NOT NULL,

    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payments_party ON payments(party_id);
CREATE INDEX idx_payments_custody ON payments(custody_id);
CREATE INDEX idx_payments_date ON payments(paid_at);
CREATE INDEX idx_payments_project ON payments(project_id);

-- ============================================================
-- 9. SETTLEMENTS
-- ============================================================

CREATE TABLE settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    custody_id UUID NOT NULL REFERENCES custodies(id) ON DELETE RESTRICT,

    settlement_type VARCHAR(50) NOT NULL CHECK (settlement_type IN (
        'cash_return', 'expense_acknowledgment', 'deduction', 'transfer'
    )),

    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',

    target_custody_id UUID REFERENCES custodies(id) ON DELETE SET NULL,

    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN (
        'pending', 'completed', 'cancelled'
    )),

    settled_by UUID NOT NULL REFERENCES users(id),
    settled_at TIMESTAMPTZ,

    notes TEXT,
    attachment_ids UUID[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_settlements_custody ON settlements(custody_id);
CREATE INDEX idx_settlements_status ON settlements(status);

-- ============================================================
-- 10. CHART OF ACCOUNTS
-- ============================================================

CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name_ar VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    type VARCHAR(50) NOT NULL CHECK (type IN (
        'asset', 'liability', 'equity', 'revenue', 'expense'
    )),
    parent_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 5),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, code)
);

CREATE INDEX idx_accounts_org ON accounts(organization_id);
CREATE INDEX idx_accounts_type ON accounts(type);
CREATE INDEX idx_accounts_code ON accounts(code);

-- ============================================================
-- 11. LEDGER ENTRIES (IMMUTABLE)
-- ============================================================

CREATE TABLE ledger_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    entry_type VARCHAR(50) NOT NULL CHECK (entry_type IN (
        'custody_issued', 'custody_returned', 'expense', 'payment',
        'entitlement', 'settlement', 'adjustment', 'opening_balance'
    )),
    reference_id UUID NOT NULL,
    reference_type VARCHAR(50) NOT NULL,

    debit_account_id UUID NOT NULL REFERENCES accounts(id),
    credit_account_id UUID NOT NULL REFERENCES accounts(id),

    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',

    entry_date DATE NOT NULL,
    description TEXT NOT NULL,

    immutable_hash VARCHAR(64) NOT NULL,
    previous_hash VARCHAR(64),

    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ledger_org ON ledger_entries(organization_id);
CREATE INDEX idx_ledger_ref ON ledger_entries(reference_id, reference_type);
CREATE INDEX idx_ledger_date ON ledger_entries(entry_date);
CREATE INDEX idx_ledger_type ON ledger_entries(entry_type);

-- Immutable trigger
CREATE OR REPLACE FUNCTION prevent_ledger_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Ledger entries are immutable and cannot be modified or deleted';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ledger_immutable_trigger
BEFORE UPDATE OR DELETE ON ledger_entries
FOR EACH ROW EXECUTE FUNCTION prevent_ledger_modification();

-- ============================================================
-- 12. AUDIT LOGS
-- ============================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL CHECK (action IN (
        'create', 'update', 'delete', 'view', 'approve', 'reject', 'cancel', 'export', 'login', 'logout'
    )),
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    organization_id UUID REFERENCES organizations(id),
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_org ON audit_logs(organization_id);

-- ============================================================
-- 13. APPROVAL WORKFLOWS
-- ============================================================

CREATE TABLE approval_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    approver_id UUID NOT NULL REFERENCES users(id),
    approval_level INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN (
        'pending', 'approved', 'rejected', 'cancelled'
    )),
    threshold_amount DECIMAL(15,2),
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_approval_entity ON approval_workflows(entity_type, entity_id);
CREATE INDEX idx_approval_approver ON approval_workflows(approver_id);
CREATE INDEX idx_approval_status ON approval_workflows(status);

-- ============================================================
-- 14. ATTACHMENTS
-- ============================================================

CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    file_size BIGINT,
    checksum VARCHAR(64),
    uploaded_by UUID NOT NULL REFERENCES users(id),
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_attachments_entity ON attachments(entity_type, entity_id);
CREATE INDEX idx_attachments_org ON attachments(organization_id);

-- ============================================================
-- 15. OFFLINE SYNC QUEUE
-- ============================================================

CREATE TABLE sync_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES users(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    operation JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN (
        'pending', 'processing', 'synced', 'failed', 'conflict'
    )),
    server_timestamp TIMESTAMPTZ,
    conflict_resolution JSONB,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sync_device ON sync_queue(device_id);
CREATE INDEX idx_sync_status ON sync_queue(status);
CREATE INDEX idx_sync_org ON sync_queue(organization_id);

-- ============================================================
-- 16. BALANCE SNAPSHOTS (Materialized for performance)
-- ============================================================

CREATE TABLE balance_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL CHECK (entity_type IN ('party', 'custody')),
    entity_id UUID NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id),

    total_in DECIMAL(15,2) DEFAULT 0,
    total_out DECIMAL(15,2) DEFAULT 0,
    total_expenses DECIMAL(15,2) DEFAULT 0,
    total_settlements DECIMAL(15,2) DEFAULT 0,
    total_entitlements DECIMAL(15,2) DEFAULT 0,
    total_payments DECIMAL(15,2) DEFAULT 0,
    total_advances DECIMAL(15,2) DEFAULT 0,
    total_deductions DECIMAL(15,2) DEFAULT 0,
    net_balance DECIMAL(15,2) DEFAULT 0,

    calculation_basis JSONB DEFAULT '{}',
    calculated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(entity_type, entity_id)
);

CREATE INDEX idx_snapshots_entity ON balance_snapshots(entity_type, entity_id);
CREATE INDEX idx_snapshots_org ON balance_snapshots(organization_id);

-- ============================================================
-- FUNCTIONS: BALANCE CALCULATIONS
-- ============================================================

CREATE OR REPLACE FUNCTION calculate_custody_balance(custody_uuid UUID)
RETURNS TABLE (
    original_amount DECIMAL,
    total_expenses DECIMAL,
    total_settlements DECIMAL,
    remaining_balance DECIMAL,
    status VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.amount,
        COALESCE(SUM(e.amount) FILTER (WHERE e.status = 'approved'), 0),
        COALESCE(SUM(s.amount) FILTER (WHERE s.status = 'completed'), 0),
        c.amount 
            - COALESCE(SUM(e.amount) FILTER (WHERE e.status = 'approved'), 0)
            - COALESCE(SUM(s.amount) FILTER (WHERE s.status = 'completed'), 0),
        CASE 
            WHEN c.amount - COALESCE(SUM(e.amount) FILTER (WHERE e.status = 'approved'), 0) 
                 - COALESCE(SUM(s.amount) FILTER (WHERE s.status = 'completed'), 0) <= 0 
                THEN 'closed_ready'
            WHEN c.due_date IS NOT NULL AND c.due_date < CURRENT_DATE 
                THEN 'overdue'
            ELSE 'open'
        END
    FROM custodies c
    LEFT JOIN expenses e ON e.custody_id = c.id
    LEFT JOIN settlements s ON s.custody_id = c.id
    WHERE c.id = custody_uuid
    GROUP BY c.id, c.amount, c.due_date;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION calculate_party_balance(
    party_uuid UUID,
    project_uuid UUID DEFAULT NULL
)
RETURNS TABLE (
    total_entitlements DECIMAL,
    total_payments DECIMAL,
    total_advances DECIMAL,
    total_deductions DECIMAL,
    net_balance DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(e.amount), 0),
        COALESCE(SUM(p.amount) FILTER (WHERE p.payment_type NOT IN ('advance', 'deduction')), 0),
        COALESCE(SUM(p.amount) FILTER (WHERE p.payment_type = 'advance'), 0),
        COALESCE(SUM(p.amount) FILTER (WHERE p.payment_type = 'deduction'), 0),
        COALESCE(SUM(e.amount), 0) 
            - COALESCE(SUM(p.amount) FILTER (WHERE p.payment_type NOT IN ('advance', 'deduction')), 0)
            - COALESCE(SUM(p.amount) FILTER (WHERE p.payment_type = 'deduction'), 0)
            + COALESCE(SUM(p.amount) FILTER (WHERE p.payment_type = 'advance'), 0)
    FROM parties pt
    LEFT JOIN entitlements e ON e.party_id = pt.id 
        AND e.status IN ('calculated', 'pending_payment', 'partially_paid')
        AND (project_uuid IS NULL OR e.project_id = project_uuid)
    LEFT JOIN payments p ON p.party_id = pt.id
        AND (project_uuid IS NULL OR p.project_id = project_uuid)
    WHERE pt.id = party_uuid
    GROUP BY pt.id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TRIGGER: Auto-generate custody number
-- ============================================================

CREATE OR REPLACE FUNCTION generate_custody_number()
RETURNS TRIGGER AS $$
DECLARE
    year_part TEXT;
    seq_num INTEGER;
    new_number TEXT;
BEGIN
    year_part := TO_CHAR(NEW.issued_at, 'YYYY');

    SELECT COALESCE(MAX(CAST(SUBSTRING(custody_number FROM 'CUST-[0-9]{4}-([0-9]+)$') AS INTEGER)), 0) + 1
    INTO seq_num
    FROM custodies
    WHERE custody_number LIKE 'CUST-' || year_part || '-%';

    new_number := 'CUST-' || year_part || '-' || LPAD(seq_num::TEXT, 6, '0');
    NEW.custody_number := new_number;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER custody_number_trigger
BEFORE INSERT ON custodies
FOR EACH ROW
WHEN (NEW.custody_number IS NULL)
EXECUTE FUNCTION generate_custody_number();

-- ============================================================
-- TRIGGER: Update timestamps
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_timestamp BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orgs_timestamp BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_projects_timestamp BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_parties_timestamp BEFORE UPDATE ON parties FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_rules_timestamp BEFORE UPDATE ON entitlement_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_custodies_timestamp BEFORE UPDATE ON custodies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_expenses_timestamp BEFORE UPDATE ON expenses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_work_records_timestamp BEFORE UPDATE ON work_records FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_entitlements_timestamp BEFORE UPDATE ON entitlements FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_payments_timestamp BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_settlements_timestamp BEFORE UPDATE ON settlements FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_accounts_timestamp BEFORE UPDATE ON accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sync_queue_timestamp BEFORE UPDATE ON sync_queue FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- DEFAULT ACCOUNTS SEED (for each organization)
-- ============================================================

CREATE OR REPLACE FUNCTION seed_organization_accounts(org_id UUID)
RETURNS VOID AS $$
BEGIN
    INSERT INTO accounts (organization_id, code, name_ar, name_en, type, level, is_active) VALUES
    (org_id, '1100', 'الصندوق', 'Cash on Hand', 'asset', 1, true),
    (org_id, '1200', 'عهدة قيد التحصيل', 'Custodies Outstanding', 'asset', 1, true),
    (org_id, '1300', 'ذمم مدينة', 'Accounts Receivable', 'asset', 1, true),
    (org_id, '2100', 'ذمم دائنة', 'Accounts Payable', 'liability', 1, true),
    (org_id, '2200', 'مستحقات العمال', 'Workers Entitlements', 'liability', 1, true),
    (org_id, '2300', 'عهدة مستلمة', 'Custody Received', 'liability', 1, true),
    (org_id, '3100', 'رأس المال', 'Capital', 'equity', 1, true),
    (org_id, '5100', 'مصروفات مواد', 'Materials Expense', 'expense', 1, true),
    (org_id, '5200', 'مصروفات عمال', 'Labor Expense', 'expense', 1, true),
    (org_id, '5300', 'مصروفات نقل', 'Transport Expense', 'expense', 1, true),
    (org_id, '5400', 'مصروفات معدات', 'Equipment Expense', 'expense', 1, true),
    (org_id, '5500', 'مصروفات خدمات', 'Services Expense', 'expense', 1, true),
    (org_id, '6100', 'إيرادات المشاريع', 'Project Revenue', 'revenue', 1, true);
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- VIEWS FOR REPORTING
-- ============================================================

CREATE VIEW custody_summary AS
SELECT 
    c.id,
    c.custody_number,
    c.holder_id,
    u.full_name as holder_name,
    c.project_id,
    p.name as project_name,
    c.amount as original_amount,
    c.currency,
    c.status,
    c.issued_at,
    c.due_date,
    c.closed_at,
    COALESCE(e.total_expenses, 0) as total_expenses,
    COALESCE(s.total_settlements, 0) as total_settlements,
    c.amount - COALESCE(e.total_expenses, 0) - COALESCE(s.total_settlements, 0) as remaining_balance
FROM custodies c
LEFT JOIN users u ON u.id = c.holder_id
LEFT JOIN projects p ON p.id = c.project_id
LEFT JOIN (
    SELECT custody_id, SUM(amount) as total_expenses 
    FROM expenses 
    WHERE status = 'approved' 
    GROUP BY custody_id
) e ON e.custody_id = c.id
LEFT JOIN (
    SELECT custody_id, SUM(amount) as total_settlements 
    FROM settlements 
    WHERE status = 'completed' 
    GROUP BY custody_id
) s ON s.custody_id = c.id;

CREATE VIEW party_statement AS
SELECT 
    p.id as party_id,
    p.full_name,
    p.type,
    p.organization_id,
    COALESCE(e.total_entitlements, 0) as total_entitlements,
    COALESCE(py.total_payments, 0) as total_payments,
    COALESCE(py.total_advances, 0) as total_advances,
    COALESCE(py.total_deductions, 0) as total_deductions,
    COALESCE(e.total_entitlements, 0) 
        - COALESCE(py.total_payments, 0) 
        - COALESCE(py.total_deductions, 0) 
        + COALESCE(py.total_advances, 0) as net_balance
FROM parties p
LEFT JOIN (
    SELECT party_id, SUM(amount) as total_entitlements
    FROM entitlements
    WHERE status IN ('calculated', 'pending_payment', 'partially_paid')
    GROUP BY party_id
) e ON e.party_id = p.id
LEFT JOIN (
    SELECT 
        party_id,
        SUM(amount) FILTER (WHERE payment_type NOT IN ('advance', 'deduction')) as total_payments,
        SUM(amount) FILTER (WHERE payment_type = 'advance') as total_advances,
        SUM(amount) FILTER (WHERE payment_type = 'deduction') as total_deductions
    FROM payments
    GROUP BY party_id
) py ON py.party_id = p.id;

-- ============================================================
-- END OF SCHEMA
-- ============================================================
