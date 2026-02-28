"""AmoCRM integration — push parsed leads into AmoCRM as contacts + leads.

Uses AmoCRM REST API v4.
Docs: https://www.amocrm.ru/developers/content/crm_platform/leads-api

Usage:
    from crm_audit.integrations import AmoCRMClient

    amo = AmoCRMClient(
        domain="yourcompany",       # yourcompany.amocrm.ru
        access_token="long_lived_token",
    )

    # Push a DataFrame of parsed Telegram members
    result = amo.push_leads(members_df, source="telegram:target_group")
    print(f"Created {result['leads_created']} leads, {result['contacts_created']} contacts")
"""

import logging
import time
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

AMOCRM_API = "https://{domain}.amocrm.ru/api/v4"


class AmoCRMClient:
    """Lightweight client for AmoCRM REST API v4."""

    def __init__(self, domain: str, access_token: str):
        self.base_url = AMOCRM_API.format(domain=domain)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        })

    # ------------------------------------------------------------------
    # Low-level API helpers
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an API request with basic retry logic."""
        url = f"{self.base_url}{path}"
        for attempt in range(4):
            resp = self.session.request(method, url, **kwargs)
            if resp.status_code == 429:
                wait = 2 ** attempt
                logger.warning("Rate limited, retrying in %ds...", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            if resp.status_code == 204:
                return {}
            return resp.json()
        resp.raise_for_status()
        return {}

    def get(self, path: str, **kwargs) -> dict:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> dict:
        return self._request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs) -> dict:
        return self._request("PATCH", path, **kwargs)

    # ------------------------------------------------------------------
    # Contacts
    # ------------------------------------------------------------------

    def create_contacts(self, contacts: list[dict]) -> list[dict]:
        """Create contacts in bulk (max 250 per request).

        Each dict should have keys: first_name, last_name, and optionally
        custom_fields_values with phone/email/etc.

        Returns list of created contact stubs with 'id'.
        """
        results = []
        for batch_start in range(0, len(contacts), 250):
            batch = contacts[batch_start : batch_start + 250]
            resp = self.post("/contacts", json=batch)
            created = resp.get("_embedded", {}).get("contacts", [])
            results.extend(created)
            logger.info("Created %d contacts (batch at offset %d)", len(created), batch_start)
        return results

    def find_contact_by_query(self, query: str) -> Optional[dict]:
        """Search for an existing contact by name, phone, or email."""
        resp = self.get("/contacts", params={"query": query, "limit": 1})
        contacts = resp.get("_embedded", {}).get("contacts", [])
        return contacts[0] if contacts else None

    # ------------------------------------------------------------------
    # Leads
    # ------------------------------------------------------------------

    def create_leads(self, leads: list[dict]) -> list[dict]:
        """Create leads in bulk (max 250 per request).

        Each dict should have: name, price (optional), _embedded.contacts (optional).
        """
        results = []
        for batch_start in range(0, len(leads), 250):
            batch = leads[batch_start : batch_start + 250]
            resp = self.post("/leads", json=batch)
            created = resp.get("_embedded", {}).get("leads", [])
            results.extend(created)
            logger.info("Created %d leads (batch at offset %d)", len(created), batch_start)
        return results

    # ------------------------------------------------------------------
    # Pipelines (for assigning leads to a specific pipeline/stage)
    # ------------------------------------------------------------------

    def get_pipelines(self) -> list[dict]:
        """List all pipelines with their statuses."""
        resp = self.get("/leads/pipelines")
        return resp.get("_embedded", {}).get("pipelines", [])

    # ------------------------------------------------------------------
    # High-level: push parsed Telegram leads into AmoCRM
    # ------------------------------------------------------------------

    def push_leads(
        self,
        df: pd.DataFrame,
        source: str = "telegram",
        pipeline_id: int = None,
        status_id: int = None,
        responsible_user_id: int = None,
        skip_existing: bool = True,
        tags: list[str] = None,
    ) -> dict:
        """Convert a DataFrame of parsed Telegram members into AmoCRM contacts + leads.

        Args:
            df: DataFrame from TelegramParser.parse_group().
                Expected columns: username, first_name, last_name, source_group.
            source: Tag or note describing lead origin.
            pipeline_id: Target pipeline ID (uses default if None).
            status_id: Target pipeline status/stage ID.
            responsible_user_id: Assign to a specific user.
            skip_existing: Skip contacts that already exist (matched by username).
            tags: Extra tags to attach to leads.

        Returns:
            Dict with counts: contacts_created, leads_created, skipped.
        """
        tags = tags or []
        tags.append(source)

        contacts_payload = []
        lead_names = []
        skipped = 0

        for _, row in df.iterrows():
            username = row.get("username", "")
            first_name = row.get("first_name", "")
            last_name = row.get("last_name", "")
            full_name = f"{first_name} {last_name}".strip() or username

            # Check for existing contact
            if skip_existing and username:
                existing = self.find_contact_by_query(username)
                if existing:
                    skipped += 1
                    continue

            contact = {
                "first_name": first_name or username,
                "last_name": last_name,
                "custom_fields_values": [],
            }

            # Add Telegram username as a custom field
            if username:
                contact["custom_fields_values"].append({
                    "field_code": "IM",
                    "values": [{"value": f"@{username}", "enum_code": "TELEGRAM"}],
                })

            # Add phone if available
            phone = row.get("phone", "")
            if phone:
                contact["custom_fields_values"].append({
                    "field_code": "PHONE",
                    "values": [{"value": phone}],
                })

            contacts_payload.append(contact)
            lead_names.append(full_name)

        # Create contacts in AmoCRM
        created_contacts = self.create_contacts(contacts_payload) if contacts_payload else []

        # Create a lead for each contact
        leads_payload = []
        for i, contact_stub in enumerate(created_contacts):
            lead = {
                "name": f"TG Lead: {lead_names[i]}",
                "_embedded": {
                    "contacts": [{"id": contact_stub["id"]}],
                    "tags": [{"name": t} for t in tags],
                },
            }
            if pipeline_id:
                lead["pipeline_id"] = pipeline_id
            if status_id:
                lead["status_id"] = status_id
            if responsible_user_id:
                lead["responsible_user_id"] = responsible_user_id
            leads_payload.append(lead)

        created_leads = self.create_leads(leads_payload) if leads_payload else []

        result = {
            "contacts_created": len(created_contacts),
            "leads_created": len(created_leads),
            "skipped": skipped,
            "total_processed": len(df),
        }
        logger.info("Push complete: %s", result)
        return result

    def export_for_import(self, df: pd.DataFrame, output_path: str = "amocrm_import.csv"):
        """Export parsed DataFrame to CSV formatted for AmoCRM manual import.

        Useful if you prefer to import via AmoCRM UI instead of API.
        """
        export = pd.DataFrame({
            "Имя": df.get("first_name", ""),
            "Фамилия": df.get("last_name", ""),
            "Телефон": df.get("phone", ""),
            "Telegram": df.get("username", "").apply(lambda u: f"@{u}" if u else ""),
            "Примечание": df.get("source_group", "").apply(lambda g: f"Из группы: {g}"),
            "Теги": "telegram,parsed",
        })
        export.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info("Exported %d rows to %s", len(export), output_path)
        return output_path
