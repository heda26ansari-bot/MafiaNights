import re

SOURCE = "main1.py"
DEST = "main_fixed.py"

# الگوهای رایج برای پیدا کردن نام‌های اصلی
patterns = [
    # patterns of players.get(uid, ...)
    (r"players\.get\(([^,)]+),\s*['\"]([^'\"]*)['\"]\)", r"get_display_name(\1)"),

    # member.user.full_name
    (r"member\.user\.full_name", r"get_display_name(member.user.id)"),

    # user.full_name
    (r"(\w+)\.full_name", r"get_display_name(\1.id)"),

    # For inline mentions that use plain name variable
    (r"html\.escape\((\w+)\)", r"html.escape(get_display_name(\1_id))"),  # optional fallback
]

# الگوهای replace ساده — جاهایی که name = players.get(...) هست
simple_name_patterns = [
    (r"name\s*=\s*players\.get\(([^,)]+)[^)]*\)", r"name = get_display_name(\1)"),
    (r"player_name\s*=\s*players\.get\(([^,)]+)[^)]*\)", r"player_name = get_display_name(\1)"),
    (r"name\s*=\s*member\.user\.full_name", r"name = get_display_name(member.user.id)"),
]

# الگوی تبدیل mention
mention_pattern = (
    r"f\"<a href='tg://user\?id=\{([^}]+)\}'>\{html\.escape\(([^)]+)\)\}\"",
    r"f\"<a href='tg://user?id={\1}'>{html.escape(get_display_name(\1))}\""
)

print("🔧 شروع اصلاح فایل...")

with open(SOURCE, "r", encoding="utf-8") as f:
    code = f.read()

# مرحله: تبدیل mention
code = re.sub(mention_pattern[0], mention_pattern[1], code)

# مرحله: جایگزینی اصلی
for pat, rep in patterns:
    code = re.sub(pat, rep, code)

# مرحله: جایگزینی ساده نام‌ها
for pat, rep in simple_name_patterns:
    code = re.sub(pat, rep, code)

# جلوگیری از تکرار: اگر get_display_name(get_display_name(uid)) شد
code = re.sub(r"get_display_name\(get_display_name\(([^)]+)\)\)", r"get_display_name(\1)", code)

with open(DEST, "w", encoding="utf-8") as f:
    f.write(code)

print("✅ تمام شد! فایل اصلاح‌شده ساخته شد: main_fixed.py")
