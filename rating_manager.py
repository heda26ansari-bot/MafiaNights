# rating_manager.py
import json
import os
import time
import logging
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import types

LOG = "RatingManager"
DB_FILE = "ratings.json"

class RatingManager:
    def __init__(self, bot, dp, get_group_id_fn, get_moderator_fn, get_players_fn, get_display_name_fn):
        """
        bot, dp: از main.py
        get_group_id_fn: تابع بدون آرگومان که آیدی گروه فعلی را برمی‌گرداند (group_chat_id)
        get_moderator_fn: تابع بدون آرگومان که moderator_id فعلی را برمی‌گرداند
        get_players_fn: تابع بدون آرگومان که dict یا list بازیکنان را برمی‌گرداند
                        (پیشنهاد: dict user_id -> name)
        get_display_name_fn: تابع user_id -> نمایش (نام مستعار یا نام واقعی)
        """
        self.bot = bot
        self.dp = dp
        self.get_group_id = get_group_id_fn
        self.get_moderator = get_moderator_fn
        self.get_players = get_players_fn
        self.get_display_name = get_display_name_fn

        # data structure
        # {
        #   "next_game_id": 1,
        #   "games": { "1": { "group_id": -100..., "timestamp": 173..., "ratings": { "from": { "to": val } }, "players": [uid,...] } },
        #   "users": { "uid": { "games": { "game_id": average_score, ... } } }
        # }
        self.db = {"next_game_id": 1, "games": {}, "users": {}}
        self._load()

        # register handlers
        self._register_handlers()

    # ---------- persistence ----------
    def _load(self):
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    self.db = json.load(f)
            except Exception as e:
                logging.warning("%s: can't load file, creating new: %s", LOG, e)
                self.db = {"next_game_id": 1, "games": {}, "users": {}}
                self._save()
        else:
            self._save()

    def _save(self):
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(self.db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.exception("%s: error saving DB: %s", LOG, e)

    # ---------- helpers ----------
    def _new_game_id(self):
        gid = str(self.db.get("next_game_id", 1))
        self.db["next_game_id"] = int(gid) + 1
        return gid

    def _now_ts(self):
        return int(time.time())

    # ---------- handlers registration ----------
    def _register_handlers(self):
        # پیام اتمام بازی — خودکار توسط گرداننده در گروه (متن دقیقا "اتمام بازی")
        @self.dp.message_handler(lambda m: m.chat.type in ["group", "supergroup"] and m.text and m.text.strip() == "اتمام بازی")
        async def on_game_end(message: types.Message):
            try:
                group_id = self.get_group_id()
                moderator = self.get_moderator()
            except Exception:
                group_id = message.chat.id
                moderator = None

            # فقط از گرداننده قبول کن
            if moderator is None or message.from_user.id != moderator:
                await message.reply("❌ فقط گرداننده می‌تواند اتمام بازی را اعلام کند.")
                return

            # جمع‌آوری بازیکنان فعلی
            players = self.get_players()
            # players may be dict user_id->name or list of uids
            if not players:
                await message.reply("⚠️ هیچ بازیکنی برای امتیازدهی پیدا نشد.")
                return

            # normalize list of user ids
            if isinstance(players, dict):
                player_ids = list(players.keys())
            elif isinstance(players, list):
                player_ids = players[:]
            else:
                # try iter
                try:
                    player_ids = list(players)
                except:
                    player_ids = []

            if not player_ids:
                await message.reply("⚠️ لیست بازیکنان خالی است.")
                return

            # create new game entry
            game_id = self._new_game_id()
            self.db["games"][game_id] = {
                "group_id": group_id,
                "timestamp": self._now_ts(),
                "ratings": {},   # from_user -> { to_user: value }
                "players": [int(x) for x in player_ids]
            }
            self._save()

            # send voting message
            text = "🎯 <b>امتیازدهی به بازیکنان</b>\n\n"
            text += "به هر بازیکن یک امتیاز از 1 تا 5 بدهید. (هر فرد برای هر بازیکن فقط یک بار می‌تواند رأی دهد)\n\n"

            for uid in self.db["games"][game_id]["players"]:
                name = self.get_display_name(int(uid))
                text += f"🔹 {name}\n"

            # build keyboard: for each player, create five rows (1..5) — single column per requirement
            kb = InlineKeyboardMarkup(row_width=1)
            for uid in self.db["games"][game_id]["players"]:
                uid = int(uid)
                # header button as non-clickable (we'll add as label via callback_data "noop")
                kb.add(InlineKeyboardButton(f"— {self.get_display_name(uid)} —", callback_data=f"noop_{game_id}"))
                # 1..5 rows
                for val in range(1, 6):
                    kb.add(InlineKeyboardButton(f"⭐ {val}", callback_data=f"rate|{game_id}|{uid}|{val}"))
                # separator
                kb.add(InlineKeyboardButton(" ", callback_data=f"noop_{game_id}"))

            sent = await message.reply(text, reply_markup=kb, parse_mode="HTML")
            # store the message id to be able to edit later if needed
            self.db["games"][game_id]["message_id"] = sent.message_id
            self.db["games"][game_id]["chat_id"] = sent.chat.id
            self._save()

            await message.reply("✅ امتیازدهی آغاز شد — هر کس می‌تواند رأی خود را ثبت کند.")

        # callback for rating buttons
        @self.dp.callback_query_handler(lambda c: c.data and c.data.startswith("rate|"))
        async def on_rate_callback(callback: types.CallbackQuery):
            """
            callback.data = "rate|{game_id}|{target_uid}|{val}"
            """
            parts = callback.data.split("|")
            if len(parts) != 4:
                await callback.answer("⚠️ دادهٔ نامعتبر.", show_alert=True)
                return
            _, game_id, target_uid_str, val_str = parts
            from_uid = callback.from_user.id
            try:
                target_uid = int(target_uid_str)
                val = int(val_str)
            except:
                await callback.answer("⚠️ دادهٔ نامعتبر.", show_alert=True)
                return

            # validate game exists
            game = self.db["games"].get(game_id)
            if not game:
                await callback.answer("⚠️ این نظرسنجی دیگر فعال نیست.", show_alert=True)
                return

            chat_id = game.get("chat_id")
            # ensure voter is member of that group
            try:
                member = await self.bot.get_chat_member(chat_id, from_uid)
            except:
                await callback.answer("⛔ فقط اعضای گروه می‌توانند رأی دهند.", show_alert=True)
                return

            # cannot vote for self
            if int(from_uid) == int(target_uid):
                await callback.answer("❌ نمی‌توانید به خودتان رأی دهید.", show_alert=True)
                return

            # ensure target in players
            if target_uid not in game.get("players", []):
                await callback.answer("⚠️ بازیکن انتخاب‌شده در این بازی نیست.", show_alert=True)
                return

            # check if voter already voted for this target in this game
            existing = game["ratings"].get(str(from_uid), {})
            if str(target_uid) in existing:
                await callback.answer("⚠️ شما قبلاً به این بازیکن رأی داده‌اید.", show_alert=True)
                return

            # record vote
            # structure: game["ratings"][from_uid_str] = {"target_uid_str": value, ...}
            game["ratings"].setdefault(str(from_uid), {})[str(target_uid)] = val
            self._save()

            # update user stats: we only compute aggregates when poll ends (on اتمام نظرسنجی)
            # but we should update the INLINE keyboard to show that this user voted (global tick)
            # rebuild keyboard labels: for each player, find if any user already voted for them? we will mark a tick for the value given by the caller
            kb = InlineKeyboardMarkup(row_width=1)
            for uid in game["players"]:
                uid = int(uid)
                kb.add(InlineKeyboardButton(f"— {self.get_display_name(uid)} —", callback_data=f"noop_{game_id}"))
                # for each val row: if this current callback.from_user voted for this uid, show check
                user_votes = game["ratings"].get(str(from_uid), {})
                voted_val_for_this = user_votes.get(str(uid))
                for v in range(1, 6):
                    label = f"⭐ {v}"
                    if voted_val_for_this and int(v) == int(voted_val_for_this):
                        label = f"✔ {v}"
                    kb.add(InlineKeyboardButton(label, callback_data=f"rate|{game_id}|{uid}|{v}"))
                kb.add(InlineKeyboardButton(" ", callback_data=f"noop_{game_id}"))

            # edit original message
            try:
                await self.bot.edit_message_reply_markup(chat_id=game["chat_id"], message_id=game.get("message_id"), reply_markup=kb)
            except Exception:
                # ignore edit errors
                pass

            await callback.answer("✅ رأی شما ثبت شد.", show_alert=True)

        # end poll handler (moderator triggers with "اتمام نظرسنجی")
        @self.dp.message_handler(lambda m: m.chat.type in ["group", "supergroup"] and m.text and m.text.strip() == "اتمام نظرسنجی")
        async def on_finish_poll(message: types.Message):
            try:
                moderator = self.get_moderator()
            except:
                moderator = None

            if moderator is None or message.from_user.id != moderator:
                await message.reply("❌ فقط گرداننده می‌تواند نظرسنجی را پایان دهد.")
                return

            # find the latest active game in this group that hasn't been finalized yet
            group_id = self.get_group_id()
            # find last game for this group
            last_game_id = None
            last_ts = 0
            for gid, info in self.db.get("games", {}).items():
                if info.get("group_id") == group_id:
                    if info.get("timestamp", 0) > last_ts:
                        last_ts = info.get("timestamp", 0)
                        last_game_id = gid
            if last_game_id is None:
                await message.reply("⚠️ هیچ نظرسنجی فعالی در این گروه پیدا نشد.")
                return

            game = self.db["games"][last_game_id]

            # compute per-target all votes and averages
            # target -> [vals...]
            votes = {}
            for from_uid_str, mapping in game.get("ratings", {}).items():
                for target_str, v in mapping.items():
                    votes.setdefault(int(target_str), []).append(int(v))

            # compute average per player and store into users DB
            results = []  # list of (uid, avg, count)
            for uid in game.get("players", []):
                uid = int(uid)
                vals = votes.get(uid, [])
                if not vals:
                    avg = None
                    cnt = 0
                else:
                    avg = sum(vals) / len(vals)
                    cnt = len(vals)

                results.append((uid, avg, cnt))

                # save to users
                user_entry = self.db.setdefault("users", {}).setdefault(str(uid), {"games": {}})
                if avg is not None:
                    user_entry["games"][last_game_id] = avg

            # persist
            self._save()

            # build result text sorted by avg desc (none -> at bottom)
            ranked = sorted(results, key=lambda x: (x[1] is not None, x[1] if x[1] is not None else -1), reverse=True)

            text = "📊 <b>نتایج امتیازدهی:</b>\n\n"
            for pos, (uid, avg, cnt) in enumerate(ranked, start=1):
                name = self.get_display_name(uid)
                if avg is None:
                    text += f"{pos}. {name} — (بدون رأی)\n"
                else:
                    text += f"{pos}. {name} — {avg:.2f} ★ (از {cnt} رأی)\n"

            # add buttons for monthly/top10 and total/top10
            kb = InlineKeyboardMarkup(row_width=1)
            kb.add(InlineKeyboardButton("🏆 امتیازات این ماه", callback_data=f"top_month|{last_game_id}"))
            kb.add(InlineKeyboardButton("🏆 امتیاز کل", callback_data=f"top_total|{last_game_id}"))
            await message.reply(text, reply_markup=kb, parse_mode="HTML")

        # callbacks for top lists
        @self.dp.callback_query_handler(lambda c: c.data and c.data.startswith("top_month|"))
        async def on_top_month(callback: types.CallbackQuery):
            _, game_id = callback.data.split("|", 1)
            await self._send_top_month(callback.message.chat.id, callback)

        @self.dp.callback_query_handler(lambda c: c.data and c.data.startswith("top_total|"))
        async def on_top_total(callback: types.CallbackQuery):
            _, game_id = callback.data.split("|", 1)
            await self._send_top_total(callback.message.chat.id, callback)

        # user stats handler: "امتیاز من" in pv or reply to bot message in group
        @self.dp.message_handler(lambda m: (m.chat.type == "private" and m.text and m.text.strip() == "امتیاز من") or (m.reply_to_message and m.text and m.text.strip() == "امتیاز من"))
        async def on_my_score(message: types.Message):
            # if reply in group to bot message, target may be the user in replied message; otherwise use author
            if message.chat.type == "private":
                uid = message.from_user.id
            else:
                # reply case
                if message.reply_to_message:
                    target = message.reply_to_message.from_user
                    uid = target.id
                else:
                    uid = message.from_user.id

            text = await self._build_user_score_text(uid)
            await message.reply(text, parse_mode="HTML")

    # ---------- utility write/read and ranking ----------
    async def _send_top_month(self, chat_id: int, callback=None):
        # compute for current month (YYYY-MM)
        now = datetime.now()
        ym = f"{now.year}-{now.month:02d}"
        # For each user, collect their games in users[uid]["games"] for which game timestamp month == ym
        scores = []
        for uid_str, user_entry in self.db.get("users", {}).items():
            uid = int(uid_str)
            games_map = user_entry.get("games", {})
            vals = []
            for gid_str, avg in games_map.items():
                game_info = self.db.get("games", {}).get(gid_str)
                if not game_info:
                    continue
                ts = game_info.get("timestamp", 0)
                dt = datetime.fromtimestamp(ts)
                if f"{dt.year}-{dt.month:02d}" == ym:
                    vals.append(float(avg))
            if vals:
                scores.append((uid, sum(vals) / len(vals), len(vals)))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)[:10]

        if not scores:
            text = "ℹ️ در این ماه هنوز امتیازی ثبت نشده."
        else:
            text = "🏆 <b>برترین‌های این ماه</b>\n\n"
            for i, (uid, avg, cnt) in enumerate(scores, start=1):
                text += f"{i}. {self.get_display_name(uid)} — {avg:.2f} ({cnt} بازی)\n"

        if callback:
            await callback.answer()
        await self.bot.send_message(chat_id, text, parse_mode="HTML")

    async def _send_top_total(self, chat_id: int, callback=None):
        scores = []
        for uid_str, user_entry in self.db.get("users", {}).items():
            uid = int(uid_str)
            games_map = user_entry.get("games", {})
            vals = [float(v) for v in games_map.values()] if games_map else []
            if vals:
                scores.append((uid, sum(vals) / len(vals), len(vals)))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)[:10]

        if not scores:
            text = "ℹ️ هنوز امتیازی ثبت نشده."
        else:
            text = "🏆 <b>برترین‌های کل</b>\n\n"
            for i, (uid, avg, cnt) in enumerate(scores, start=1):
                text += f"{i}. {self.get_display_name(uid)} — {avg:.2f} ({cnt} بازی)\n"

        if callback:
            await callback.answer()
        await self.bot.send_message(chat_id, text, parse_mode="HTML")

    async def _build_user_score_text(self, uid: int):
        ue = self.db.get("users", {}).get(str(uid), {})
        games_map = ue.get("games", {})
        if not games_map:
            return "ℹ️ هنوز هیچ امتیازی برای این کاربر ثبت نشده."

        # last game: choose last by game's timestamp
        last_gid = None
        last_ts = 0
        for gid in games_map.keys():
            g = self.db.get("games", {}).get(gid)
            if g and g.get("timestamp", 0) > last_ts:
                last_ts = g.get("timestamp", 0)
                last_gid = gid

        last_game_score = games_map.get(last_gid) if last_gid else None

        # monthly average
        now = datetime.now()
        ym = f"{now.year}-{now.month:02d}"
        month_vals = []
        for gid, avg in games_map.items():
            g = self.db.get("games", {}).get(gid)
            if not g:
                continue
            dt = datetime.fromtimestamp(g.get("timestamp", 0))
            if f"{dt.year}-{dt.month:02d}" == ym:
                month_vals.append(float(avg))
        monthly_avg = sum(month_vals) / len(month_vals) if month_vals else None

        # total avg
        all_vals = [float(v) for v in games_map.values()] if games_map else []
        total_avg = sum(all_vals) / len(all_vals) if all_vals else None

        text = f"📊 امتیازات {self.get_display_name(uid)}:\n\n"
        if last_game_score is not None:
            text += f"🔹 امتیاز آخرین بازی: {float(last_game_score):.2f}\n"
        else:
            text += "🔹 امتیاز آخرین بازی: —\n"
        if monthly_avg is not None:
            text += f"🔸 امتیاز این ماه: {monthly_avg:.2f}\n"
        else:
            text += "🔸 امتیاز این ماه: —\n"
        if total_avg is not None:
            text += f"🏅 امتیاز کل: {total_avg:.2f}\n"
        else:
            text += "🏅 امتیاز کل: —\n"

        return text
