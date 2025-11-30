# mafia_addons.py
# --------------------------------------------------------
# افزونه امکانات اضافه + ذخیره تنظیمات در فایل JSON دائمی
# سازگار با main.py موجود (Aiogram)
# --------------------------------------------------------

import json
import os
import copy
import logging
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

SETTINGS_FILE = "addons_settings.json"
LOG_TAG = "MafiaAddons"

# تنظیمات پیش‌فرض (برای هر گروه)
DEFAULT_GROUP_SETTINGS = {
    "security": {
        "control_speech": True,
        "delete_out_of_turn": True
    },
    "next": {
        "anti_spam": True,
        # compatibility keys
        "allow_players_next": True,
        "allow_moderator_next": True
    },
    "auto_start": {
        "enabled": False
    },
    "color": {
        "primary": True,
        "challenge": True,
        # optional prefix string shown before timer messages
        "timer_prefix": ""
    }
}


class MafiaAddons:
    """
    کلاس مدیریت افزونه‌ها، نگهداری تنظیمات و منوهای پیوی
    استفاده:
      addons = MafiaAddons(bot)
      addons.setup_handlers(dp)   # فقط یک‌بار در startup
      addons.register(moderator_id=..., group_id=...)  # وقتی یک گرداننده در لابی انتخاب می‌شود
    بعد از register، addons.settings به تنظیمات گروه جاری اشاره می‌کند.
    """

    def __init__(self, bot):
        self.bot = bot
        # بار اولیه تنظیمات: dict که هر کلید = str(group_id) و مقدار = dict تنظیمات آن گروه
        self._all_settings = {}
        # در register بعدی مقداردهی خواهد شد
        self.group_id = None
        self.moderator_id = None
        # setting view برای گروه جاری (برای سازگاری با کد فعلی که addons.settings.get(...) استفاده می‌کند)
        self.settings = copy.deepcopy(DEFAULT_GROUP_SETTINGS)

        # لود از فایل (اگر موجود باشد)
        self._load_from_file()

    # -------------------------
    # فایل ذخیره/بارگذاری
    # -------------------------
    def _load_from_file(self):
        if not os.path.exists(SETTINGS_FILE):
            # ساختار پایه با یک کلید default (اگر لازم باشه)
            self._all_settings = {}
            return

        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._all_settings = data
                else:
                    logging.warning("%s: تنظیمات فایل نامعتبر است؛ ساختار جدید ساخته شد.", LOG_TAG)
                    self._all_settings = {}
        except Exception as e:
            logging.exception("%s: خطا در خواندن فایل تنظیمات: %s", LOG_TAG, e)
            self._all_settings = {}

    def _save_to_file(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._all_settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.exception("%s: خطا در نوشتن فایل تنظیمات: %s", LOG_TAG, e)

    # -------------------------
    # کمک‌ها: گرفتن/تنظیم تنظیمات گروه
    # -------------------------
    def _group_key(self, group_id):
        return str(group_id)

    def get_group_settings(self, group_id):
        key = self._group_key(group_id)
        s = self._all_settings.get(key)
        if s is None:
            # return deep copy of default so modification doesn't alter DEFAULT_GROUP_SETTINGS
            s = copy.deepcopy(DEFAULT_GROUP_SETTINGS)
            # ensure compatibility keys exist
            if "next" not in s:
                s["next"] = {"anti_spam": True, "allow_players_next": True, "allow_moderator_next": True}
            if "security" not in s:
                s["security"] = {"control_speech": True, "delete_out_of_turn": True}
            # don't write auto into file immediately; will save on register/toggle
            self._all_settings[key] = s
            self._save_to_file()
        return s

    def set_group_settings(self, group_id, settings_dict):
        key = self._group_key(group_id)
        self._all_settings[key] = settings_dict
        # update active settings if group matches
        if self.group_id and self._group_key(self.group_id) == key:
            self.settings = self._all_settings[key]
        self._save_to_file()

    # -------------------------
    # register: اتصال افزونه به گروه و گرداننده
    # -------------------------
    def register(self, *, moderator_id, group_id):
        """
        وقتی گرداننده در لابی انتخاب می‌شود، main.py این را صدا می‌زند.
        این متد تنظیمات گروه را بارگذاری می‌کند و self.settings را به آن اشاره می‌دهد.
        """
        try:
            self.moderator_id = moderator_id
            self.group_id = group_id
            self.settings = self.get_group_settings(group_id)
            # ضمانت وجود کلیدهای مهم (برای سازگاری)
            # next.* keys
            self.settings.setdefault("next", {})
            self.settings["next"].setdefault("anti_spam", True)
            self.settings["next"].setdefault("allow_players_next", True)
            self.settings["next"].setdefault("allow_moderator_next", True)
            # security keys
            self.settings.setdefault("security", {})
            self.settings["security"].setdefault("control_speech", True)
            self.settings["security"].setdefault("delete_out_of_turn", True)
            # auto_start
            self.settings.setdefault("auto_start", {})
            self.settings["auto_start"].setdefault("enabled", False)
            # color
            self.settings.setdefault("color", {})
            self.settings["color"].setdefault("primary", True)
            self.settings["color"].setdefault("challenge", True)
            self.settings["color"].setdefault("timer_prefix", "")

            # بازنویسی در فایل (در صورت نبود)
            self._all_settings[self._group_key(group_id)] = self.settings
            self._save_to_file()
        except Exception as e:
            logging.exception("%s: خطا در register افزونه: %s", LOG_TAG, e)

    # -------------------------
    # متد عمومی: setup_handlers
    # - این متد را یک بار در startup فراخوانی کن (main.py)
    # -------------------------
    def setup_handlers(self, dp):
        """
        ثبت هندلرهای callback query مورد نیاز افزونه در dispatcher.
        فراخوانی فقط یک بار در زمان startup لازم است.
        """
        # منوی اصلی افزونه
        dp.register_callback_query_handler(self._open_menu_handler, lambda c: c.data == "addons_menu")

        # زیربخش‌ها
        dp.register_callback_query_handler(self._open_security_menu, lambda c: c.data == "addons_security")
        dp.register_callback_query_handler(self._open_next_menu, lambda c: c.data == "addons_next")
        dp.register_callback_query_handler(self._open_auto_menu, lambda c: c.data == "addons_auto")
        dp.register_callback_query_handler(self._open_color_menu, lambda c: c.data == "addons_color")

        # توگل‌ها
        dp.register_callback_query_handler(self._toggle_control_speech, lambda c: c.data == "toggle_control_speech")
        dp.register_callback_query_handler(self._toggle_delete_messages, lambda c: c.data == "toggle_delete_messages")
        dp.register_callback_query_handler(self._toggle_next_antispam, lambda c: c.data == "toggle_next_antispam")
        dp.register_callback_query_handler(self._toggle_autostart, lambda c: c.data == "toggle_autostart")
        dp.register_callback_query_handler(self._toggle_color_primary, lambda c: c.data == "toggle_color_primary")
        dp.register_callback_query_handler(self._toggle_color_challenge, lambda c: c.data == "toggle_color_challenge")

        # بازگشت / navigation
        dp.register_callback_query_handler(self._back_to_addons_menu, lambda c: c.data == "panel_back")
        dp.register_callback_query_handler(self._back_to_main, lambda c: c.data == "addons_menu")

    # -------------------------
    # منوها — wrapper برای استفاده در main
    # -------------------------
    async def open_addons_menu(self, callback: types.CallbackQuery):
        """
        فراخوانیِ منوی اصلی افزونه؛ اگر تنظیمات گروه لود نشده باشند،
        از group_id استفاده می‌کند وقتی که register صدا زده شده باشد.
        """
        # اگر register نشده باشیم سعی کن از callback.chat.id استفاده کنی
        if not self.group_id:
            # اگر در پیوی اجرا می‌شود، باید moderator_id و group_id از قبل set شده باشد
            # fallback: تلاش برای استفاده از پیام مرجع
            try:
                # اگر callback.message.chat.type == 'private' تلاش برای استفاده از moderator_id
                if callback.message.chat.type == "private" and self.moderator_id:
                    # group_id قبلاً باید register شده باشد، در غیر این صورت پیام به کاربر بده
                    pass
            except:
                pass

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔐 امنیت بازی", callback_data="addons_security"))
        kb.add(InlineKeyboardButton("⏭ مدیریت نکست", callback_data="addons_next"))
        kb.add(InlineKeyboardButton("▶ شروع خودکار", callback_data="addons_auto"))
        kb.add(InlineKeyboardButton("🎨 رنگ‌بندی پیام‌ها", callback_data="addons_color"))
        kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="panel_back"))

        try:
            await callback.message.edit_text(
                "⚙️ <b>امکانات اضافه</b>\n\nیکی از بخش‌ها را انتخاب کنید:",
                reply_markup=kb, parse_mode="HTML"
            )
        except Exception:
            try:
                await callback.message.answer(
                    "⚙️ <b>امکانات اضافه</b>\n\nیکی از بخش‌ها را انتخاب کنید:",
                    reply_markup=kb, parse_mode="HTML"
                )
            except:
                pass

    # -------------------------
    # منوی امنیت
    # -------------------------
    async def _open_security_menu(self, callback: types.CallbackQuery):
        # اطمینان از این که تنظیمات برای گروه جاری وجود دارد
        if self.group_id:
            self.settings = self.get_group_settings(self.group_id)

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(
            f"🟦 کنترل نوبت صحبت: {'فعال' if self.settings['security'].get('control_speech', True) else 'غیرفعال'}",
            callback_data="toggle_control_speech"
        ))
        kb.add(InlineKeyboardButton(
            f"🗑 حذف پیام‌های خارج نوبت: {'فعال' if self.settings['security'].get('delete_out_of_turn', True) else 'غیرفعال'}",
            callback_data="toggle_delete_messages"
        ))
        kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="panel_back"))

        try:
            await callback.message.edit_text(
                "🔐 <b>امنیت بازی</b>\nگزینه‌های زیر را مدیریت کنید:",
                reply_markup=kb, parse_mode="HTML"
            )
        except Exception:
            try:
                await callback.message.answer(
                    "🔐 <b>امنیت بازی</b>\nگزینه‌های زیر را مدیریت کنید:",
                    reply_markup=kb, parse_mode="HTML"
                )
            except:
                pass

    # -------------------------
    # منوی نکست
    # -------------------------
    async def _open_next_menu(self, callback: types.CallbackQuery):
        if self.group_id:
            self.settings = self.get_group_settings(self.group_id)

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(
            f"⏭ ضد اسپم نکست: {'فعال' if self.settings['next'].get('anti_spam', True) else 'غیرفعال'}",
            callback_data="toggle_next_antispam"
        ))
        kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="panel_back"))

        try:
            await callback.message.edit_text(
                "⏭ <b>مدیریت نکست</b>",
                reply_markup=kb, parse_mode="HTML"
            )
        except Exception:
            try:
                await callback.message.answer("⏭ <b>مدیریت نکست</b>", reply_markup=kb, parse_mode="HTML")
            except:
                pass

    # -------------------------
    # منوی اتو استارت
    # -------------------------
    async def _open_auto_menu(self, callback: types.CallbackQuery):
        if self.group_id:
            self.settings = self.get_group_settings(self.group_id)

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(
            f"▶ Auto Start: {'فعال' if self.settings['auto_start'].get('enabled', False) else 'غیرفعال'}",
            callback_data="toggle_autostart"
        ))
        kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="panel_back"))

        try:
            await callback.message.edit_text(
                "▶ <b>شروع خودکار دور جدید</b>",
                reply_markup=kb, parse_mode="HTML"
            )
        except Exception:
            try:
                await callback.message.answer("▶ <b>شروع خودکار دور جدید</b>", reply_markup=kb, parse_mode="HTML")
            except:
                pass

    # -------------------------
    # منوی رنگ
    # -------------------------
    async def _open_color_menu(self, callback: types.CallbackQuery):
        if self.group_id:
            self.settings = self.get_group_settings(self.group_id)

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(
            f"🎨 رنگ نوبت اصلی: {'فعال' if self.settings['color'].get('primary', True) else 'غیرفعال'}",
            callback_data="toggle_color_primary"
        ))
        kb.add(InlineKeyboardButton(
            f"🟥 رنگ نوبت چالش: {'فعال' if self.settings['color'].get('challenge', True) else 'غیرفعال'}",
            callback_data="toggle_color_challenge"
        ))
        kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="panel_back"))

        try:
            await callback.message.edit_text(
                "🎨 <b>رنگ‌بندی پیام‌ها</b>",
                reply_markup=kb, parse_mode="HTML"
            )
        except Exception:
            try:
                await callback.message.answer("🎨 <b>رنگ‌بندی پیام‌ها</b>", reply_markup=kb, parse_mode="HTML")
            except:
                pass

    # -------------------------
    # توگل‌ها
    # -------------------------
    async def _toggle_control_speech(self, callback: types.CallbackQuery):
        if not self.group_id:
            await callback.answer("⚠️ ابتدا یک بازی/گروه ثبت شود.", show_alert=True)
            return

        # فقط گرداننده اجازه دارد
        if callback.from_user.id != self.moderator_id:
            await callback.answer("⚠️ فقط گرداننده می‌تواند این تنظیمات را تغییر دهد.", show_alert=True)
            return

        self.settings['security']['control_speech'] = not self.settings['security'].get('control_speech', True)
        # persist
        self._all_settings[self._group_key(self.group_id)] = self.settings
        self._save_to_file()

        await callback.answer("✔️ وضعیت ذخیره شد.")
        # بازگشت به منو امنیت
        await self._open_security_menu(callback)

    async def _toggle_delete_messages(self, callback: types.CallbackQuery):
        if not self.group_id:
            await callback.answer("⚠️ ابتدا یک بازی/گروه ثبت شود.", show_alert=True)
            return
        if callback.from_user.id != self.moderator_id:
            await callback.answer("⚠️ فقط گرداننده می‌تواند این تنظیمات را تغییر دهد.", show_alert=True)
            return

        self.settings['security']['delete_out_of_turn'] = not self.settings['security'].get('delete_out_of_turn', True)
        self._all_settings[self._group_key(self.group_id)] = self.settings
        self._save_to_file()

        await callback.answer("✔️ وضعیت ذخیره شد.")
        await self._open_security_menu(callback)

    async def _toggle_next_antispam(self, callback: types.CallbackQuery):
        if not self.group_id:
            await callback.answer("⚠️ ابتدا یک بازی/گروه ثبت شود.", show_alert=True)
            return
        if callback.from_user.id != self.moderator_id:
            await callback.answer("⚠️ فقط گرداننده می‌تواند این تنظیمات را تغییر دهد.", show_alert=True)
            return

        self.settings['next']['anti_spam'] = not self.settings['next'].get('anti_spam', True)
        self._all_settings[self._group_key(self.group_id)] = self.settings
        self._save_to_file()

        await callback.answer("✔️ وضعیت ذخیره شد.")
        await self._open_next_menu(callback)

    async def _toggle_autostart(self, callback: types.CallbackQuery):
        if not self.group_id:
            await callback.answer("⚠️ ابتدا یک بازی/گروه ثبت شود.", show_alert=True)
            return
        if callback.from_user.id != self.moderator_id:
            await callback.answer("⚠️ فقط گرداننده می‌تواند این تنظیمات را تغییر دهد.", show_alert=True)
            return

        self.settings['auto_start']['enabled'] = not self.settings['auto_start'].get('enabled', False)
        self._all_settings[self._group_key(self.group_id)] = self.settings
        self._save_to_file()

        await callback.answer("✔️ وضعیت ذخیره شد.")
        await self._open_auto_menu(callback)

    async def _toggle_color_primary(self, callback: types.CallbackQuery):
        if not self.group_id:
            await callback.answer("⚠️ ابتدا یک بازی/گروه ثبت شود.", show_alert=True)
            return
        if callback.from_user.id != self.moderator_id:
            await callback.answer("⚠️ فقط گرداننده می‌تواند این تنظیمات را تغییر دهد.", show_alert=True)
            return

        self.settings['color']['primary'] = not self.settings['color'].get('primary', True)
        self._all_settings[self._group_key(self.group_id)] = self.settings
        self._save_to_file()

        await callback.answer("✔️ وضعیت ذخیره شد.")
        await self._open_color_menu(callback)

    async def _toggle_color_challenge(self, callback: types.CallbackQuery):
        if not self.group_id:
            await callback.answer("⚠️ ابتدا یک بازی/گروه ثبت شود.", show_alert=True)
            return
        if callback.from_user.id != self.moderator_id:
            await callback.answer("⚠️ فقط گرداننده می‌تواند این تنظیمات را تغییر دهد.", show_alert=True)
            return

        self.settings['color']['challenge'] = not self.settings['color'].get('challenge', True)
        self._all_settings[self._group_key(self.group_id)] = self.settings
        self._save_to_file()

        await callback.answer("✔️ وضعیت ذخیره شد.")
        await self._open_color_menu(callback)

    # -------------------------
    # navigation / back
    # -------------------------
    async def _back_to_addons_menu(self, callback: types.CallbackQuery):
        # بازگردانی view و نمایش منوی اصلی افزونه
        await self.open_addons_menu(callback)

    async def _back_to_main(self, callback: types.CallbackQuery):
        # بازگشت به منوی بالا (برای consistency)
        await self.open_addons_menu(callback)

    # -------------------------
    # helpers : convenience برای main.py
    # -------------------------
    def is_control_speech_enabled(self):
        return self.settings.get("security", {}).get("control_speech", True)

    def is_delete_out_of_turn_enabled(self):
        return self.settings.get("security", {}).get("delete_out_of_turn", True)

    def is_next_antispam_enabled(self):
        return self.settings.get("next", {}).get("anti_spam", True)

    def is_player_next_allowed(self):
        return self.settings.get("next", {}).get("allow_players_next", True)

    def is_moderator_next_allowed(self):
        return self.settings.get("next", {}).get("allow_moderator_next", True)

    def is_auto_start_enabled(self):
        return self.settings.get("auto_start", {}).get("enabled", False)

    def is_color_primary(self):
        return self.settings.get("color", {}).get("primary", True)

    def is_color_challenge(self):
        return self.settings.get("color", {}).get("challenge", True)

    def get_timer_prefix(self):
        return self.settings.get("color", {}).get("timer_prefix", "")

    # -------------------------
    # API کوچک برای main.py که لازم است
    # -------------------------
    def ensure_defaults_for_group(self, group_id):
        """
        تضمین می‌کند که تنظیمات برای group_id وجود داشته باشد.
        """
        key = self._group_key(group_id)
        if key not in self._all_settings:
            self._all_settings[key] = copy.deepcopy(DEFAULT_GROUP_SETTINGS)
            self._save_to_file()

    def export_current_settings(self):
        """ برای دسترسی سریع در main.py می‌توانید از addons.settings استفاده کنید. """
        return self.settings
