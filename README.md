# FFCES - Field Financial Custody & Entitlements System
## نظام إدارة العهد والمستحقات والمصروفات الميدانية

### Overview
FFCES is a specialized financial management system designed for field operations, construction companies, and humanitarian organizations. It combines:
- **Custody Management** (العهدة المالية)
- **Expense Tracking** (المصروفات)
- **Worker Entitlements** (الاستحقاقات)
- **Real-time Balance** (الرصيد اللحظي)
- **Double-Entry Ledger** (القيود المحاسبية)

### Architecture
- **Backend**: FastAPI (Python) + SQLAlchemy 2.0 + PostgreSQL 15+
- **Cache/Queue**: Redis
- **Storage**: MinIO (S3-compatible)
- **Frontend**: React + TailwindCSS + PWA

### Quick Start
```bash
# 1. Clone and setup
cd ffces_project
cp .env.example .env

# 2. Start infrastructure
docker-compose up -d db redis minio

# 3. Run migrations
psql -h localhost -U ffces_user -d ffces_db -f migrations/001_initial_schema.sql

# 4. Start API
pip install -r requirements.txt
uvicorn main:app --reload

# 5. Access
API Docs: http://localhost:8000/api/docs
Health: http://localhost:8000/health
```

### Core Entities
| Entity | Description |
|--------|-------------|
| `custodies` | Financial custody with full lifecycle tracking |
| `expenses` | Expenses linked to custody with mandatory attachments |
| `parties` | Workers, suppliers, contractors |
| `work_records` | Achievement/attendance records |
| `entitlements` | Calculated payables (daily/qty/hourly/monthly/lump_sum/mixed) |
| `payments` | Payments with advance/deduction tracking |
| `settlements` | Custody settlement workflows |
| `ledger_entries` | Immutable double-entry bookkeeping |

### Key Features
1. **Balance on-the-fly**: All balances calculated from source, never stored
2. **Immutable Ledger**: PostgreSQL trigger prevents any modification/deletion
3. **Entitlement Engine**: Supports 6 calculation types (daily, hourly, quantity, monthly, lump_sum, mixed)
4. **Offline-First**: PWA with background sync
5. **Approval Workflow**: Hierarchical approval based on amount and role
6. **Audit Trail**: Every operation logged with before/after values

### Project Structure
```
ffces_project/
├── main.py                    # FastAPI application entry
├── app/
│   ├── core/                  # Config, Database, Auth, Redis
│   ├── models/                # SQLAlchemy models (18 entities)
│   ├── schemas/               # Pydantic DTOs
│   ├── services/              # Business logic
│   │   ├── entitlement_engine.py   # Core calculation engine
│   │   ├── ledger_service.py       # Double-entry bookkeeping
│   │   ├── balance_service.py      # Real-time balance calc
│   │   ├── audit_service.py        # Audit trail
│   │   └── approval_service.py     # Workflow engine
│   └── api/v1/                # REST API routes
├── migrations/                # SQL DDL
├── docker-compose.yml
└── requirements.txt
```

### License
MIT License - 2024
