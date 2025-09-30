FROM python:3.11-slim

WORKDIR /Mafia

COPY requirements.txt .

# ساخت venv و نصب پکیج‌ها
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

COPY . .

# ایجاد اسکریپت اجرا
RUN echo '#!/bin/sh\n/opt/venv/bin/python /Mafia/main.py' > /run.sh \
    && chmod +x /run.sh

# اجرای ربات
CMD ["/run.sh"]
