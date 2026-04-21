import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from recommender.engine import SubscriptionRecommender


BOT_TOKEN = os.getenv("BOT_TOKEN")

# Initialize recommender
rec = SubscriptionRecommender(csv_path="data/subscriptions.csv", region="IN")

# User state
USER_STATE = {}

# Domains
DOMAINS = ["ott", "music", "tools"]

# Features
FEATURES = {
    "ott": ["no-ads", "hd", "4k", "sports", "downloads", "kids"],
    "music": ["ad-free", "offline", "lyrics", "podcasts", "family-plan"],
    "tools": ["templates", "editor", "background-removal", "team", "brand-kit"],
}

# 🔁 Start Again Button
def get_start_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Start Again", callback_data="restart")]
    ])

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    USER_STATE[uid] = {
        "domain": None,
        "budget": None,
        "features": []
    }

    buttons = [
        [InlineKeyboardButton(d.upper(), callback_data=f"domain:{d}")]
        for d in DOMAINS
    ]

    await update.message.reply_text(
        "Welcome! Choose a domain:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ---------------- BUTTON HANDLER ----------------
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    data = query.data

    print("CLICKED:", data)  # debug

    # 🔁 RESTART
    if data == "restart":
        USER_STATE[uid] = {
            "domain": None,
            "budget": None,
            "features": []
        }

        buttons = [
            [InlineKeyboardButton(d.upper(), callback_data=f"domain:{d}")]
            for d in DOMAINS
        ]

        await query.message.reply_text(
            "🔄 Restarted! Choose a domain:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # DOMAIN SELECT
    if data.startswith("domain:"):
        domain = data.split(":")[1]
        USER_STATE[uid]["domain"] = domain

        await query.edit_message_text(
            f"Selected domain: {domain.upper()}\n\n"
            "Now send your monthly budget in ₹ (e.g., 299)."
        )
        return

    # FEATURE TOGGLE
    if data.startswith("feature:"):
        feature = data.split(":")[1]
        st = USER_STATE.get(uid, {})
        feats = set(st.get("features", []))

        if feature in feats:
            feats.remove(feature)
        else:
            feats.add(feature)

        USER_STATE[uid]["features"] = list(feats)

        domain = st.get("domain")

        buttons = [
            [InlineKeyboardButton(("✅ " if f in feats else "") + f,
                                  callback_data=f"feature:{f}")]
            for f in FEATURES.get(domain, [])
        ]

        buttons.append([InlineKeyboardButton("Done", callback_data="feature_done")])

        await query.edit_message_text(
            "Select features (toggle):",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # DONE → SHOW RESULTS
    if data == "feature_done":
        await query.edit_message_text("Fetching recommendations...")

        st = USER_STATE.get(uid, {})
        results = rec.recommend(
            st["domain"],
            st["budget"],
            st["features"],
            top_k=5
        )

        if not results:
            await query.message.reply_text(
                "No matches found. Try again.",
                reply_markup=get_start_button()
            )
            return

        text = "\n\n".join([
            f"• {r['name']} — ₹{r['price_month']}/month (⭐ {r['rating']})\n"
            f"{r['reason']}\n"
            f"{r['url']}"
            for r in results
        ])

        await query.message.reply_text(
            text,
            reply_markup=get_start_button()
        )
        return

# ---------------- MESSAGE HANDLER ----------------
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    st = USER_STATE.get(uid)

    if not st:
        await update.message.reply_text("Use /start to begin.")
        return

    # Expect budget
    if st["budget"] is None:
        try:
            st["budget"] = int(update.message.text.strip())
        except:
            await update.message.reply_text("Please send a valid number (e.g., 299).")
            return

        domain = st["domain"]

        buttons = [
            [InlineKeyboardButton(f, callback_data=f"feature:{f}")]
            for f in FEATURES.get(domain, [])
        ]

        buttons.append([InlineKeyboardButton("Done", callback_data="feature_done")])

        await update.message.reply_text(
            "Select features (you can toggle multiple):",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    print("Bot running...")
    app.run_polling()

# ---------------- RUN ----------------
if __name__ == "__main__":
    main()
