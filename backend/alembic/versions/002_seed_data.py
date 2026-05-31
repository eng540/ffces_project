"""seed data - default organization, admin user, project, chart of accounts, entitlement rules

Revision ID: 002_seed
Revises: 001_initial
Create Date: 2024-01-01 00:01:00.000000

"""
from alembic import op

revision = '002_seed'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
-- Default Organization
INSERT INTO organizations (id, name, name_en, code, address, phone, email, fiscal_year_start, fiscal_year_end, is_active)
VALUES (
    '00000000-0000-4000-8000-000000000001',
    'المؤسسة الافتراضية', 'Default Organization', 'ORG-001',
    'الرياض، المملكة العربية السعودية', '+966-11-0000000', 'info@ffces.com',
    1, 12, TRUE
) ON CONFLICT (id) DO NOTHING;

-- Default Admin User (password: Admin@123)
INSERT INTO users (id, email, full_name, hashed_password, employee_number, phone, role, department, job_title, is_active, organization_id)
VALUES (
    '00000000-0000-4000-8000-000000000002',
    'admin@ffces.com', 'مدير النظام', '$2b$12$LJ3m4ys3Nz/6KF7wGFvMbOs7T1k6aS8Z7QGr0PMJoL1ZO6nPCc1qK',
    'EMP-0001', '+966-50-0000001', 'admin', 'الإدارة', 'مدير النظام', TRUE,
    '00000000-0000-4000-8000-000000000001'
) ON CONFLICT (id) DO NOTHING;

-- Default Project
INSERT INTO projects (id, name, name_en, code, description, organization_id, total_budget, status)
VALUES (
    '00000000-0000-4000-8000-000000000003',
    'المشروع الافتراضي', 'Default Project', 'PRJ-001',
    'مشروع تجريبي للنظام', '00000000-0000-4000-8000-000000000001',
    500000.00, 'active'
) ON CONFLICT (id) DO NOTHING;

-- Chart of Accounts
INSERT INTO accounts (id, code, name, name_en, account_type, organization_id, balance) VALUES
('00000000-0000-4000-8000-000000000010', '1000', 'الأصول', 'Assets', 'asset', '00000000-0000-4000-8000-000000000001', 0),
('00000000-0000-4000-8000-000000000011', '1100', 'الأصول المتداولة', 'Current Assets', 'asset', '00000000-0000-4000-8000-000000000001', 0),
('00000000-0000-4000-8000-000000000012', '1110', 'النقدية والبنوك', 'Cash & Banks', 'asset', '00000000-0000-4000-8000-000000000001', 0),
('00000000-0000-4000-8000-000000000013', '1120', 'عهد مستلمة', 'Custodies Receivable', 'asset', '00000000-0000-4000-8000-000000000001', 0),
('00000000-0000-4000-8000-000000000014', '1130', 'مدينون آخرون', 'Other Receivables', 'asset', '00000000-0000-4000-8000-000000000001', 0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO accounts (id, code, name, name_en, account_type, organization_id, balance) VALUES
('00000000-0000-4000-8000-000000000020', '2000', 'الالتزامات', 'Liabilities', 'liability', '00000000-0000-4000-8000-000000000001', 0),
('00000000-0000-4000-8000-000000000021', '2100', 'التزامات متداولة', 'Current Liabilities', 'liability', '00000000-0000-4000-8000-000000000001', 0),
('00000000-0000-4000-8000-000000000022', '2110', 'دائنون', 'Accounts Payable', 'liability', '00000000-0000-4000-8000-000000000001', 0),
('00000000-0000-4000-8000-000000000023', '2120', 'مصروفات مقدمة', 'Prepaid Expenses', 'liability', '00000000-0000-4000-8000-000000000001', 0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO accounts (id, code, name, name_en, account_type, organization_id, balance) VALUES
('00000000-0000-4000-8000-000000000030', '3000', 'حقوق الملكية', 'Equity', 'equity', '00000000-0000-4000-8000-000000000001', 0),
('00000000-0000-4000-8000-000000000031', '3100', 'رأس المال', 'Capital', 'equity', '00000000-0000-4000-8000-000000000001', 0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO accounts (id, code, name, name_en, account_type, organization_id, balance) VALUES
('00000000-0000-4000-8000-000000000040', '4000', 'الإيرادات', 'Revenue', 'revenue', '00000000-0000-4000-8000-000000000001', 0),
('00000000-0000-4000-8000-000000000041', '4100', 'إيرادات المشروعات', 'Project Revenue', 'revenue', '00000000-0000-4000-8000-000000000001', 0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO accounts (id, code, name, name_en, account_type, organization_id, balance) VALUES
('00000000-0000-4000-8000-000000000050', '5000', 'المصروفات', 'Expenses', 'expense', '00000000-0000-4000-8000-000000000001', 0),
('00000000-0000-4000-8000-000000000051', '5100', 'مصروفات النقل', 'Transportation Expenses', 'expense', '00000000-0000-4000-8000-000000000001', 0),
('00000000-0000-4000-8000-000000000052', '5200', 'مصروفات السكن', 'Accommodation Expenses', 'expense', '00000000-0000-4000-8000-000000000001', 0),
('00000000-0000-4000-8000-000000000053', '5300', 'مصروفات الوجبات', 'Meal Expenses', 'expense', '00000000-0000-4000-8000-000000000001', 0),
('00000000-0000-4000-8000-000000000054', '5400', 'مصروفات عامة', 'General Expenses', 'expense', '00000000-0000-4000-8000-000000000001', 0)
ON CONFLICT (id) DO NOTHING;

-- Default Entitlement Rules
INSERT INTO entitlement_rules (id, name, name_en, organization_id, entitlement_type, amount, currency, unit, role, is_active, effective_date)
VALUES
('00000000-0000-4000-8000-000000000060', 'بدل نقل يومي', 'Daily Transportation', '00000000-0000-4000-8000-000000000001', 'transportation', 150.00, 'SAR', 'daily', NULL, TRUE, NOW()),
('00000000-0000-4000-8000-000000000061', 'بدل سكن يومي', 'Daily Accommodation', '00000000-0000-4000-8000-000000000001', 'housing', 300.00, 'SAR', 'daily', NULL, TRUE, NOW()),
('00000000-0000-4000-8000-000000000062', 'بدل وجبات يومي', 'Daily Meals', '00000000-0000-4000-8000-000000000001', 'meals', 100.00, 'SAR', 'daily', NULL, TRUE, NOW()),
('00000000-0000-4000-8000-000000000063', 'بدل نقل بالكيلومتر', 'Per KM Transportation', '00000000-0000-4000-8000-000000000001', 'transportation', 1.50, 'SAR', 'per_km', NULL, TRUE, NOW())
ON CONFLICT (id) DO NOTHING;
""")


def downgrade() -> None:
    op.execute("""
        DELETE FROM entitlement_rules WHERE id IN (
            '00000000-0000-4000-8000-000000000060',
            '00000000-0000-4000-8000-000000000061',
            '00000000-0000-4000-8000-000000000062',
            '00000000-0000-4000-8000-000000000063'
        );
        DELETE FROM accounts WHERE organization_id = '00000000-0000-4000-8000-000000000001';
        DELETE FROM projects WHERE id = '00000000-0000-4000-8000-000000000003';
        DELETE FROM users WHERE id = '00000000-0000-4000-8000-000000000002';
        DELETE FROM organizations WHERE id = '00000000-0000-4000-8000-000000000001';
    """)
