# Ladybot

Telegram group manager bot with invite tracking, anti-link moderation, and
forward-info inspection for private chats.

## Features

- Invite/add tracking with leaderboard.
- Per-event history logging (join/leave, invite, ban/unban).
- Anti-link moderation for non-admins.
- Admin-only commands in groups with private DM responses.
- Forwarded-message inspection in private chats.

## Commands

- `/start` (private only): onboarding message.
- `/stats` (admin only): invite leaderboard. In groups, results are sent via DM.
- `/chat_id` (admin only): sends group chat ID via DM when used in groups.
- `/history` (admin only, DM): recent event history for a chat.

## Environment

- `BOT_TOKEN` (required): Telegram bot token.
- `ALLOWED_CHAT_IDS` (optional): comma-separated list of allowed chat IDs.
  Example: `-1003577925363,-1002200706225`
- `DB_PATH` (optional): SQLite path, default `bot.db`.

## Local setup

1. Create `.env` with your `BOT_TOKEN` and optional settings.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the bot:

```bash
python bot.py
```

## Database

The bot uses SQLite.

### `invites`

Stores invite counts per user per chat.

Columns:
- `user_id`
- `chat_id`
- `count`

### `invite_events`

Stores per-event history.

Columns:
- `id`
- `chat_id`
- `event_type` (`join_invite`, `join_added`, `join_unknown`, `leave_left`,
  `leave_removed`, `ban`, `unban`)
- `actor_id` (who performed the action when known)
- `target_id` (user affected by the action)
- `invite_creator_id`
- `invite_link`
- `created_at` (UTC ISO8601)

## Notes

- Admin DMs only work after the admin has started the bot in private at least once.
- If `ALLOWED_CHAT_IDS` is set, the bot ignores all other chats.
