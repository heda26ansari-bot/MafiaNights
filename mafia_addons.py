# mafia_addons.py
# --------------------------------------------------------
# افزونه امکانات اضافه + ذخیره تنظیمات در فایل JSON دائمی
# --------------------------------------------------------

import json
import os
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


SETTINGS_FILE = "addons_settings.json"


class MafiaAddons:
    def __init__(self, bot):
        self.bot = bot

        # تنظیمات پیش‌فرض (در صورت نبود فایل)
        self.settings = {
            "security": {
                "control_speech": True,
                "delete_out_of_turn": True,
            },
            "next": {
                "anti_spam": True,
            },
            "auto_start": {
                "enabled": False,
            },
            "color": {
                "primary": True,
                "challenge": True,
            }
        }

        # لود تنظیمات قبلی
        self.load_settings()

        # این‌ها توسط برنامه اصلی ست می‌شود
        self.group_id = None
        self.moderator_id = None

    # --------------------------------------------------------
    # ذخیره تنظیمات روی فایل JSON
    # --------------------------------------------------------
    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print("⚠️ خطا در ذخیره تنظیمات:", e)

    # --------------------------------------------------------
    # لود تنظیمات از فایل JSON
    # --------------------------------------------------------
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            except:
                print("⚠️ فایل تنظیمات خراب است، تنظیمات جدید ساخته شد.")
                self.save_settings()  # ساخت فایل جدید

    # --------------------------------------------------------
    # ثبت محیط لازم از برنامه اصلی
    # --------------------------------------------------------
    def register(self, *, moderator_id, group_id):
        self.moderator_id = moderator_id
        self.group_id = group_id

    # --------------------------------------------------------
    # نمایش منوی اصلی افزونه
    # --------------------------------------------------------
    async def open_addons_menu(self, callback: types.CallbackQuery):
        kb = InlineKeyboardMarkup()

        kb.add(InlineKeyboardButton("🔐 امنیت بازی", callback_data="addons_security"))
        kb.add(InlineKeyboardButton("⏭ مدیریت نکست", callback_data="addons_next"))
        kb.add(InlineKeyboardButton("▶ شروع خودکار", callback_data="addons_auto"))
        kb.add(InlineKeyboardButton("🎨 رنگ‌بندی پیام‌ها", callback_data="addons_color"))
        kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="panel_back"))

        await callback.message.edit_text(
            "⚙️ <b>امکانات اضافه</b>\n\nیکی از بخش‌ها را انتخاب کنید:",
            reply_markup=kb, parse_mode="HTML"
        )

    # --------------------------------------------------------
    # 🔐 امنیت
    # --------------------------------------------------------
    async def menu_security(self, callback: types.CallbackQuery):
        kb = InlineKeyboardMarkup()

        kb.add(InlineKeyboardButton(
            f"🟦 کنترل نوبت صحبت: {'فعال' if self.settings['security']['control_speech'] else 'غیرفعال'}",
            callback_data="toggle_control_speech"
        ))

        kb.add(InlineKeyboardButton(
            f"🗑 حذف پیام‌های خارج نوبت: {'فعال' if self.settings['security']['delete_out_of_turn'] else 'غیرفعال'}",
            callback_data="toggle_delete_messages"
        ))

        kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="addons_menu"))

        await callback.message.edit_text(
            "🔐 <b>امنیت بازی</b>\nگزینه‌های زیر را مدیریت کنید:",
            reply_markup=kb, parse_mode="HTML"
        )

    # --------------------------------------------------------
    # ⏭ مدیریت نکست
    # --------------------------------------------------------
    async def menu_next(self, callback: types.CallbackQuery):
        kb = InlineKeyboardMarkup()

        kb.add(InlineKeyboardButton(
            f"⏭ ضد اسپم نکست: {'فعال' if self.settings['next']['anti_spam'] else 'غیرفعال'}",
            callback_data="toggle_next_antispam"
        ))

        kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="addons_menu"))

        await callback.message.edit_text(
            "⏭ <b>مدیریت نکست</b>",
            reply_markup=kb, parse_mode="HTML"
        )

    # --------------------------------------------------------
    # ▶ شروع خودکار
    # --------------------------------------------------------
    async def menu_auto(self, callback: types.CallbackQuery):
        kb = InlineKeyboardMarkup()

        kb.add(InlineKeyboardButton(
            f"▶ Auto Start: {'فعال' if self.settings['auto_start']['enabled'] else 'غیرفعال'}",
            callback_data="toggle_autostart"
        ))

        kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="addons_menu"))

        await callback.message.edit_text(
            "▶ <b>شروع خودکار دور جدید</b>",
            reply_markup=kb,
            parse_mode="HTML"
        )

    # --------------------------------------------------------
    # 🎨 رنگ‌بندی پیام‌ها
    # --------------------------------------------------------
    async def menu_color(self, callback: types.CallbackQuery):
        kb = InlineKeyboardMarkup()

        kb.add(InlineKeyboardButton(
            f"🎨 رنگ نوبت اصلی: {'فعال' if self.settings['color']['primary'] else 'غیرفعال'}",
            callback_data="toggle_color_primary"
        ))

        kb.add(InlineKeyboardButton(
            f"🟥 رنگ نوبت چالش: {'فعال' if self.settings['color']['challenge'] else 'غیرفعال'}",
            callback_data="toggle_color_challenge"
        ))

        kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="addons_menu"))

        await callback.message.edit_text(
            "🎨 <b>رنگ‌بندی پیام‌ها</b>",
            reply_markup=kb,
            parse_mode="HTML"
        )

    # --------------------------------------------------------
    # دکمه‌های توگل
    # --------------------------------------------------------
    def toggle(self, section, key):
        self.settings[section][key] = not self.settings[section][key]
        self.save_settings()
