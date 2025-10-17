import random
import json
import time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# === CONFIGURATION ===
BOT_TOKEN = "8061641659:AAHXE2KQSnhYo8eGrvI6i0UUbg_VoIzo8eE"
COINS_FILE = "coins.json"
USED_FILE = "used_riddles.json"
RIDDLES_FILE = "riddles.json"

# === LOAD / SAVE HELPERS ===
def load_json(filename, default):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

# === DATA ===
coins = load_json(COINS_FILE, {})
used_riddles = load_json(USED_FILE, [])
RIDDLES = load_json(RIDDLES_FILE, [])
current_riddle = {}
wrong_guesses = {}
next_riddle_time = 0

# === FUNCTIONS ===

# send riddle automatically
async def send_riddle(context: ContextTypes.DEFAULT_TYPE):
    global current_riddle, used_riddles, next_riddle_time, wrong_guesses
    group_chats = context.application.chat_data.keys()

    if len(used_riddles) >= len(RIDDLES):
        used_riddles = []
        save_json(USED_FILE, used_riddles)
        print("♻️ All riddles used — resetting list.")

    for chat_id in group_chats:
        if chat_id < 0:
            await new_riddle_for_group(context, chat_id, auto=True)

    next_riddle_time = time.time() + 3600  # 1 hour later


# helper — create new riddle for group
async def new_riddle_for_group(context, chat_id, auto=False):
    global RIDDLES, used_riddles, current_riddle, wrong_guesses

    unused = [r for r in RIDDLES if r["question"] not in used_riddles]
    if not unused:
        used_riddles = []
        unused = RIDDLES

    riddle = random.choice(unused)
    used_riddles.append(riddle["question"])
    save_json(USED_FILE, used_riddles)
    current_riddle[chat_id] = riddle
    wrong_guesses[chat_id] = 0

    await context.bot.send_message(chat_id=chat_id, text=f"🧩 Riddle Time!\n\n{riddle['question']}")
    print(f"🧩 Sent riddle to {chat_id}: {riddle['question']}")

    # Only schedule auto reveal if riddle was sent automatically
    if auto:
        context.job_queue.run_once(reveal_answer, when=300, chat_id=chat_id)


# reveal answer if unsolved
async def reveal_answer(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    if chat_id in current_riddle:
        answer = current_riddle[chat_id]["answer"]
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ Time’s up! The answer was: *{answer}*\nNext riddle coming up...",
            parse_mode="Markdown",
        )
        del current_riddle[chat_id]
        await new_riddle_for_group(context, chat_id, auto=True)


# check answers
async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_riddle, wrong_guesses
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id > 0:
        return  # ignore DMs

    if chat_id in current_riddle:
        answer = current_riddle[chat_id]["answer"].lower().strip()
        guess = update.message.text.lower().strip()

        if answer == guess:
            coins[user.id] = coins.get(user.id, 0) + 10
            save_json(COINS_FILE, coins)
            await update.message.reply_text(f"✅ Correct, {user.first_name}! +10 coins 🎉")
            del current_riddle[chat_id]
            wrong_guesses[chat_id] = 0
        else:
            wrong_guesses[chat_id] = wrong_guesses.get(chat_id, 0) + 1
            if wrong_guesses[chat_id] == 3:
                hint = answer[0].upper() + "*" * (len(answer) - 1)
                await update.message.reply_text(f"💡 Hint: It starts with '{answer[0].upper()}'")
            elif wrong_guesses[chat_id] > 3:
                await update.message.reply_text("❌ Nope! Keep trying!")


# manual riddle command
async def manual_riddle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id > 0:
        await update.message.reply_text("❌ This command only works in groups.")
        return
    await new_riddle_for_group(context, chat_id, auto=False)


# time until next riddle
async def next_riddle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_riddle_time
    remaining = int(next_riddle_time - time.time())
    if remaining <= 0:
        await update.message.reply_text("⏳ The next riddle is about to drop any moment!")
        return
    mins, secs = divmod(remaining, 60)
    await update.message.reply_text(f"🕒 Next riddle in {mins} min {secs} sec.")


# coin system
async def coins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_coins = coins.get(user.id, 0)
    await update.message.reply_text(f"💰 {user.first_name}, you have {user_coins} coins!")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not coins:
        await update.message.reply_text("🏆 No players yet!")
        return
    top_players = sorted(coins.items(), key=lambda x: x[1], reverse=True)[:5]
    board = "🏆 Top Players:\n\n"
    for uid, score in top_players:
        try:
            user = await context.bot.get_chat(uid)
            board += f"{user.first_name}: {score} coins\n"
        except:
            board += f"User {uid}: {score} coins\n"
    await update.message.reply_text(board)


# start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Riddle Bot Activated!\n"
        "🧩 Sends riddles every hour.\n"
        "💬 Use /riddle to get one now.\n"
        "⏳ /next shows when the next drops.\n"
        "💡 3 wrong tries → hint.\n"
        "⏰ 5 minutes no answer → auto reveal (only for scheduled riddles).\n"
        "Earn coins by being right 💰!"
    )

# === MAIN APP ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("coins", coins_command))
app.add_handler(CommandHandler("leaderboard", leaderboard))
app.add_handler(CommandHandler("riddle", manual_riddle))
app.add_handler(CommandHandler("next", next_riddle))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer))

# 🧹 Clear old jobs (prevents duplicate riddles)
app.job_queue.scheduler.remove_all_jobs()

# send riddles every hour
app.job_queue.run_repeating(send_riddle, interval=3600, first=5)

print("✅ Riddle Bot running — stable version (no double posts, no early reveals).")
app.run_polling()
