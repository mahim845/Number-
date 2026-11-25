import telebot
import requests
import sqlite3
import re
import html
import time
import threading

from telebot import types
from datetime import datetime
from zoneinfo import ZoneInfo

# =====================================================
#              BLACK MATRIX TRIBUNAL
#                   CONFIGURATION
# =====================================================

BOT_TOKEN = "9066168112:AAFXQOmka1lhaqbC9HtvzZyXNUnyzumuuY8"

ADMIN_ID = 7276206449

API_URL = "https://gajarbotol.site/apis/unknown.php"

FORCE_JOIN_CHANNEL = "@bmt_coder_team"
CHANNEL_LINK = "https://t.me/bmt_coder_team"

DATABASE = "bmt_database.db"

API_TIMEOUT = 15

TIMEZONE = ZoneInfo("Asia/Dhaka")

DAILY_LIMIT = 50

# =====================================================
#                    BOT SETUP
# =====================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    threaded=True,
    num_threads=8
)

db_lock = threading.RLock()

session = requests.Session()

# =====================================================
#                    PREMIUM STYLE
# =====================================================

class Font:

    TOP = "╔════════════════════════════╗"
    MID = "╠════════════════════════════╣"
    BOT = "╚════════════════════════════╝"

    LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    DOT = "▰▱▰▱▰▱▰▱▰▱▰▱▰▱▰▱"

    BRAND = "𝐁𝐋𝐀𝐂𝐊 𝐌𝐀𝐓𝐑𝐈𝐗 𝐓𝐑𝐈𝐁𝐔𝐍𝐀𝐋"

    FOOTER = (
        "\n▰▱▰▱▰▱▰▱▰▱▰▱\n"
        "⚡ <b>BLACK MATRIX TRIBUNAL</b>"
    )


def header(title):

    return (
        f"{Font.TOP}\n"
        f"║  ✦ {title} ✦\n"
        f"{Font.BOT}\n"
    )


def footer():

    return Font.FOOTER


def now():

    return datetime.now(TIMEZONE)


def timestamp():

    return now().strftime("%Y-%m-%d %H:%M:%S")


def safe(value):

    return html.escape(str(value))


# =====================================================
#                    DATABASE
# =====================================================

def connect_db():

    conn = sqlite3.connect(
        DATABASE,
        timeout=20
    )

    conn.execute("PRAGMA busy_timeout=20000")

    return conn


def init_db():

    with db_lock:

        conn = connect_db()

        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                join_date TEXT,
                is_banned INTEGER DEFAULT 0
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS admins(
                user_id INTEGER PRIMARY KEY
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS search_history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                number TEXT,
                timestamp TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS usage(
                user_id INTEGER,
                search_date TEXT,
                total INTEGER DEFAULT 0,
                PRIMARY KEY(user_id, search_date)
            )
        """)

        c.execute("""
            INSERT OR IGNORE INTO admins(user_id)
            VALUES(?)
        """, (ADMIN_ID,))

        conn.commit()
        conn.close()


init_db()


# =====================================================
#                    DATABASE HELPERS
# =====================================================

def add_user(user):

    with db_lock:

        conn = connect_db()

        conn.execute("""
            INSERT OR IGNORE INTO users
            (user_id, first_name, username, join_date)
            VALUES(?,?,?,?)
        """, (
            user.id,
            user.first_name or "User",
            user.username or "N/A",
            timestamp()
        ))

        conn.execute("""
            UPDATE users
            SET first_name=?, username=?
            WHERE user_id=?
        """, (
            user.first_name or "User",
            user.username or "N/A",
            user.id
        ))

        conn.commit()
        conn.close()


def is_admin(uid):

    with db_lock:

        conn = connect_db()

        row = conn.execute(
            "SELECT 1 FROM admins WHERE user_id=?",
            (uid,)
        ).fetchone()

        conn.close()

    return row is not None


def is_banned(uid):

    with db_lock:

        conn = connect_db()

        row = conn.execute(
            "SELECT is_banned FROM users WHERE user_id=?",
            (uid,)
        ).fetchone()

        conn.close()

    return bool(row and row[0] == 1)


def save_history(uid, number):

    masked = mask_number(number)

    with db_lock:

        conn = connect_db()

        conn.execute("""
            INSERT INTO search_history
            (user_id, number, timestamp)
            VALUES(?,?,?)
        """, (
            uid,
            masked,
            timestamp()
        ))

        conn.commit()
        conn.close()


def increase_usage(uid):

    today = now().strftime("%Y-%m-%d")

    with db_lock:

        conn = connect_db()

        conn.execute("""
            INSERT INTO usage
            (user_id, search_date, total)
            VALUES(?,?,1)

            ON CONFLICT(user_id, search_date)
            DO UPDATE SET total=total+1
        """, (uid, today))

        conn.commit()
        conn.close()


def get_usage(uid):

    today = now().strftime("%Y-%m-%d")

    with db_lock:

        conn = connect_db()

        row = conn.execute("""
            SELECT total FROM usage
            WHERE user_id=? AND search_date=?
        """, (uid, today)).fetchone()

        conn.close()

    return row[0] if row else 0


def get_stats():

    today = now().strftime("%Y-%m-%d")

    with db_lock:

        conn = connect_db()

        c = conn.cursor()

        total_users = c.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        total_searches = c.execute(
            "SELECT COUNT(*) FROM search_history"
        ).fetchone()[0]

        banned = c.execute(
            "SELECT COUNT(*) FROM users WHERE is_banned=1"
        ).fetchone()[0]

        admins = c.execute(
            "SELECT COUNT(*) FROM admins"
        ).fetchone()[0]

        today_users = c.execute("""
            SELECT COUNT(*) FROM users
            WHERE substr(join_date,1,10)=?
        """, (today,)).fetchone()[0]

        today_searches = c.execute("""
            SELECT COUNT(*) FROM search_history
            WHERE substr(timestamp,1,10)=?
        """, (today,)).fetchone()[0]

        conn.close()

    return (
        total_users,
        total_searches,
        banned,
        admins,
        today_users,
        today_searches
    )


# =====================================================
#                    NUMBER HELPERS
# =====================================================

def normalize_number(value):

    value = re.sub(
        r"[\s()+.-]",
        "",
        str(value)
    )

    if not value.isdigit():
        return None

    if not 7 <= len(value) <= 15:
        return None

    # Bangladesh local format to international format
    if len(value) == 11 and value.startswith("01"):

        value = "88" + value

    elif len(value) == 10 and value.startswith("1"):

        value = "880" + value

    return value


def mask_number(number):

    if len(number) < 7:
        return "*" * len(number)

    return (
        number[:4]
        + "*" * (len(number) - 7)
        + number[-3:]
    )


# =====================================================
#                    API CLEANER
# =====================================================

def clean_api_text(value):

    if not value:
        return "Unknown"

    value = str(value)

    value = re.sub(
        r"\s*\(@num_1nfo_bd_bot\)",
        "",
        value,
        flags=re.IGNORECASE
    )

    return value.strip()


def fetch_api(number):

    try:

        response = session.get(
            API_URL,
            params={"number": number},
            timeout=API_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            return None

        if data.get("success") is not True:
            return None

        return data

    except requests.exceptions.Timeout:

        print("API Timeout")
        return None

    except requests.exceptions.RequestException as e:

        print("API Error:", type(e).__name__)
        return None

    except ValueError:

        print("Invalid JSON")
        return None


# =====================================================
#                    RESULT FORMAT
# =====================================================

def format_response(data):

    if not data:
        return "❌ No information found."

    fields = [
        ("name","👤 Name"),
        ("number", "📞 NUMBER"),
        ("international_format", "🌐 INTERNATIONAL"),
        ("country", "🌍 COUNTRY"),
        ("carrier", "📡 CARRIER"),
        ("type", "📱 TYPE"),
        ("timestamp", "🕐 TIME")
    ]

    lines = []

    for key, label in fields:

        value = data.get(key)

        if value is None or value == "":
            continue

        if key == "carrier":

            value = clean_api_text(value)

        value = safe(value)

        lines.append(
            f"┃ {label} : <code>{value}</code>"
        )

    if not lines:

        return "❌ No valid information found."

    return (
        "╔════════════════════════════╗\n"
        "║     ✦ 𝐁𝐌𝐓 𝐍𝐔𝐌𝐁𝐄𝐑 𝐈𝐍𝐅𝐎 ✦\n"
        "╠════════════════════════════╣\n"
        + "\n".join(lines)
        + "\n╚════════════════════════════╝\n"
        + footer()
    )


# =====================================================
#                    FORCE JOIN
# =====================================================

def is_joined(uid):

    if not FORCE_JOIN_CHANNEL:
        return True

    try:

        member = bot.get_chat_member(
            FORCE_JOIN_CHANNEL,
            uid
        )

        return member.status in (
            "member",
            "administrator",
            "creator"
        )

    except Exception:

        return False


def join_keyboard():

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "📢 𝐉𝐎𝐈𝐍 𝐂𝐇𝐀𝐍𝐍𝐄𝐋",
            url=CHANNEL_LINK
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "✅ 𝐕𝐄𝐑𝐈𝐅𝐘",
            callback_data="bmt_verify"
        )
    )

    return markup


def require_join(message):

    if is_joined(message.from_user.id):
        return True

    bot.send_message(
        message.chat.id,
        header("𝐅𝐎𝐑𝐂𝐄 𝐉𝐎𝐈𝐍")
        + "\n🔒 Access পেতে প্রথমে Channel Join করুন।",
        reply_markup=join_keyboard()
    )

    return False


# =====================================================
#                    MAIN MENU
# =====================================================

def main_menu(uid):

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2
    )

    markup.add(
        "🔍 𝐒𝐄𝐀𝐑𝐂𝐇 𝐍𝐔𝐌𝐁𝐄𝐑",
        "📊 𝐌𝐘 𝐒𝐓𝐀𝐓𝐒"
    )

    markup.add(
        "📜 𝐇𝐈𝐒𝐓𝐎𝐑𝐘",
        "ℹ️ 𝐇𝐄𝐋𝐏"
    )

    markup.add(
        "📢 𝐔𝐏𝐃𝐀𝐓𝐄 𝐂𝐇𝐀𝐍𝐍𝐄𝐋"
    )

    if is_admin(uid):

        markup.add(
            "👑 𝐁𝐌𝐓 𝐀𝐃𝐌𝐈𝐍"
        )

    return markup


# =====================================================
#                    START
# =====================================================

@bot.message_handler(commands=["start"])
def start(message):

    user = message.from_user

    add_user(user)

    if is_banned(user.id):

        bot.send_message(
            message.chat.id,
            "🚫 Access Denied."
        )

        return

    if not require_join(message):
        return

    text = f"""
✨ <b>WELCOME TO BMT</b> ✨

╔════════════════════════════╗
║   𝐁𝐋𝐀𝐂𝐊 𝐌𝐀𝐓𝐑𝐈𝐗 𝐓𝐑𝐈𝐁𝐔𝐍𝐀𝐋
╠════════════════════════════╣
┃ ⚡ Premium Number Service
┃ 🔍 Number Information
┃ 🛡️ Secure Interface
╚════════════════════════════╝

{Font.DOT}

👇 Select an option below.
"""

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML",
        reply_markup=main_menu(user.id)
    )


# =====================================================
#                    VERIFY
# =====================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "bmt_verify"
)
def verify(call):

    uid = call.from_user.id

    if is_joined(uid):

        bot.answer_callback_query(
            call.id,
            "✅ Verified!"
        )

        add_user(call.from_user)

        try:

            bot.delete_message(
                call.message.chat.id,
                call.message.message_id
            )

        except Exception:
            pass

        bot.send_message(
            call.message.chat.id,
            "⚡ BMT ACCESS GRANTED",
            reply_markup=main_menu(uid)
        )

    else:

        bot.answer_callback_query(
            call.id,
            "❌ Join first!",
            show_alert=True
        )


# =====================================================
#                    SEARCH BUTTON
# =====================================================

@bot.message_handler(
    func=lambda m: m.text == "🔍 𝐒𝐄𝐀𝐑𝐂𝐇 𝐍𝐔𝐌𝐁𝐄𝐑"
)
def search_button(message):

    if is_banned(message.from_user.id):
        return

    if not require_join(message):
        return

    bot.send_message(
        message.chat.id,
        header("𝐍𝐔𝐌𝐁𝐄𝐑 𝐒𝐄𝐀𝐑𝐂𝐇")
        + "\n📞 Send a valid number.\n"
        "Example: <code>018XXXXXXXX</code>",
        parse_mode="HTML"
    )


# =====================================================
#                    NUMBER SEARCH
# =====================================================

@bot.message_handler(
    func=lambda m:
        bool(m.text)
        and not m.text.startswith("/")
        and m.text not in [
            "🔍 𝐒𝐄𝐀𝐑𝐂𝐇 𝐍𝐔𝐌𝐁𝐄𝐑",
            "📊 𝐌𝐘 𝐒𝐓𝐀𝐓𝐒",
            "📜 𝐇𝐈𝐒𝐓𝐎𝐑𝐘",
            "ℹ️ 𝐇𝐄𝐋𝐏",
            "📢 𝐔𝐏𝐃𝐀𝐓𝐄 𝐂𝐇𝐀𝐍𝐍𝐄𝐋",
            "👑 𝐁𝐌𝐓 𝐀𝐃𝐌𝐈𝐍"
        ]
)
def number_search(message):

    uid = message.from_user.id

    if is_banned(uid):
        return

    if not require_join(message):
        return

    number = normalize_number(message.text)

    if not number:

        bot.reply_to(
            message,
            "❌ Invalid Number Format!"
        )

        return

    if not is_admin(uid):

        if get_usage(uid) >= DAILY_LIMIT:

            bot.reply_to(
                message,
                "⚠️ Daily Search Limit Reached!"
            )

            return

    loading = bot.reply_to(
        message,
        "⏳ <b>BMT Searching...</b>",
        parse_mode="HTML"
    )

    data = fetch_api(number)

    if data:

        result = format_response(data)

        save_history(uid, number)
        increase_usage(uid)

        bot.edit_message_text(
            result,
            message.chat.id,
            loading.message_id,
            parse_mode="HTML"
        )

    else:

        bot.edit_message_text(
            "❌ API Error or No Demo Information Found.",
            message.chat.id,
            loading.message_id
        )


# =====================================================
#                    MY HISTORY
# =====================================================

@bot.message_handler(
    func=lambda m: m.text == "📜 𝐇𝐈𝐒𝐓𝐎𝐑𝐘"
)
def history(message):

    uid = message.from_user.id

    if is_banned(uid):
        return

    with db_lock:

        conn = connect_db()

        rows = conn.execute("""
            SELECT number, timestamp
            FROM search_history
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT 10
        """, (uid,)).fetchall()

        conn.close()

    if not rows:

        bot.send_message(
            message.chat.id,
            "📭 No History Found."
        )

        return

    text = header("𝐒𝐄𝐀𝐑𝐂𝐇 𝐇𝐈𝐒𝐓𝐎𝐑𝐘")

    for i, row in enumerate(rows, 1):

        text += (
            f"\n{i}. 📞 <code>{safe(row[0])}</code>\n"
            f"   🕐 {safe(row[1])}\n"
        )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML"
    )


# =====================================================
#                    MY STATS
# =====================================================

@bot.message_handler(
    func=lambda m: m.text == "📊 𝐌𝐘 𝐒𝐓𝐀𝐓𝐒"
)
def my_stats(message):

    uid = message.from_user.id

    with db_lock:

        conn = connect_db()

        searches = conn.execute("""
            SELECT COUNT(*) FROM search_history
            WHERE user_id=?
        """, (uid,)).fetchone()[0]

        joined = conn.execute("""
            SELECT join_date FROM users
            WHERE user_id=?
        """, (uid,)).fetchone()

        conn.close()

    text = f"""
╔════════════════════════════╗
║       📊 𝐌𝐘 𝐒𝐓𝐀𝐓𝐒
╠════════════════════════════╣
┃ 👤 User ID : <code>{uid}</code>
┃ 🔍 Searches : <code>{searches}</code>
┃ 📅 Today : <code>{get_usage(uid)}</code>
┃ 🗓 Joined : <code>{safe(joined[0] if joined else 'N/A')}</code>
╚════════════════════════════╝
"""

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML"
    )


# =====================================================
#                    HELP
# =====================================================

@bot.message_handler(
    func=lambda m: m.text == "ℹ️ 𝐇𝐄𝐋𝐏"
)
def help_message(message):

    text = """
╔════════════════════════════╗
║          ℹ️ 𝐇𝐄𝐋𝐏
╚════════════════════════════╝

📌 HOW TO USE

┃ 1. Search Number নির্বাচন করুন
┃ 2. Valid Number পাঠান
┃ 3. API Information দেখুন

🛡️ Face any problem inbox @Unkonwn_BMT.
"""

    bot.send_message(
        message.chat.id,
        text
    )


# =====================================================
#                    CHANNEL
# =====================================================

@bot.message_handler(
    func=lambda m: m.text == "📢 𝐔𝐏𝐃𝐀𝐓𝐄 𝐂𝐇𝐀𝐍𝐍𝐄𝐋"
)
def channel(message):

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "📢 JOIN BMT CHANNEL",
            url=CHANNEL_LINK
        )
    )

    bot.send_message(
        message.chat.id,
        "⚡ Follow BLACK MATRIX TRIBUNAL",
        reply_markup=markup
    )


# =====================================================
#                    ADMIN PANEL
# =====================================================

@bot.message_handler(commands=["admin"])
@bot.message_handler(
    func=lambda m: m.text == "👑 𝐁𝐌𝐓 𝐀𝐃𝐌𝐈𝐍"
)
def admin_panel(message):

    if not is_admin(message.from_user.id):
        return

    stats = get_stats()

    markup = types.InlineKeyboardMarkup(row_width=2)

    buttons = [
        ("📊 𝐒𝐓𝐀𝐓𝐒", "adm_stats"),
        ("📢 𝐁𝐑𝐎𝐀𝐃𝐂𝐀𝐒𝐓", "adm_broadcast"),
        ("👥 𝐔𝐒𝐄𝐑𝐒", "adm_users"),
        ("📜 𝐇𝐈𝐒𝐓𝐎𝐑𝐘", "adm_history"),
        ("👑 𝐀𝐃𝐌𝐈𝐍𝐒", "adm_admins"),
        ("🚫 𝐁𝐀𝐍𝐍𝐄𝐃", "adm_banned"),
        ("⚙️ 𝐂𝐎𝐍𝐅𝐈𝐆", "adm_config")
    ]

    for label, callback in buttons:

        markup.add(
            types.InlineKeyboardButton(
                label,
                callback_data=callback
            )
        )

    text = f"""
╔════════════════════════════╗
║       👑 𝐁𝐌𝐓 𝐀𝐃𝐌𝐈𝐍
╠════════════════════════════╣
┃ 👥 Users : <code>{stats[0]}</code>
┃ 🔍 Searches : <code>{stats[1]}</code>
┃ 🚫 Banned : <code>{stats[2]}</code>
┃ 👑 Admins : <code>{stats[3]}</code>
┃ 🆕 Today Users : <code>{stats[4]}</code>
┃ 📅 Today Searches : <code>{stats[5]}</code>
╚════════════════════════════╝
"""

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML",
        reply_markup=markup
    )


# =====================================================
#                    ADMIN CALLBACKS
# =====================================================

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("adm_")
)
def admin_callback(call):

    if not is_admin(call.from_user.id):

        bot.answer_callback_query(
            call.id,
            "Access Denied!",
            show_alert=True
        )

        return

    action = call.data[4:]

    bot.answer_callback_query(call.id)

    if action == "stats":

        s = get_stats()

        text = (
            "📊 <b>BMT STATISTICS</b>\n\n"
            f"Users: <code>{s[0]}</code>\n"
            f"Searches: <code>{s[1]}</code>\n"
            f"Banned: <code>{s[2]}</code>\n"
            f"Admins: <code>{s[3]}</code>\n"
            f"Today Users: <code>{s[4]}</code>\n"
            f"Today Searches: <code>{s[5]}</code>"
        )

        bot.send_message(
            call.message.chat.id,
            text,
            parse_mode="HTML"
        )

    elif action == "broadcast":

        msg = bot.send_message(
            call.message.chat.id,
            "📢 Broadcast Message পাঠান।\n"
            "Cancel: /cancel"
        )

        bot.register_next_step_handler(
            msg,
            do_broadcast
        )

    elif action == "users":

        with db_lock:

            conn = connect_db()

            rows = conn.execute("""
                SELECT user_id, first_name,
                username, is_banned
                FROM users
                ORDER BY join_date DESC
                LIMIT 20
            """).fetchall()

            conn.close()

        text = "👥 <b>RECENT USERS</b>\n\n"

        for r in rows:

            status = "🚫" if r[3] else "✅"

            text += (
                f"{status} <code>{r[0]}</code>\n"
                f"Name: {safe(r[1])}\n"
                f"Username: {safe(r[2])}\n\n"
            )

        bot.send_message(
            call.message.chat.id,
            text,
            parse_mode="HTML"
        )

    elif action == "history":

        with db_lock:

            conn = connect_db()

            rows = conn.execute("""
                SELECT user_id, number, timestamp
                FROM search_history
                ORDER BY id DESC
                LIMIT 20
            """).fetchall()

            conn.close()

        text = "📜 <b>RECENT HISTORY</b>\n\n"

        for r in rows:

            text += (
                f"User: <code>{r[0]}</code>\n"
                f"Number: <code>{safe(r[1])}</code>\n"
                f"Time: {safe(r[2])}\n\n"
            )

        bot.send_message(
            call.message.chat.id,
            text,
            parse_mode="HTML"
        )

    elif action == "admins":

        with db_lock:

            conn = connect_db()

            rows = conn.execute(
                "SELECT user_id FROM admins"
            ).fetchall()

            conn.close()

        text = "👑 <b>ADMIN LIST</b>\n\n"

        for r in rows:
            text += f"<code>{r[0]}</code>\n"

        text += (
            "\n/addadmin USER_ID"
            "\n/deladmin USER_ID"
        )

        bot.send_message(
            call.message.chat.id,
            text,
            parse_mode="HTML"
        )

    elif action == "banned":

        with db_lock:

            conn = connect_db()

            rows = conn.execute("""
                SELECT user_id, first_name
                FROM users WHERE is_banned=1
            """).fetchall()

            conn.close()

        text = "🚫 <b>BANNED USERS</b>\n\n"

        for r in rows:

            text += (
                f"<code>{r[0]}</code> "
                f"{safe(r[1])}\n"
            )

        bot.send_message(
            call.message.chat.id,
            text,
            parse_mode="HTML"
        )

    elif action == "config":

        bot.send_message(
            call.message.chat.id,
            "⚙️ <b>BMT CONFIGURATION</b>\n"
            "API: gajarbotol.site\n"
            f"Channel: {safe(FORCE_JOIN_CHANNEL)}",
            parse_mode="HTML"
        )


# =====================================================
#                    BROADCAST
# =====================================================

def do_broadcast(message):

    if not is_admin(message.from_user.id):
        return

    if message.text and message.text.strip() == "/cancel":

        bot.reply_to(
            message,
            "❌ Broadcast Cancelled."
        )

        return

    with db_lock:

        conn = connect_db()

        users = conn.execute("""
            SELECT user_id FROM users
            WHERE is_banned=0
        """).fetchall()

        conn.close()

    status = bot.reply_to(
        message,
        "📤 Broadcasting..."
    )

    sent = 0
    failed = 0

    for user in users:

        try:

            bot.copy_message(
                user[0],
                message.chat.id,
                message.message_id
            )

            sent += 1

        except Exception:

            failed += 1

        time.sleep(0.05)

    bot.edit_message_text(
        f"""
✅ <b>BROADCAST COMPLETED</b>

┃ Sent: <code>{sent}</code>
┃ Failed: <code>{failed}</code>
┃ Total: <code>{len(users)}</code>
""",
        message.chat.id,
        status.message_id,
        parse_mode="HTML"
    )


# =====================================================
#                    ADMIN COMMANDS
# =====================================================

@bot.message_handler(commands=["addadmin"])
def add_admin(message):

    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2:
        bot.reply_to(message, "Usage: /addadmin USER_ID")
        return

    try:

        uid = int(parts[1])

        with db_lock:

            conn = connect_db()

            conn.execute(
                "INSERT INTO admins(user_id) VALUES(?)",
                (uid,)
            )

            conn.commit()
            conn.close()

        bot.reply_to(
            message,
            f"✅ Admin Added: {uid}"
        )

    except sqlite3.IntegrityError:

        bot.reply_to(
            message,
            "⚠️ Already Admin."
        )

    except ValueError:

        bot.reply_to(
            message,
            "Invalid User ID."
        )


@bot.message_handler(commands=["deladmin"])
def del_admin(message):

    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2:
        bot.reply_to(message, "Usage: /deladmin USER_ID")
        return

    try:

        uid = int(parts[1])

        if uid == ADMIN_ID:

            bot.reply_to(
                message,
                "❌ Main Admin cannot be removed."
            )

            return

        with db_lock:

            conn = connect_db()

            conn.execute(
                "DELETE FROM admins WHERE user_id=?",
                (uid,)
            )

            conn.commit()
            conn.close()

        bot.reply_to(
            message,
            f"✅ Admin Removed: {uid}"
        )

    except ValueError:

        bot.reply_to(
            message,
            "Invalid User ID."
        )


@bot.message_handler(commands=["ban"])
def ban_user(message):

    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2:
        bot.reply_to(message, "Usage: /ban USER_ID")
        return

    try:

        uid = int(parts[1])

        with db_lock:

            conn = connect_db()

            conn.execute(
                "UPDATE users SET is_banned=1 WHERE user_id=?",
                (uid,)
            )

            conn.commit()
            conn.close()

        bot.reply_to(
            message,
            f"🚫 User Banned: {uid}"
        )

    except ValueError:

        bot.reply_to(
            message,
            "Invalid User ID."
        )


@bot.message_handler(commands=["unban"])
def unban_user(message):

    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2:
        bot.reply_to(message, "Usage: /unban USER_ID")
        return

    try:

        uid = int(parts[1])

        with db_lock:

            conn = connect_db()

            conn.execute(
                "UPDATE users SET is_banned=0 WHERE user_id=?",
                (uid,)
            )

            conn.commit()
            conn.close()

        bot.reply_to(
            message,
            f"✅ User Unbanned: {uid}"
        )

    except ValueError:

        bot.reply_to(
            message,
            "Invalid User ID."
        )


# =====================================================
#                    CANCEL
# =====================================================

@bot.message_handler(commands=["cancel"])
def cancel(message):

    bot.reply_to(
        message,
        "❌ Operation Cancelled.",
        reply_markup=main_menu(message.from_user.id)
    )


# =====================================================
#                    UNKNOWN
# =====================================================

@bot.message_handler(
    content_types=["text"],
    func=lambda m: True
)
def unknown(message):

    if is_banned(message.from_user.id):
        return

    if not require_join(message):
        return

    bot.send_message(
        message.chat.id,
        "❓ Unknown Command.\n"
        "Use BMT Menu.",
        reply_markup=main_menu(message.from_user.id)
    )


# =====================================================
#                    RUN BOT
# =====================================================

if __name__ == "__main__":

    print(Font.LINE)
    print("BLACK MATRIX TRIBUNAL")
    print("BMT TELEGRAM BOT")
    print("POLLING STARTED")
    print(Font.LINE)

    while True:

        try:

            bot.infinity_polling(
                skip_pending=True,
                timeout=30,
                long_polling_timeout=30
            )

        except KeyboardInterrupt:

            print("Bot Stopped.")
            break

        except Exception as error:

            print(
                "Polling Error:",
                type(error).__name__
            )

            time.sleep(5)
