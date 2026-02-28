"""Telegram group parser — extracts members from Telegram groups/channels.

Uses Telethon (Telegram MTProto API) to collect user data
and export it as a pandas DataFrame ready for CRM import.

Usage:
    from crm_audit.integrations import TelegramParser

    parser = TelegramParser(api_id=12345, api_hash="your_hash", phone="+79001234567")
    await parser.connect()

    members = await parser.parse_group("https://t.me/target_group")
    print(f"Collected {len(members)} contacts")

    # Export to CSV for manual import
    members.to_csv("leads.csv", index=False)

    # Or push directly to AmoCRM
    from crm_audit.integrations import AmoCRMClient
    amo = AmoCRMClient(domain="yourcompany", token="xxx")
    amo.push_leads(members, source="telegram:target_group")
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

try:
    from telethon import TelegramClient
    from telethon.tl.functions.channels import GetParticipantsRequest
    from telethon.tl.types import (
        ChannelParticipantsSearch,
        UserStatusOnline,
        UserStatusRecently,
        UserStatusLastWeek,
        UserStatusLastMonth,
    )
except ImportError:
    TelegramClient = None

logger = logging.getLogger(__name__)


class TelegramParser:
    """Parse members from Telegram groups and supergroups.

    Requires a Telegram API application (https://my.telegram.org/apps).
    """

    def __init__(self, api_id: int, api_hash: str, phone: str,
                 session_name: str = "crm_audit_session"):
        if TelegramClient is None:
            raise ImportError(
                "telethon is required: pip install telethon"
            )
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.client = TelegramClient(session_name, api_id, api_hash)

    async def connect(self):
        """Connect and authenticate with Telegram."""
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone)
            code = input("Enter the Telegram verification code: ")
            await self.client.sign_in(self.phone, code)
        logger.info("Connected to Telegram")

    async def disconnect(self):
        """Disconnect from Telegram."""
        await self.client.disconnect()

    async def parse_group(
        self,
        group: str,
        limit: int = 0,
        active_only: bool = False,
        with_phone: bool = False,
    ) -> pd.DataFrame:
        """Parse members from a Telegram group.

        Args:
            group: Group username, link (t.me/...), or numeric ID.
            limit: Max members to fetch. 0 = all available.
            active_only: Keep only users seen within the last month.
            with_phone: Include phone numbers (only visible for mutual contacts).

        Returns:
            DataFrame with columns: user_id, username, first_name, last_name,
            phone (optional), last_seen, bio, is_bot.
        """
        entity = await self.client.get_entity(group)
        logger.info("Parsing group: %s (id=%s)", getattr(entity, "title", group), entity.id)

        rows = []
        offset = 0
        batch_size = 200

        while True:
            participants = await self.client(GetParticipantsRequest(
                channel=entity,
                filter=ChannelParticipantsSearch(""),
                offset=offset,
                limit=batch_size,
                hash=0,
            ))

            if not participants.users:
                break

            for user in participants.users:
                if user.bot:
                    continue

                last_seen = self._resolve_last_seen(user.status)

                if active_only and last_seen is None:
                    continue

                row = {
                    "user_id": user.id,
                    "username": user.username or "",
                    "first_name": user.first_name or "",
                    "last_name": user.last_name or "",
                    "last_seen": last_seen,
                    "is_bot": user.bot,
                }

                if with_phone:
                    row["phone"] = user.phone or ""

                rows.append(row)

            offset += len(participants.users)
            logger.info("Fetched %d members so far...", offset)

            if 0 < limit <= len(rows):
                rows = rows[:limit]
                break

            if len(participants.users) < batch_size:
                break

        df = pd.DataFrame(rows)

        if not df.empty:
            df["parsed_at"] = datetime.now(timezone.utc).isoformat()
            df["source_group"] = str(group)

        logger.info("Parsed %d members from %s", len(df), group)
        return df

    async def get_user_bio(self, user_id: int) -> str:
        """Fetch the bio/about text for a single user."""
        try:
            full = await self.client.get_entity(user_id)
            full_user = await self.client(
                __import__("telethon.tl.functions.users", fromlist=["GetFullUserRequest"])
                .GetFullUserRequest(full)
            )
            return full_user.full_user.about or ""
        except Exception:
            return ""

    async def enrich_with_bios(self, df: pd.DataFrame, delay: float = 1.0) -> pd.DataFrame:
        """Add bio/about text to each row. Throttled to avoid flood waits.

        Args:
            df: DataFrame from parse_group().
            delay: Seconds between API calls (Telegram rate-limits aggressively).

        Returns:
            Same DataFrame with an added 'bio' column.
        """
        bios = []
        for uid in df["user_id"]:
            bio = await self.get_user_bio(uid)
            bios.append(bio)
            await asyncio.sleep(delay)
        df["bio"] = bios
        return df

    @staticmethod
    def _resolve_last_seen(status) -> Optional[str]:
        """Convert Telegram UserStatus to a human-readable string."""
        if isinstance(status, UserStatusOnline):
            return "online"
        if isinstance(status, UserStatusRecently):
            return "recently"
        if isinstance(status, UserStatusLastWeek):
            return "last_week"
        if isinstance(status, UserStatusLastMonth):
            return "last_month"
        if hasattr(status, "was_online"):
            return status.was_online.isoformat()
        return None

    @staticmethod
    def filter_leads(df: pd.DataFrame, has_username: bool = True,
                     seen_since: str = "last_month") -> pd.DataFrame:
        """Filter parsed members to keep the most promising leads.

        Args:
            df: DataFrame from parse_group().
            has_username: Only keep users with a public @username.
            seen_since: Minimum activity level — 'online', 'recently',
                        'last_week', or 'last_month'.

        Returns:
            Filtered DataFrame.
        """
        out = df.copy()

        if has_username:
            out = out[out["username"].astype(bool)]

        activity_order = ["online", "recently", "last_week", "last_month"]
        if seen_since in activity_order:
            cutoff = activity_order.index(seen_since)
            allowed = set(activity_order[: cutoff + 1])
            out = out[out["last_seen"].isin(allowed)]

        return out.reset_index(drop=True)
