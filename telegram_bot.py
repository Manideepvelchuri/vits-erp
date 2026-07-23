import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import sqlite3
import os
import toml
import logging
import html

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VITS_ERP_Bot")

# Load configuration and secrets
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECRETS_PATH = os.path.join(BASE_DIR, ".streamlit", "secrets.toml")

# Read token
token = ""
if os.path.exists(SECRETS_PATH):
    try:
        secrets = toml.load(SECRETS_PATH)
        token = secrets.get("telegram", {}).get("bot_token", "")
    except Exception as e:
        logger.error(f"Error loading secrets: {e}")

# If token is empty/placeholder, log warning
if not token or token == "YOUR_TELEGRAM_BOT_TOKEN":
    logger.warning("No valid Telegram bot token found in .streamlit/secrets.toml. "
                   "Please update secrets.toml with your token to start the bot.")
    # Initialize with dummy token to avoid startup crash if user hasn't set it yet
    token = "DUMMY_TOKEN_PLEASE_REPLACE"

bot = telebot.TeleBot(token)

# Setup telegram chats table in a local SQLite database specifically for bot state
# (This avoids SQL syntax/dialect incompatibilities with production PostgreSQL/Supabase)
def get_bot_db_conn():
    conn = sqlite3.connect(os.path.join(BASE_DIR, "telegram_chats.db"))
    conn.row_factory = sqlite3.Row
    return conn

def init_bot_db():
    try:
        conn = get_bot_db_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS telegram_chats (
                chat_id INTEGER PRIMARY KEY,
                roll_no TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing Telegram chat table: {e}")

# Helper to escape HTML tags
def escape_html(val):
    if val is None:
        return ""
    return html.escape(str(val))

# Database helper functions
def get_student_by_roll(roll_no):
    from database import get_db_connection
    conn = get_db_connection()
    student = conn.execute("""
        SELECT name, department, section, semester, branch FROM students WHERE roll_no=?
    """, (roll_no,)).fetchone()
    conn.close()
    return student

def get_chat_roll(chat_id):
    conn = get_bot_db_conn()
    row = conn.execute("SELECT roll_no FROM telegram_chats WHERE chat_id=?", (chat_id,)).fetchone()
    conn.close()
    return row['roll_no'] if row else None

def save_chat_roll(chat_id, roll_no):
    conn = get_bot_db_conn()
    conn.execute("INSERT OR REPLACE INTO telegram_chats (chat_id, roll_no) VALUES (?, ?)", (chat_id, roll_no))
    conn.commit()
    conn.close()

def delete_chat_roll(chat_id):
    conn = get_bot_db_conn()
    conn.execute("DELETE FROM telegram_chats WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()


# KPI and Calculations
def calculate_skips(attended, conducted):
    # Overall attendance target thresholds
    if conducted == 0:
        return 0, 0
        
    pct = (attended / conducted) * 100
    
    # How many classes can be missed to stay above 75%
    if pct >= 75:
        can_miss = 0
        temp_att = attended
        temp_cond = conducted
        while True:
            temp_cond += 1
            if (temp_att / temp_cond) * 100 >= 75:
                can_miss += 1
            else:
                break
        return can_miss, 0
    # How many classes must be attended continuously to reach 75%
    else:
        needed = 0
        temp_att = attended
        temp_cond = conducted
        while (temp_att / temp_cond) * 100 < 75:
            temp_att += 1
            temp_cond += 1
            needed += 1
        return 0, needed

# Menus and Keyboards
def get_main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("📊 Quick Summary"), KeyboardButton("📚 Subject Details"))
    markup.row(KeyboardButton("🔮 Skip Predictor"), KeyboardButton("👤 My Profile"))
    markup.row(KeyboardButton("🔄 Change Roll Number"))
    return markup

def get_stats_inline_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📊 Summary", callback_data="show_summary"),
        InlineKeyboardButton("📚 Subjects", callback_data="show_subjects")
    )
    markup.row(
        InlineKeyboardButton("🔮 Skip Projections", callback_data="show_predictor"),
        InlineKeyboardButton("🎓 CGPA/Grades", callback_data="show_cgpa")
    )
    markup.row(
        InlineKeyboardButton("👤 My Profile", callback_data="show_profile")
    )
    return markup

# Bot command handlers
@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    chat_id = message.chat.id
    roll_no = get_chat_roll(chat_id)
    
    welcome_text = (
        "👋 <b>Welcome to the VITS Student ERP Assistant Bot!</b>\n\n"
        "This bot provides <i>live, up-to-date</i> query access to student attendance metrics and academic statistics.\n\n"
    )
    
    if roll_no:
        student = get_student_by_roll(roll_no)
        if student:
            name = escape_html(student['name'])
            dept = escape_html(student['department'])
            sec = escape_html(student['section'])
            welcome_text += (
                f"Logged in as: <b>{name}</b> ({escape_html(roll_no)})\n"
                f"Class: <b>{dept} - {sec}</b>\n\n"
                "Use the menu below to query your stats instantly."
            )
            bot.send_message(chat_id, welcome_text, parse_mode="HTML", reply_markup=get_main_keyboard())
            return
            
    welcome_text += "Please send your <b>Roll Number</b> (e.g. <code>25891A04C9</code> or <code>24891A0465</code>) to get started."
    # Remove keyboard if not logged in
    bot.send_message(chat_id, welcome_text, parse_mode="HTML", reply_markup=telebot.types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda msg: msg.text == "📊 Quick Summary")
def handler_summary(message):
    show_summary_view(message.chat.id, message.message_id, edit=False)

@bot.message_handler(func=lambda msg: msg.text == "📚 Subject Details")
def handler_subjects(message):
    show_subjects_view(message.chat.id, message.message_id, edit=False)

@bot.message_handler(func=lambda msg: msg.text == "🔮 Skip Predictor")
def handler_predictor(message):
    show_predictor_view(message.chat.id, message.message_id, edit=False)

@bot.message_handler(func=lambda msg: msg.text == "👤 My Profile")
def handler_profile(message):
    show_profile_view(message.chat.id, message.message_id, edit=False)

@bot.message_handler(func=lambda msg: msg.text == "🔄 Change Roll Number")
def handler_change_roll(message):
    chat_id = message.chat.id
    delete_chat_roll(chat_id)
    bot.send_message(
        chat_id, 
        "🔄 Roll number removed. Please type your new <b>Roll Number</b> to register.", 
        parse_mode="HTML",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )

# Roll Number Ingestion
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip().upper()
    
    # Check if text looks like a roll number
    if len(text) >= 8 and any(char.isdigit() for char in text):
        student = get_student_by_roll(text)
        if student:
            save_chat_roll(chat_id, text)
            name = escape_html(student['name'])
            branch = escape_html(student['branch'])
            sec = escape_html(student['section'])
            bot.send_message(
                chat_id,
                f"✅ <b>Registration Successful!</b>\n\n"
                f"Student: <b>{name}</b>\n"
                f"Branch: <b>{branch}</b> | Section: <b>{sec}</b>\n\n"
                "You can now query your attendance summary below.",
                parse_mode="HTML",
                reply_markup=get_main_keyboard()
            )
            # Show summary automatically
            show_summary_view(chat_id, None, edit=False)
        else:
            bot.send_message(chat_id, "❌ Roll number not found in database. Please check and try again.")
    else:
        bot.send_message(chat_id, "ℹ️ Please select a menu option or reply with a valid Roll Number.")

# Inline Button Callback Handler
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if call.data == "show_summary":
        show_summary_view(chat_id, message_id, edit=True)
    elif call.data == "show_subjects":
        show_subjects_view(chat_id, message_id, edit=True)
    elif call.data == "show_predictor":
        show_predictor_view(chat_id, message_id, edit=True)
    elif call.data == "show_cgpa":
        show_cgpa_view(chat_id, message_id, edit=True)
    elif call.data == "show_profile":
        show_profile_view(chat_id, message_id, edit=True)
        
    bot.answer_callback_query(call.id)

# ─── Data Views ───

def show_summary_view(chat_id, message_id, edit=False):
    roll_no = get_chat_roll(chat_id)
    if not roll_no:
        bot.send_message(chat_id, "❌ Please enter your Roll Number first.")
        return
        
    student = get_student_by_roll(roll_no)
    if not student:
        return
        
    from database import get_db_connection, compute_cgpa
    conn = get_db_connection()
    
    # Query Attendance Summary
    att_rows = conn.execute("""
        SELECT hours_attended, hours_conducted FROM attendance WHERE roll_no=? AND semester='Sem 2'
    """, (roll_no,)).fetchall()
    
    total_att = sum(r['hours_attended'] or 0 for r in att_rows)
    total_cond = sum(r['hours_conducted'] or 0 for r in att_rows)
    overall = round((total_att / total_cond * 100), 1) if total_cond else 0.0
    
    cgpa = compute_cgpa(roll_no, conn)
    
    conn.close()
    
    # Format Text
    status_icon = "🟢" if overall >= 75 else ("🟡" if overall >= 65 else "🔴")
    status_text = "Safe Zone" if overall >= 75 else ("Risk Zone (Need Condonation)" if overall >= 65 else "Debarred Zone")
    
    name = escape_html(student['name'])
    dept = escape_html(student['department'])
    sec = escape_html(student['section'])
    sem = escape_html(student['semester'])
    
    msg_text = (
        f"📊 <b>Attendance &amp; Statistics Summary</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Student:</b> {name}\n"
        f"🆔 <b>Roll No:</b> <code>{escape_html(roll_no)}</code>\n"
        f"🏫 <b>Class:</b> {dept} - {sec}\n"
        f"🎓 <b>Active Sem:</b> {sem}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📈 <b>Overall Attendance:</b> <b>{overall}%</b>\n"
        f"⏱️ <b>Hours:</b> {total_att} attended / {total_cond} conducted\n"
        f"🚨 <b>Status:</b> {status_icon} <b>{status_text}</b>\n\n"
        f"⭐️ <b>CGPA:</b> <b>{f'{cgpa:.2f}' if cgpa > 0 else 'Pending/Fail'}</b>\n"
        f"🕒 <b>Query Time:</b> {logging.Formatter().formatTime(logging.LogRecord('','','','','','',''), '%H:%M:%S')}\n"
    )
    
    send_or_edit(chat_id, message_id, msg_text, get_stats_inline_keyboard(), edit)

def show_subjects_view(chat_id, message_id, edit=False):
    roll_no = get_chat_roll(chat_id)
    if not roll_no: return
    
    student = get_student_by_roll(roll_no)
    if not student: return
    
    from database import get_db_connection
    conn = get_db_connection()
    att_rows = conn.execute("""
        SELECT subject, hours_attended, hours_conducted FROM attendance WHERE roll_no=? AND semester='Sem 2'
    """, (roll_no,)).fetchall()
    conn.close()
    
    msg_text = (
        f"📚 <b>Subject-wise Attendance Details</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Roll No: <code>{escape_html(roll_no)}</code>\n"
        f"Semester: Sem 2\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    if not att_rows:
        msg_text += "<i>No attendance data logged for current subjects.</i>"
    else:
        for r in sorted(att_rows, key=lambda x: (x['hours_attended']/(x['hours_conducted'] or 1)), reverse=False):
            sub = r['subject']
            att = r['hours_attended'] or 0
            cond = r['hours_conducted'] or 0
            pct = round((att / cond * 100), 1) if cond else 0.0
            
            indicator = "🟢" if pct >= 75 else ("🟡" if pct >= 65 else "🔴")
            # Truncate subject name
            short_sub = sub[:22] + "..." if len(sub) > 22 else sub
            
            msg_text += f"{indicator} <b>{escape_html(short_sub)}</b>\n"
            msg_text += f"    └─ <i>{pct}%</i>  ({att}/{cond} hrs conducted)\n\n"
            
    send_or_edit(chat_id, message_id, msg_text, get_stats_inline_keyboard(), edit)

def show_predictor_view(chat_id, message_id, edit=False):
    roll_no = get_chat_roll(chat_id)
    if not roll_no: return
    
    from database import get_db_connection
    conn = get_db_connection()
    att_rows = conn.execute("""
        SELECT hours_attended, hours_conducted FROM attendance WHERE roll_no=? AND semester='Sem 2'
    """, (roll_no,)).fetchall()
    conn.close()
    
    total_att = sum(r['hours_attended'] or 0 for r in att_rows)
    total_cond = sum(r['hours_conducted'] or 0 for r in att_rows)
    overall = round((total_att / total_cond * 100), 1) if total_cond else 0.0
    
    msg_text = (
        f"🔮 <b>Attendance Skip Predictor Projections</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Current overall attendance: <b>{overall}%</b> ({total_att}/{total_cond} hrs)\n"
        f"Target Threshold: <b>75.0%</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    if total_cond == 0:
        msg_text += "<i>No conducting data present.</i>"
    else:
        can_miss, need = calculate_skips(total_att, total_cond)
        
        # Estimate daily averages (usually 7 periods a day)
        avg_classes = 7.0
        
        if overall >= 75:
            days = round(can_miss / avg_classes, 1)
            msg_text += (
                f"🟢 <b>Safe Zone Analysis:</b>\n"
                f"• You can miss <b>{can_miss} hours</b> of classes continuously without falling below the 75% target threshold.\n"
                f"• This is equivalent to approximately <b>{days} days</b> of absence.\n"
            )
        else:
            days = round(need / avg_classes, 1)
            msg_text += (
                f"🔴 <b>Risk/Debarred Zone Analysis:</b>\n"
                f"• You need to attend <b>{need} consecutive hours</b> of classes without skipping to recover your attendance to 75.0%.\n"
                f"• This is equivalent to approximately <b>{days} days</b> of full attendance.\n"
            )
            
    send_or_edit(chat_id, message_id, msg_text, get_stats_inline_keyboard(), edit)

def show_cgpa_view(chat_id, message_id, edit=False):
    roll_no = get_chat_roll(chat_id)
    if not roll_no: return
    
    from database import get_db_connection
    conn = get_db_connection()
    sgpa_rows = conn.execute("""
        SELECT semester, sgpa, failed FROM sgpa_records WHERE roll_no=? ORDER BY semester
    """, (roll_no,)).fetchall()
    
    backlogs = conn.execute("""
        SELECT subject, score, grade_point, exam_type FROM marks
        WHERE roll_no=? AND grade_point=0.0 AND exam_type LIKE '%Final Examinations'
    """, (roll_no,)).fetchall()
    
    conn.close()
    
    msg_text = (
        f"🎓 <b>Academic Grades &amp; CGPA Record</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Roll No: <code>{escape_html(roll_no)}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    msg_text += "<b>Semester Performance:</b>\n"
    if not sgpa_rows:
        msg_text += "• <i>No SGPA details posted yet.</i>\n\n"
    else:
        for r in sgpa_rows:
            sem = r['semester']
            gpa = r['sgpa'] or 0.0
            status = "🔴 FAIL" if r['failed'] else "🟢 PASS"
            msg_text += f"• <b>{escape_html(sem)}:</b> GPA: <code>{gpa:.2f}</code> ({status})\n"
        msg_text += "\n"
        
    msg_text += "<b>Active Backlogs Summary:</b>\n"
    if not backlogs:
        msg_text += "• ✅ <b>Zero active backlogs! All subjects passed.</b>\n"
    else:
        msg_text += f"• ⚠️ <b>{len(backlogs)} active backlog(s) found:</b>\n"
        for b in backlogs:
            msg_text += f"  └─ {escape_html(b['subject'])} (GP: {b['grade_point']})\n"
            
    send_or_edit(chat_id, message_id, msg_text, get_stats_inline_keyboard(), edit)

def show_profile_view(chat_id, message_id, edit=False):
    roll_no = get_chat_roll(chat_id)
    if not roll_no:
        bot.send_message(chat_id, "❌ Please enter your Roll Number first.")
        return
        
    from database import get_db_connection
    conn = get_db_connection()
    row = conn.execute("""
        SELECT name, department, section, semester, branch, email, phone, parent_phone 
        FROM students WHERE roll_no=?
    """, (roll_no,)).fetchone()
    conn.close()
    
    if not row:
        bot.send_message(chat_id, "❌ Student record not found.")
        return
        
    name = escape_html(row['name'])
    dept = escape_html(row['department'])
    sec = escape_html(row['section'])
    sem = escape_html(row['semester'])
    br = escape_html(row['branch'])
    email = escape_html(row['email'])
    phone = escape_html(row['phone'])
    parent_phone = escape_html(row['parent_phone'])
    
    msg_text = (
        f"👤 <b>Student Profile Details</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Name:</b> {name}\n"
        f"🆔 <b>Roll No:</b> <code>{escape_html(roll_no)}</code>\n"
        f"🏫 <b>Class:</b> {dept} - {sec}\n"
        f"🎓 <b>Semester:</b> Sem {sem} ({br})\n"
        f"📧 <b>Email:</b> {email or '<i>Not Set</i>'}\n"
        f"📞 <b>Phone:</b> {phone or '<i>Not Set</i>'}\n"
        f"👨‍👩‍👦 <b>Parent Phone:</b> {parent_phone or '<i>Not Set</i>'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )
    
    send_or_edit(chat_id, message_id, msg_text, get_stats_inline_keyboard(), edit)

OFFLINE_MODE = False

def send_or_edit(chat_id, message_id, text, keyboard, edit=False):
    if OFFLINE_MODE:
        # Clean HTML formatting slightly for clean terminal printout
        clean_text = (
            text.replace("<b>", "")
                .replace("</b>", "")
                .replace("<i>", "")
                .replace("</i>", "")
                .replace("<code>", "'")
                .replace("</code>", "'")
                .replace("&amp;", "&")
        )
        print("\n" + "="*40)
        print(clean_text)
        print("="*40)
        return
        
    try:
        if edit and message_id:
            bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=keyboard)
        else:
            bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)

def run_offline_simulator():
    global OFFLINE_MODE
    OFFLINE_MODE = True
    
    print("\n" + "="*55)
    print("  VITS ERP BOT - OFFLINE LOCAL TERMINAL SIMULATOR")
    print("="*55)
    print("[Offline Mode: Running local test with live vits_erp.db data]")
    print("[No internet connection or Telegram token required]\n")
    
    chat_id = 99999  # Mock chat ID for local simulation
    
    # Show welcome prompt
    roll = get_chat_roll(chat_id)
    print("Bot: 👋 Welcome to the VITS Student ERP Assistant!")
    if roll:
        student = get_student_by_roll(roll)
        if student:
            print(f"     Registered as: {student['name']} ({roll})")
            print(f"     Class: {student['department']} - {student['section']}")
    else:
        print("     Please reply with a Roll Number to register and query attendance.")
        
    while True:
        roll = get_chat_roll(chat_id)
        if roll:
            print("\n" + "-"*40)
            print("📊 Menu Options:")
            print(" [1] Quick Summary")
            print(" [2] Subject Details")
            print(" [3] Skip Predictor")
            print(" [4] My Profile")
            print(" [5] CGPA & Grades")
            print(" [6] Logout / Change Roll Number")
            print(" [0] Exit Simulator")
            try:
                choice = input(f"\nSelect option for {roll}: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting simulator.")
                break
        else:
            try:
                choice = input("\nEnter Roll Number (or '0' to exit): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting simulator.")
                break
                
        if not choice:
            continue
            
        if choice == '0':
            print("Exiting simulator.")
            break
            
        if not roll:
            # Attempt to register
            roll_upper = choice.upper()
            student = get_student_by_roll(roll_upper)
            if student:
                save_chat_roll(chat_id, roll_upper)
                print(f"\nBot: ✅ Registration Successful!")
                print(f"     Student: {student['name']}")
                print(f"     Section: {student['section']}")
                show_summary_view(chat_id, None, edit=False)
            else:
                print("\nBot: ❌ Roll number not found in database. Please check and try again.")
        else:
            if choice == '1':
                show_summary_view(chat_id, None, edit=False)
            elif choice == '2':
                show_subjects_view(chat_id, None, edit=False)
            elif choice == '3':
                show_predictor_view(chat_id, None, edit=False)
            elif choice == '4':
                show_profile_view(chat_id, None, edit=False)
            elif choice == '5':
                show_cgpa_view(chat_id, None, edit=False)
            elif choice == '6':
                delete_chat_roll(chat_id)
                print("\nBot: 🔄 Roll number removed. Register again with another Roll Number.")
            elif len(choice) >= 8 and any(c.isdigit() for c in choice):
                # Allow switching directly
                roll_upper = choice.upper()
                student = get_student_by_roll(roll_upper)
                if student:
                    save_chat_roll(chat_id, roll_upper)
                    print(f"\nBot: ✅ Switched Registration!")
                    print(f"     Student: {student['name']}")
                    show_summary_view(chat_id, None, edit=False)
                else:
                    print("\nBot: ❌ Roll number not found.")
            else:
                print("\nBot: ℹ️ Invalid menu choice. Please select 1-6 or 0.")

if __name__ == "__main__":
    init_bot_db()
    
    # Check if we should run in offline simulator mode
    is_dummy_token = (
        not token or 
        token == "YOUR_TELEGRAM_BOT_TOKEN" or 
        token == "DUMMY_TOKEN_PLEASE_REPLACE" or 
        "DUMMY" in token
    )
    
    if is_dummy_token:
        run_offline_simulator()
    else:
        logger.info("VITS ERP Telegram Bot started polling...")
        try:
            bot.infinity_polling()
        except Exception as e:
            logger.error(f"Critical error in bot polling: {e}")
            logger.info("Falling back to local terminal simulator...")
            run_offline_simulator()
