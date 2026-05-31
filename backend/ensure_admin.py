"""Ensure the default admin user exists with the correct password.

Runs after Alembic migrations to handle cases where:
- The seed migration was already applied with an outdated/incorrect password hash
- ON CONFLICT DO NOTHING prevented the hash from being updated
- A fresh database needs the admin user created
"""
import asyncio
import bcrypt
import os
import sys

# Default admin credentials
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@ffces.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@123")
ADMIN_NAME = "مدير النظام"
ADMIN_ROLE = "admin"
ORG_ID = "00000000-0000-4000-8000-000000000001"
ADMIN_ID = "00000000-0000-4000-8000-000000000002"


async def ensure_admin():
    # Build a synchronous URL for psycopg2 (alembic-style)
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("  WARNING: DATABASE_URL not set, skipping admin setup", file=sys.stderr)
        return

    # Convert async URL to sync for psycopg2
    sync_url = db_url.replace("+asyncpg", "").replace("+psycopg", "")

    try:
        import psycopg2

        conn = psycopg2.connect(sync_url)
        conn.autocommit = True
        cur = conn.cursor()

        # Hash the password with bcrypt
        password_bytes = ADMIN_PASSWORD.encode("utf-8")
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")

        # Check if organization exists
        cur.execute("SELECT id FROM organizations WHERE id = %s", (ORG_ID,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO organizations (id, name, name_en, code, is_active, fiscal_year_start, fiscal_year_end)
                VALUES (%s, %s, %s, %s, TRUE, 1, 12)
                ON CONFLICT (id) DO NOTHING
            """, (ORG_ID, ADMIN_NAME, "Default", "ORG-001"))

        # Upsert admin user (create or update password)
        cur.execute("""
            INSERT INTO users (id, email, full_name, hashed_password, employee_number, role, is_active, organization_id)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s)
            ON CONFLICT (id) DO UPDATE SET
                hashed_password = EXCLUDED.hashed_password,
                is_active = TRUE
        """, (ADMIN_ID, ADMIN_EMAIL, ADMIN_NAME, hashed, "EMP-0001", ADMIN_ROLE, ORG_ID))

        print(f"  Admin user ready: {ADMIN_EMAIL}", file=sys.stderr)
        cur.close()
        conn.close()

    except Exception as e:
        print(f"  WARNING: Could not ensure admin user: {e}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(ensure_admin())
