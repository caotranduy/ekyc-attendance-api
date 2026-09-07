import uuid
import datetime
import random
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import engine, SessionLocal
import app.models.user_face
import app.models.check_in_log
from app.models.user import User
from app.models.check_in_log import CheckInLog

def upgrade_schema_if_needed():
    """Ensures SQLite users table has employee_code, gender, and dob columns."""
    with engine.connect() as conn:
        for col_def in [
            "ALTER TABLE users ADD COLUMN employee_code VARCHAR(20)",
            "ALTER TABLE users ADD COLUMN gender VARCHAR(10)",
            "ALTER TABLE users ADD COLUMN dob DATETIME",
            "ALTER TABLE users ADD COLUMN password VARCHAR(255)"
        ]:
            try:
                conn.execute(text(col_def))
                conn.commit()
            except Exception:
                pass

def seed_database():
    """Seeds 2 test employees with random check-in history for July 2026."""
    upgrade_schema_if_needed()
    db: Session = SessionLocal()
    try:
        # 1. Create or fetch User 1: Nguyễn Văn An
        user1 = db.query(User).filter(User.employee_code == "NV-1001").first()
        if not user1:
            user1 = User(
                id=uuid.UUID('0190c58e-1001-7000-8000-000000000001'),
                name="Nguyễn Văn An",
                username="an.nguyen",
                email="an.nguyen@company.com",
                employee_code="NV-1001",
                gender="Nam",
                dob=datetime.date(1995, 8, 15),
                is_active=True,
                is_admin=False
            )
            db.add(user1)
            print("Created employee: Nguyen Van An (NV-1001)")
        else:
            print("Employee NV-1001 already exists.")

        # 2. Create or fetch User 2: Trần Thị Bích
        user2 = db.query(User).filter(User.employee_code == "NV-1002").first()
        if not user2:
            user2 = User(
                id=uuid.UUID('0190c58e-1002-7000-8000-000000000002'),
                name="Trần Thị Bích",
                username="bich.tran",
                email="bich.tran@company.com",
                employee_code="NV-1002",
                gender="Nữ",
                dob=datetime.date(1998, 11, 20),
                is_active=True,
                is_admin=False
            )
            db.add(user2)
            print("Created employee: Tran Thi Bich (NV-1002)")
        else:
            print("Employee NV-1002 already exists.")

        db.commit()

        # 3. Generate random check-in logs for July 2026 (weekdays only)
        users = [user1, user2]
        july_days = [1, 2, 3, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17, 20, 21]

        added_logs_count = 0
        for u in users:
            for day in july_days:
                check_date = datetime.date(2026, 7, day)
                
                # Check if log already exists
                existing = db.query(CheckInLog).filter(
                    CheckInLog.user_id == u.id,
                    CheckInLog.check_in_date == check_date
                ).first()

                if not existing:
                    # Random check-in time between 07:45 and 08:30
                    hour = 7 if random.random() < 0.3 else 8
                    minute = random.randint(45, 59) if hour == 7 else random.randint(0, 30)
                    second = random.randint(0, 59)
                    
                    check_time = datetime.datetime(2026, 7, day, hour, minute, second)
                    
                    log = CheckInLog(
                        user_id=u.id,
                        check_in_at=check_time,
                        check_in_date=check_date
                    )
                    db.add(log)
                    added_logs_count += 1

        db.commit()
        print(f"Successfully seeded {added_logs_count} check-in logs for July 2026!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
