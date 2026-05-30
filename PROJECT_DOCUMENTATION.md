# FFCES - نظام إدارة العهد والمستحقات الميدانية
## Field Financial Custody & Entitlements System

---

## الملخص التنفيذي

نظام مالي ميداني متكامل تم بناؤه بالكامل لحل مشكلة حقيقية في:
- شركات المقاولات الصغيرة والمتوسطة
- المنظمات الإنسانية الميدانية
- المؤسسات التشغيلية الميدانية

**الفجوة التي يملأها**: الجمع بين العهد + المصروفات + الاستحقاقات + العمالة + كشف الحساب الحي في نظام بسيط وسريع وميداني.

---

## الهيكل المعماري

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                              │
│  Mobile PWA  │  React Dashboard  │  WhatsApp Bot  │  OCR     │
├─────────────────────────────────────────────────────────────┤
│                    API GATEWAY                               │
│  Kong/Nginx  │  JWT+RBAC+MFA  │  Rate Limiter  │  Offline  │
├─────────────────────────────────────────────────────────────┤
│                  CORE SERVICES (FastAPI)                     │
│  Custody  │  Expense  │  Entitlement  │  Payment  │  Worker │
├─────────────────────────────────────────────────────────────┤
│              EVENT BUS & LEDGER ENGINE                       │
│  Redis Streams  │  Double-Entry Ledger  │  Audit Log      │
├─────────────────────────────────────────────────────────────┤
│                    DATA LAYER                                │
│  PostgreSQL  │  Redis Cache  │  MinIO/S3  │  Elasticsearch  │
├─────────────────────────────────────────────────────────────┤
│                 INFRASTRUCTURE                               │
│  Docker  │  K8s  │  CI/CD  │  Monitoring  │  Backup & DR  │
└─────────────────────────────────────────────────────────────┘
```

---

## الكيانات الرئيسية (18 Entity)

| الكيان | الوصف | السجلات |
|--------|-------|---------|
| `organizations` | الجهات/الشركات | Multi-tenant |
| `users` | المستخدمون مع RBAC | 7 أدوار |
| `projects` | المشاريع مع الميزانية | تتبع تكلفة |
| `parties` | الأطراف (عمال/موردين/مقاولين) | 9 أنواع |
| `entitlement_rules` | قواعد الحساب | 6 أنواع حساب |
| `custodies` | العهدة المالية | دورة حياة كاملة |
| `expenses` | المصروفات | مع إثباتات إلزامية |
| `work_records` | سجلات الإنجاز | GPS + صور |
| `entitlements` | الاستحقاقات المحسوبة | شفافية تامة |
| `payments` | الدفعات | سلف/خصميات |
| `settlements` | تسويات العهدة | 4 أنواع |
| `accounts` | شجرة الحسابات | 5 مستويات |
| `ledger_entries` | القيود المحاسبية | **غير قابلة للتعديل** |
| `audit_logs` | سجل التدقيق | كل عملية |
| `approval_workflows` | سير الموافقات | هرمي حسب المبلغ |
| `attachments` | المرفقات | S3-compatible |
| `sync_queue` | مزامنة Offline | FIFO |
| `balance_snapshots` | لقطات الرصيد | Materialized |

---

## محرك الحساب (Entitlement Engine)

### أنواع الحساب المدعومة

| النوع | الوصف | المعادلة | مثال |
|-------|-------|----------|------|
| **daily** | يومي | أيام × أجر يومي | 15 يوم × 10$ = 150$ |
| **quantity** | بالكمية | كمية × سعر الوحدة | 50 متر × 4$ = 200$ |
| **hourly** | بالساعة | ساعات × سعر الساعة | 40 ساعة × 5$ = 200$ |
| **monthly** | شهري | أشهر × الراتب | 1 شهر × 300$ = 300$ |
| **lump_sum** | مقطوعي | مبلغ ثابت | حمام كامل = 500$ |
| **mixed** | مختلط | راتب + بدلات - خصميات | 300 + 50 - 20 = 330$ |

### شفافية الحساب

كل استحقاق يحمل `calculation_details` JSONB:
```json
{
  "version": "1.0",
  "calc_type": "quantity",
  "total_quantity": 50.0,
  "unit": "meter",
  "rate": 4.00,
  "formula": "50.0 × 4.00",
  "work_record_ids": ["uuid-1", "uuid-2"],
  "period": "2024-01-01 to 2024-01-15"
}
```

---

## القيود المحاسبية (Immutable Ledger)

### حماية PostgreSQL

```sql
-- لا يمكن تعديل أو حذف أي قيد
CREATE TRIGGER ledger_immutable_trigger
BEFORE UPDATE OR DELETE ON ledger_entries
FOR EACH ROW EXECUTE FUNCTION prevent_ledger_modification();
```

### أمثلة القيود

| العملية | مدين | دائن | المبلغ |
|---------|------|------|--------|
| تسليم عهدة | عهدة قيد التحصيل (1200) | الصندوق (1100) | 5000$ |
| مصروف مواد | مصروفات مواد (5100) | عهدة المندوب (1200) | 1200$ |
| استحقاق عامل | مصروفات عمال (5200) | مستحقات العمال (2200) | 200$ |
| دفعة للعامل | مستحقات العمال (2200) | الصندوق (1100) | 150$ |
| إعادة عهدة | الصندوق (1100) | عهدة قيد التحصيل (1200) | 1000$ |

---

## نظام الموافقات (Approval Workflow)

### قواعد الموافقة

| الكيان | المبلغ | الموافق |
|--------|--------|---------|
| مصروف | < 100$ | مشرف ميداني |
| مصروف | < 500$ | محاسب |
| مصروف | < 1000$ | مدير مالي |
| مصروف | > 1000$ | مدير مالي + CEO |
| عهدة | < 500$ | محاسب |
| عهدة | < 2000$ | مدير مالي |
| عهدة | > 2000$ | مدير مالي + CEO |

---

## API Endpoints

### Custodies
```
POST   /api/v1/custodies              → إنشاء عهدة
GET    /api/v1/custodies/{id}         → تفاصيل + رصيد حي
GET    /api/v1/custodies/{id}/balance → رصيد فقط
POST   /api/v1/custodies/{id}/settle  → إخلاء العهدة
GET    /api/v1/custodies?status=open  → فلترة
```

### Expenses
```
POST   /api/v1/expenses               → تسجيل مصروف
GET    /api/v1/expenses/{id}          → تفاصيل
PATCH  /api/v1/expenses/{id}/approve  → موافقة/رفض
GET    /api/v1/expenses?custody_id=.. → فلترة
```

### Work Records
```
POST   /api/v1/work-records           → تسجيل إنجاز
POST   /api/v1/work-records/bulk      → تسجيل مجموعة
PATCH  /api/v1/work-records/{id}/verify → تحقق
```

### Entitlements
```
POST   /api/v1/entitlements/calculate  → حساب استحقاقات
GET    /api/v1/entitlements?party_id=.. → قائمة
```

### Parties
```
POST   /api/v1/parties                → إضافة طرف
GET    /api/v1/parties/{id}/balance   → رصيد حي
GET    /api/v1/parties/{id}/statement → كشف حساب
```

### Reports
```
GET    /api/v1/reports/custody-statement?custody_id=..
GET    /api/v1/reports/party-ledger?party_id=..
GET    /api/v1/reports/project-summary?project_id=..
GET    /api/v1/reports/open-custodies
```

### Dashboard
```
GET    /api/v1/dashboard/summary      → إحصائيات سريعة
GET    /api/v1/dashboard/alerts       → تنبيهات
```

---

## خطة التنفيذ (MVP - 10 أسابيع)

| الأسبوع | المحتوى |
|---------|---------|
| 1-2 | Foundation: Docker, Auth, Schema |
| 3-4 | Core: Custody, Expense, Party CRUD |
| 5-6 | Engine: Work Records, Entitlements, Payments |
| 7-8 | Ledger, Reports, Dashboard |
| 9-10 | Offline Sync, Polish, Testing |

---

## التقنيات المستخدمة

| الطبقة | التقنية |
|--------|---------|
| Backend | FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| Database | PostgreSQL 15+ (ACID, JSONB, Window Functions) |
| Cache/Queue | Redis (Streams, Pub/Sub, Sorted Sets) |
| Storage | MinIO (S3-compatible) |
| Auth | JWT + RBAC + MFA-ready |
| Container | Docker + Docker Compose |
| Testing | pytest + pytest-asyncio |

---

## الملفات المتاحة للتحميل

| الملف | الوصف |
|-------|-------|
| [مخطط الهيكل المعماري](sandbox:///mnt/agents/output/system_architecture.png) | 7 طبقات معمارية |
| [مخطط نموذج البيانات](sandbox:///mnt/agents/output/erd_diagram.png) | 18 كيان مع العلاقات |
| [مخطط سير العمليات](sandbox:///mnt/agents/output/workflows_diagram.png) | 3 سيناريوهات |
| [تحليل السوق](sandbox:///mnt/agents/output/market_analysis.png) | دراسة السوق |
| [التوثيق المعماري](sandbox:///mnt/agents/output/ffces_architecture_documentation.md) | التوثيق الكامل |
| **كود المشروع** | **31 ملف** |

---

## إحصائيات المشروع

| المقياس | القيمة |
|---------|--------|
| إجمالي الملفات | 31 |
| إجمالي الأسطر | ~3,500 |
| الكيانات | 18 |
| خدمات الأعمال | 6 |
| نقاط API | 40+ |
| أنواع الحساب | 6 |
| أنواع التسوية | 4 |
| أدوار المستخدمين | 7 |

---

**النظام جاهز للتنفيذ والتشغيل.**
