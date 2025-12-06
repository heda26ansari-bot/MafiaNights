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
class DummyNicknameManager:
    """کلاس جایگزین در صورت شکست اتصال به دیتابیس"""
    def __init__(self):
        logging.critical("❌ استفاده از حالت Dummy: نام مستعار ذخیره نخواهد شد.")
        
    def set(self, user_id, nickname):
        pass # عملیاتی انجام نمی‌دهد
        
    def get(self, user_id):
        return None
        
    def all(self):
        return {}


# ------------------------------------------------
# تعیین کلاس نهایی برای ایمپورت
# ------------------------------------------------
# کلاس نهایی که از این ماژول ایمپورت می‌شود
FinalNicknameManager = NicknameManager 

if not db_initialization_success:
    # اگر اتصال دیتابیس شکست خورد، از کلاس Dummy استفاده کن
    FinalNicknameManager = DummyNicknameManager

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
