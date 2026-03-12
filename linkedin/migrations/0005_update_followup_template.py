"""Patch old followup templates to include no-signature instruction."""

import hashlib
from pathlib import Path

from django.db import migrations

# SHA-256 of the old followup2.j2 (before the no-signature fix).
OLD_TEMPLATE_HASH = "e9f7073d2406ba9dd74de75fe3d2225fea37ecb6efe860843a0755017431911c"

ROOT = Path(__file__).resolve().parent.parent.parent
NEW_TEMPLATE_PATH = ROOT / "assets" / "templates" / "prompts" / "followup2.j2"
# Fallback when /app/assets is a volume that overwrites image content (Railway).
BACKUP_TEMPLATE_PATH = ROOT / "assets_templates_backup" / "prompts" / "followup2.j2"


def _get_template_path():
    """Return path to followup2.j2, using backup if main path missing (volume mount)."""
    return NEW_TEMPLATE_PATH if NEW_TEMPLATE_PATH.exists() else BACKUP_TEMPLATE_PATH


def forwards(apps, schema_editor):
    Campaign = apps.get_model("linkedin", "Campaign")
    template_path = _get_template_path()
    new_content = template_path.read_text()

    for campaign in Campaign.objects.all():
        h = hashlib.sha256(campaign.followup_template.encode()).hexdigest()
        if h == OLD_TEMPLATE_HASH:
            campaign.followup_template = new_content
            campaign.save(update_fields=["followup_template"])


class Migration(migrations.Migration):
    dependencies = [
        ("linkedin", "0004_rename_is_promo_to_is_partner"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
