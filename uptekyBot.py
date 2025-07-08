import sqlite3
import discord  # type: ignore
from discord.ext import commands, tasks  # type: ignore
from datetime import datetime, timedelta

TOKEN = "Token"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


### DATABASE SETUP ###
def setup_db():
    with sqlite3.connect("attendance.db") as conn:
        cursor = conn.cursor()

        # Attendance Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT,
                date TEXT,
                status TEXT
            )
        """)

        # Task Management Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                assigned_by TEXT,
                assigned_to TEXT,
                task_desc TEXT,
                deadline TEXT,
                is_user_done INTEGER DEFAULT 0,
                is_admin_done INTEGER DEFAULT 0
            )
        """)

        # Employee Status Table (Login, Logout, AFK)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_status (
                user_name TEXT PRIMARY KEY,
                status TEXT,
                afk_reason TEXT DEFAULT NULL
            )
        """)

        conn.commit()


setup_db()


### LOGIN & LOGOUT SYSTEM ###
@bot.command()
async def login(ctx):
    user_name = ctx.author.name
    with sqlite3.connect("attendance.db") as conn:
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO employee_status (user_name, status, afk_reason) VALUES (?, ?, NULL)", (user_name, "Logged In"))
        conn.commit()
    await ctx.send(f"✅ {ctx.author.mention} is now **logged in**.")


@bot.command()
async def logout(ctx):
    user_name = ctx.author.name
    with sqlite3.connect("attendance.db") as conn:
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO employee_status (user_name, status, afk_reason) VALUES (?, ?, NULL)", (user_name, "Logged Out"))
        conn.commit()
    await ctx.send(f"✅ {ctx.author.mention} is now **logged out**.")


@bot.command()
async def afk(ctx, *, reason: str):
    user_name = ctx.author.name
    with sqlite3.connect("attendance.db") as conn:
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO employee_status (user_name, status, afk_reason) VALUES (?, ?, ?)", (user_name, "AFK", reason))
        conn.commit()
    await ctx.send(f"🚀 {ctx.author.mention} is **AFK**: {reason}")


@bot.command()
async def status(ctx, member: discord.Member = None):
    user_name = member.name if member else ctx.author.name
    with sqlite3.connect("attendance.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, afk_reason FROM employee_status WHERE user_name = ?", (user_name,))
        record = cursor.fetchone()

    if not record:
        await ctx.send(f"⚠ No status found for {user_name}.")
    else:
        status_message = f"🛠 **{user_name}** is currently **{record[0]}**"
        if record[1]:
            status_message += f" (AFK Reason: {record[1]})"
        await ctx.send(status_message)


### ATTENDANCE SYSTEM ###
@bot.command()
async def mark_attendance(ctx, status: str):
    user_name = ctx.author.name
    today = datetime.today().strftime('%Y-%m-%d')

    if status.lower() not in ["present", "absent"]:
        await ctx.send("❌ Invalid status! Use `present` or `absent`.")
        return

    with sqlite3.connect("attendance.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO attendance (user_name, date, status) VALUES (?, ?, ?)", (user_name, today, status))
        conn.commit()

    await ctx.send(f"✅ Attendance marked as **{status}** for {ctx.author.mention}.")


@bot.command()
async def attendance_report(ctx, member: discord.Member = None):
    user_name = member.name if member else ctx.author.name

    with sqlite3.connect("attendance.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT date, status FROM attendance WHERE user_name = ?", (user_name,))
        records = cursor.fetchall()

    if not records:
        await ctx.send(f"❌ No attendance records found for {user_name}.")
        return

    report = f"📅 **Attendance Report for {user_name}**\n"
    for date, status in records:
        report += f"📍 {date} - {status.capitalize()}\n"

    await ctx.send(report)


### TASK MANAGEMENT ###
@bot.command()
async def assign_task(ctx, member: discord.Member, deadline: str, *, task_desc: str):
    with sqlite3.connect("attendance.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (assigned_by, assigned_to, task_desc, deadline) VALUES (?, ?, ?, ?)",
                       (ctx.author.name, member.name, task_desc, deadline))
        conn.commit()
    await ctx.send(f"✅ Task assigned to {member.mention}: {task_desc} (Deadline: {deadline})")


@bot.command()
async def my_tasks(ctx):
    with sqlite3.connect("attendance.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT task_id, task_desc, deadline, is_user_done, is_admin_done FROM tasks WHERE assigned_to = ?", (ctx.author.name,))
        tasks = cursor.fetchall()

    if not tasks:
        await ctx.send("🎉 You have no pending tasks!")
        return

    response = "**📝 Your Tasks:**\n"
    for task in tasks:
        status = "✅ Completed" if task[3] and task[4] else "⏳ Pending"
        response += f"🔹 Task ID: {task[0]} | {task[1]} | ⏰ {task[2]} | Status: {status}\n"

    await ctx.send(response)


@bot.command()
async def mark_done(ctx, task_id: int):
    with sqlite3.connect("attendance.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET is_user_done = 1 WHERE task_id = ?", (task_id,))
        conn.commit()
    await ctx.send(f"✅ Task {task_id} marked as completed. Awaiting admin approval.")


@bot.command()
async def approve_task(ctx, task_id: int):
    with sqlite3.connect("attendance.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET is_admin_done = 1 WHERE task_id = ?", (task_id,))
        conn.commit()
    await ctx.send(f"✅ Task {task_id} approved by {ctx.author.mention}!")


### RUNNING THE BOT ###
@bot.event
async def on_ready():
    print(f'Employee bot logged in as {bot.user}')

bot.run(TOKEN)
