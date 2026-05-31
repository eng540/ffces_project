"""initial schema - 16 tables with UUID PKs, constraints, and indexes

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable PostgreSQL extensions (one per execute — asyncpg requirement)
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── Table 1: organizations ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS organizations (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(255) NOT NULL,
        name_en VARCHAR(255),
        code VARCHAR(50) UNIQUE NOT NULL,
        address TEXT,
        phone VARCHAR(50),
        email VARCHAR(255),
        logo_url VARCHAR(500),
        fiscal_year_start INTEGER CHECK (fiscal_year_start BETWEEN 1 AND 12),
        fiscal_year_end INTEGER CHECK (fiscal_year_end BETWEEN 1 AND 12),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE
    )
    """)

    # ── Table 2: users ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        email VARCHAR(255) UNIQUE NOT NULL,
        full_name VARCHAR(255) NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        employee_number VARCHAR(50) UNIQUE,
        phone VARCHAR(50),
        role VARCHAR(50) NOT NULL DEFAULT 'employee',
        department VARCHAR(100),
        job_title VARCHAR(200),
        is_active BOOLEAN DEFAULT TRUE,
        organization_id UUID NOT NULL REFERENCES organizations(id),
        last_login TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        CONSTRAINT chk_user_role CHECK (role IN ('admin', 'accountant', 'manager', 'employee'))
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_org ON users(organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")

    # ── Table 3: projects ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(255) NOT NULL,
        name_en VARCHAR(255),
        code VARCHAR(50) UNIQUE NOT NULL,
        description TEXT,
        organization_id UUID NOT NULL REFERENCES organizations(id),
        start_date TIMESTAMP WITH TIME ZONE,
        end_date TIMESTAMP WITH TIME ZONE,
        total_budget DECIMAL(15,2) DEFAULT 0 CHECK (total_budget >= 0),
        spent_amount DECIMAL(15,2) DEFAULT 0 CHECK (spent_amount >= 0),
        status VARCHAR(50) DEFAULT 'active',
        manager_id UUID REFERENCES users(id),
        location VARCHAR(500),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        CONSTRAINT chk_project_status CHECK (status IN ('active', 'completed', 'paused', 'cancelled'))
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_projects_org ON projects(organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")

    # ── Table 4: parties ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS parties (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(255) NOT NULL,
        name_en VARCHAR(255),
        type VARCHAR(50) NOT NULL,
        code VARCHAR(50) UNIQUE NOT NULL,
        national_id VARCHAR(50),
        phone VARCHAR(50),
        email VARCHAR(255),
        address TEXT,
        bank_name VARCHAR(255),
        bank_account VARCHAR(100),
        iban VARCHAR(50),
        organization_id UUID NOT NULL REFERENCES organizations(id),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        CONSTRAINT chk_party_type CHECK (type IN ('employee', 'vendor', 'contractor', 'client', 'other'))
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_parties_org ON parties(organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_parties_type ON parties(type)")

    # ── Table 5: entitlement_rules ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS entitlement_rules (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(255) NOT NULL,
        name_en VARCHAR(255),
        description TEXT,
        organization_id UUID NOT NULL REFERENCES organizations(id),
        project_id UUID REFERENCES projects(id),
        role VARCHAR(50),
        entitlement_type VARCHAR(50) NOT NULL,
        amount DECIMAL(15,2) NOT NULL DEFAULT 0 CHECK (amount >= 0),
        currency VARCHAR(10) DEFAULT 'SAR',
        unit VARCHAR(50),
        conditions TEXT,
        max_amount DECIMAL(15,2),
        is_active BOOLEAN DEFAULT TRUE,
        effective_date TIMESTAMP WITH TIME ZONE,
        expiry_date TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_ent_rules_org ON entitlement_rules(organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ent_rules_type ON entitlement_rules(entitlement_type)")

    # ── Table 6: custodies ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS custodies (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        holder_id UUID NOT NULL REFERENCES users(id),
        custodian_id UUID NOT NULL REFERENCES users(id),
        project_id UUID REFERENCES projects(id),
        amount DECIMAL(15,2) NOT NULL DEFAULT 0 CHECK (amount >= 0),
        currency VARCHAR(10) DEFAULT 'SAR',
        purpose TEXT NOT NULL,
        custody_type VARCHAR(50) DEFAULT 'general',
        status VARCHAR(50) DEFAULT 'active',
        issued_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        due_date TIMESTAMP WITH TIME ZONE,
        settled_amount DECIMAL(15,2) DEFAULT 0,
        remaining_amount DECIMAL(15,2) DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        CONSTRAINT ck_custody_amount_positive CHECK (amount >= 0),
        CONSTRAINT ck_custody_settled_range CHECK (settled_amount >= 0 AND settled_amount <= amount),
        CONSTRAINT ck_custody_status CHECK (status IN ('active', 'partially_settled', 'settled', 'overdue')),
        CONSTRAINT ck_custody_type CHECK (custody_type IN ('general', 'project', 'travel', 'emergency'))
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_custody_holder ON custodies(holder_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_custody_custodian ON custodies(custodian_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_custody_project ON custodies(project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_custody_status ON custodies(status)")

    # ── Table 7: expenses ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        custody_id UUID NOT NULL REFERENCES custodies(id),
        created_by UUID NOT NULL REFERENCES users(id),
        amount DECIMAL(15,2) NOT NULL DEFAULT 0 CHECK (amount >= 0),
        currency VARCHAR(10) DEFAULT 'SAR',
        category VARCHAR(100) NOT NULL,
        description TEXT NOT NULL,
        expense_date TIMESTAMP WITH TIME ZONE NOT NULL,
        receipt_number VARCHAR(100),
        vendor VARCHAR(255),
        status VARCHAR(50) DEFAULT 'pending',
        approved_by UUID REFERENCES users(id),
        approved_at TIMESTAMP WITH TIME ZONE,
        rejection_reason TEXT,
        verified_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        CONSTRAINT ck_expense_status CHECK (status IN ('pending', 'approved', 'rejected', 'verified'))
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_expense_custody_id ON expenses(custody_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_expense_category ON expenses(category)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_expense_status ON expenses(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_expense_date ON expenses(expense_date)")

    # ── Table 8: work_records ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS work_records (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id),
        project_id UUID NOT NULL REFERENCES projects(id),
        "date" TIMESTAMP WITH TIME ZONE NOT NULL,
        start_time TIMESTAMP WITH TIME ZONE,
        end_time TIMESTAMP WITH TIME ZONE,
        hours_worked FLOAT DEFAULT 0 CHECK (hours_worked >= 0),
        location VARCHAR(500),
        description TEXT,
        status VARCHAR(50) DEFAULT 'draft',
        approved_by UUID REFERENCES users(id),
        approved_at TIMESTAMP WITH TIME ZONE,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        CONSTRAINT ck_wr_status CHECK (status IN ('draft', 'submitted', 'approved', 'rejected'))
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_wr_user ON work_records(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_wr_project ON work_records(project_id)")
    op.execute('CREATE INDEX IF NOT EXISTS idx_wr_date ON work_records("date")')

    # ── Table 9: entitlements ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS entitlements (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id),
        project_id UUID NOT NULL REFERENCES projects(id),
        rule_id UUID NOT NULL REFERENCES entitlement_rules(id),
        work_record_id UUID REFERENCES work_records(id),
        amount DECIMAL(15,2) NOT NULL DEFAULT 0 CHECK (amount >= 0),
        currency VARCHAR(10) DEFAULT 'SAR',
        status VARCHAR(50) DEFAULT 'calculated',
        period_start TIMESTAMP WITH TIME ZONE NOT NULL,
        period_end TIMESTAMP WITH TIME ZONE NOT NULL,
        calculation_basis TEXT,
        approved_by UUID REFERENCES users(id),
        approved_at TIMESTAMP WITH TIME ZONE,
        paid_at TIMESTAMP WITH TIME ZONE,
        payment_id UUID,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        CONSTRAINT ck_ent_status CHECK (status IN ('calculated', 'approved', 'paid', 'rejected'))
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_ent_user ON entitlements(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ent_project ON entitlements(project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ent_status ON entitlements(status)")

    # ── Table 10: payments ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        payee_id UUID REFERENCES parties(id),
        payer_id UUID REFERENCES parties(id),
        amount DECIMAL(15,2) NOT NULL DEFAULT 0 CHECK (amount >= 0),
        currency VARCHAR(10) DEFAULT 'SAR',
        payment_method VARCHAR(50) NOT NULL,
        payment_date TIMESTAMP WITH TIME ZONE NOT NULL,
        reference_number VARCHAR(100),
        description TEXT,
        status VARCHAR(50) DEFAULT 'pending',
        bank_name VARCHAR(255),
        bank_account VARCHAR(100),
        created_by UUID REFERENCES users(id),
        approved_by UUID REFERENCES users(id),
        approved_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE,
        organization_id UUID NOT NULL REFERENCES organizations(id),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        CONSTRAINT ck_payment_status CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
        CONSTRAINT ck_payment_method CHECK (payment_method IN ('bank_transfer', 'cash', 'check', 'wire'))
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_payment_status ON payments(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_payment_date ON payments(payment_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_payment_org ON payments(organization_id)")

    # ── Table 11: settlements ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS settlements (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        custody_id UUID NOT NULL REFERENCES custodies(id),
        user_id UUID NOT NULL REFERENCES users(id),
        amount DECIMAL(15,2) NOT NULL DEFAULT 0 CHECK (amount >= 0),
        currency VARCHAR(10) DEFAULT 'SAR',
        settlement_date TIMESTAMP WITH TIME ZONE NOT NULL,
        description TEXT,
        status VARCHAR(50) DEFAULT 'pending',
        approved_by UUID REFERENCES users(id),
        approved_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE,
        refund_amount DECIMAL(15,2) DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        CONSTRAINT ck_settlement_status CHECK (status IN ('pending', 'approved', 'rejected', 'completed'))
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_settlement_custody ON settlements(custody_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_settlement_status ON settlements(status)")

    # ── Table 12: accounts ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        code VARCHAR(50) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        name_en VARCHAR(255),
        account_type VARCHAR(50) NOT NULL,
        parent_id UUID REFERENCES accounts(id),
        organization_id UUID NOT NULL REFERENCES organizations(id),
        description TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        balance DECIMAL(15,2) DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        CONSTRAINT ck_account_type CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense'))
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_account_code ON accounts(code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_account_type ON accounts(account_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_account_org ON accounts(organization_id)")

    # ── Table 13: ledger_entries ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS ledger_entries (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        entry_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        debit_account_id UUID NOT NULL REFERENCES accounts(id),
        credit_account_id UUID NOT NULL REFERENCES accounts(id),
        amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
        currency VARCHAR(10) DEFAULT 'SAR',
        description TEXT NOT NULL,
        reference_type VARCHAR(100),
        reference_id UUID,
        created_by UUID NOT NULL REFERENCES users(id),
        organization_id UUID NOT NULL REFERENCES organizations(id),
        journal_number VARCHAR(100),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        CONSTRAINT ck_ledger_accounts CHECK (debit_account_id != credit_account_id)
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_ledger_reference ON ledger_entries(reference_type, reference_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ledger_date ON ledger_entries(entry_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ledger_debit ON ledger_entries(debit_account_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ledger_credit ON ledger_entries(credit_account_id)")

    # ── Table 14: audit_logs ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID REFERENCES users(id),
        action VARCHAR(100) NOT NULL,
        entity_type VARCHAR(100) NOT NULL,
        entity_id UUID NOT NULL,
        old_values TEXT,
        new_values TEXT,
        ip_address VARCHAR(50),
        user_agent VARCHAR(500),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_logs(entity_type, entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_user ON audit_logs(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_date ON audit_logs(created_at)")

    # ── Table 15: attachments ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS attachments (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        file_name VARCHAR(255) NOT NULL,
        file_path VARCHAR(500) NOT NULL,
        file_size INTEGER,
        file_type VARCHAR(100),
        mime_type VARCHAR(100),
        entity_type VARCHAR(100) NOT NULL,
        entity_id UUID NOT NULL,
        uploaded_by UUID NOT NULL REFERENCES users(id),
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_attachment_entity ON attachments(entity_type, entity_id)")

    # ── Table 16: approval_workflows ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS approval_workflows (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        entity_type VARCHAR(50) NOT NULL,
        entity_id UUID NOT NULL,
        approver_id UUID NOT NULL REFERENCES users(id),
        approval_level INTEGER NOT NULL DEFAULT 1 CHECK (approval_level >= 1),
        status VARCHAR(50) DEFAULT 'pending',
        threshold_amount DECIMAL(15,2),
        approved_at TIMESTAMP WITH TIME ZONE,
        rejected_at TIMESTAMP WITH TIME ZONE,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        CONSTRAINT ck_approval_status CHECK (status IN ('pending', 'approved', 'rejected', 'skipped'))
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_entity ON approval_workflows(entity_type, entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_approver ON approval_workflows(approver_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_status ON approval_workflows(status)")


def downgrade() -> None:
    # Drop tables in reverse dependency order (one per execute — asyncpg requirement)
    op.execute("DROP TABLE IF EXISTS approval_workflows")
    op.execute("DROP TABLE IF EXISTS attachments")
    op.execute("DROP TABLE IF EXISTS audit_logs")
    op.execute("DROP TABLE IF EXISTS ledger_entries")
    op.execute("DROP TABLE IF EXISTS accounts")
    op.execute("DROP TABLE IF EXISTS settlements")
    op.execute("DROP TABLE IF EXISTS payments")
    op.execute("DROP TABLE IF EXISTS entitlements")
    op.execute("DROP TABLE IF EXISTS work_records")
    op.execute("DROP TABLE IF EXISTS expenses")
    op.execute("DROP TABLE IF EXISTS custodies")
    op.execute("DROP TABLE IF EXISTS entitlement_rules")
    op.execute("DROP TABLE IF EXISTS parties")
    op.execute("DROP TABLE IF EXISTS projects")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS organizations")
