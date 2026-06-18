    except ValueError:
        return await message.reply("❌ Invalid User ID. Please enter a valid number.")

    user = await db.get_user(user_id)
    if not user:
        return await message.reply("⚠️ User not found in database.")

    username = user.get("username")
    username_display = f"@{username}" if username else "N/A"

    last_date = user.get("last_date", "N/A")
    expiry_time = user.get("expiry_time")

    if isinstance(last_date, datetime):
        last_date = last_date.strftime("%Y-%m-%d")

    # -------- STATUS CHECK --------
    is_premium = await db.has_premium_access(user_id)
    is_verified = await db.is_user_verified(user_id)

    # -------- LIMIT LOGIC --------
    if is_premium:
        daily_limit = PREMIUM_DAILY_LIMIT
        subscription_type = "Paid"
    elif is_verified:
        daily_limit = VERIFICATION_DAILY_LIMIT
        subscription_type = "Verified"
    else:
        daily_limit = DAILY_LIMIT
        subscription_type = "Free"

    used = await db.get_video_count(user_id)
    remaining = max(daily_limit - used, 0)

    # -------- EXPIRY FORMAT --------
    if isinstance(expiry_time, datetime):
        try:
            if expiry_time.tzinfo is None:
                expiry_time = pytz.utc.localize(expiry_time)

            expiry_dt = expiry_time.astimezone(pytz.timezone("Asia/Kolkata"))
            expiry_date = expiry_dt.strftime('%d-%m-%Y')
            expiry_clock = expiry_dt.strftime('%I:%M:%S %p')
        except Exception:
            expiry_date = "Error"
            expiry_clock = "Error"
    else:
        expiry_date = "N/A"
        expiry_clock = "N/A"

    # -------- SAME STYLE TEXT --------
    text = f"""**👤 User Info**

🆔 User ID: `{user_id}`
📛 Username: {username_display}
📆 Last Active: `{last_date}`

**📦 Plan Details**
💠 Subscription: `{subscription_type}`
📁 Daily Limit: `{daily_limit} Files`
📤 Files Used: `{used}/{daily_limit}`
🟢 Remaining: `{remaining} Files`
"""

    if is_premium:
        text += f"""**💎 Premium Info**
📅 Expiry Date: `{expiry_date}`
⏰ Expiry Time: `{expiry_clock}`
"""

    await message.reply(text)
