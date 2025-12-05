import os
import logging
from sqlalchemy import create_engine, Column, BigInteger, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ------------------------------------------------
# تنظیمات دیتابیس
# ------------------------------------------------
# Railway به صورت خودکار متغیر DATABASE_URL را تنظیم می‌کند
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # اگر در محیط توسعه محلی هستید، رشته اتصال دیتابیس خود را وارد کنید
    logging.error("❌ متغیر محیطی DATABASE_URL تنظیم نشده است!")
    # اگر در Railway اجرا می‌شود، اینجا متوقف می‌شود

# اگر DATABASE_URL با postgres:// شروع شده (که در Railway پیش‌فرض است)
# باید آن را برای سازگاری با SQLAlchemy 2.0 به postgresql+psycopg2:// تغییر دهیم.
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)


# ایجاد موتور دیتابیس و Base برای تعریف مدل‌ها
engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ------------------------------------------------
# مدل دیتابیس (جدول Nickname)
# ------------------------------------------------
class Nickname(Base):
    """مدل ذخیره نام‌های مستعار بازیکنان"""
    __tablename__ = "nicknames"

    # user_id: کلید اصلی (BigInteger برای user ID تلگرام)
    user_id = Column(BigInteger, primary_key=True, index=True)
    # nickname: نام مستعار (رشته)
    nickname = Column(String, index=True)

# ------------------------------------------------
# کلاس NicknameManager جدید
# ------------------------------------------------
class NicknameManager:
    def __init__(self):
        # مطمئن شوید که جدول nicknames در دیتابیس وجود دارد
        Base.metadata.create_all(bind=engine)
        logging.info("✅ اتصال به PostgreSQL و ایجاد جدول Nicknames موفقیت‌آمیز بود.")

    def set(self, user_id, nickname):
        """نام مستعار جدیدی را برای کاربر تنظیم و ذخیره می‌کند."""
        session = SessionLocal()
        try:
            # سعی در پیدا کردن رکورد
            record = session.query(Nickname).filter(Nickname.user_id == user_id).first()

            if record:
                # اگر رکورد وجود داشت، آن را به روز رسانی کن
                record.nickname = nickname
            else:
                # اگر وجود نداشت، رکورد جدیدی ایجاد کن
                new_record = Nickname(user_id=user_id, nickname=nickname)
                session.add(new_record)
            
            session.commit()
        except Exception as e:
            session.rollback()
            logging.error(f"❌ خطای ذخیره‌سازی نام مستعار در دیتابیس: {e}")
        finally:
            session.close()

    def get(self, user_id):
        """نام مستعار یک کاربر را دریافت می‌کند."""
        session = SessionLocal()
        try:
            record = session.query(Nickname).filter(Nickname.user_id == user_id).first()
            return record.nickname if record else None
        except Exception as e:
            logging.error(f"❌ خطای دریافت نام مستعار از دیتابیس: {e}")
            return None
        finally:
            session.close()

    def all(self):
        """همه نام‌های مستعار ذخیره شده را به صورت دیکشنری {user_id: nickname} برمی‌گرداند."""
        session = SessionLocal()
        try:
            records = session.query(Nickname).all()
            return {r.user_id: r.nickname for r in records}
        except Exception as e:
            logging.error(f"❌ خطای دریافت همه نام‌های مستعار: {e}")
            return {}
        finally:
            session.close()

# ------------------------------------------------
# تست ایمپورت (برای برطرف کردن خطای قبلی)
# ------------------------------------------------
try:
    # یک نمونه برای اطمینان از صحت ایمپورت ایجاد کنید
    # این خط همان خطی است که در main.py شما اجرا می‌شود: nicknames = NicknameManager()
    temp_manager = NicknameManager() 
except Exception as e:
    logging.critical(f"❌ خطای حیاتی در راه‌اندازی NicknameManager: {e}")
    # اگر این کد با موفقیت اجرا شود، خطای main.py رفع خواهد شد.
