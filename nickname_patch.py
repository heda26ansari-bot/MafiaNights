# ==========================================
# nickname_patch.py
# پچ کامل سیستم نام مستعار برای ربات مافیا
# ==========================================

import json
import os
from aiogram import types

NICK_FILE = "nicknames.json"


# ----------------------------
# مدیریت نام‌های مستعار
# ----------------------------
class NicknameManager:
    def __init__(self):
        if not os.path.exists(NICK_FILE):
            with open(NICK_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)

        with open(NICK_FILE, "r", encoding="utf-8") as f:
            try:
                self.data = json.load(f)
            except:
                self.data = {}
                self.save()

    def save(self):
        with open(NICK_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def set(self, user_id: int, nickname: str):
        self.data[str(user_id)] = nickname
        self.save()

    def get(self, user_id: int):
        return self.data.get(str(user_id), None)

    def all(self):
        return self.data

    def display_name(self, user_id: int, fallback: str):
        """همیشه ابتدا نام مستعار را برمی‌گرداند"""
        return self.data.get(str(user_id), fallback)


# نمونه عمومی
nick = NicknameManager()


# ==========================================
#   توابع هندلرهای ربات برای مدیریت مستعار
# ==========================================

def register_nickname_handlers(dp, bot):
    """
    این تابع باید از main.py فراخوانی شود:
    register_nickname_handlers(dp, bot)
    """

    # -------------------------
    # ست‌کردن نام مستعار
    # -------------------------
    @dp.message_handler(lambda m: m.reply_to_message and m.text.startswith("تنظیم مستعار "))
    async def _(message: types.Message):
        target = message.reply_to_message.from_user
        nickname = message.text.replace("تنظیم مستعار ", "", 1).strip()

        nick.set(target.id, nickname)
        await message.reply(f"✅ نام مستعار برای {target.full_name} تنظیم شد: {nickname}")

    # -------------------------
    # دریافت نام مستعار
    # -------------------------
    @dp.message_handler(lambda m: m.reply_to_message and m.text.strip() == "نام مستعار")
    async def _(message: types.Message):
        target = message.reply_to_message.from_user
        nickname = nick.get(target.id)

        if nickname:
            await message.reply(f"📛 نام مستعار این کاربر: {nickname}")
        else:
            await message.reply("ℹ️ این کاربر نام مستعار ندارد.")

    # -------------------------
    # لیست مستعارها
    # -------------------------
    @dp.message_handler(lambda m: m.text.strip() == "لیست مستعار")
    async def _(message: types.Message):
        data = nick.all()
        if not data:
            await message.reply("📛 هیچ نام مستعاری ثبت نشده.")
            return

        text = "📛 <b>لیست نام‌های مستعار:</b>\n\n"
        for uid, name in sorted(data.items(), key=lambda x: x[1]):
            text += f" - {name}  <code>{uid}</code>\n"

        await message.reply(text, parse_mode="HTML")


# ==========================================
# تابع کمکی برای کل پروژه
# ==========================================
def display_name(user_id: int, fallback: str):
    """در کل پروژه فقط از این استفاده می‌کنیم"""
    return nick.display_name(user_id, fallback)
