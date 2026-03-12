"""
Create or update a Django superuser from environment variables.

Used for non-interactive deployments (e.g. Railway). Idempotent: safe to run
on every startup. If the user exists, updates password to match env vars.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Create/update superuser from DJANGO_SUPERUSER_* env vars. "
        "Idempotent; safe to run on every deploy."
    )

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not all([username, email, password]):
            self.stdout.write(
                self.style.WARNING(
                    "Skipping ensure_superuser: set DJANGO_SUPERUSER_USERNAME, "
                    "DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD to create a superuser."
                )
            )
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created superuser '{username}'."))
        else:
            user.email = email
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Updated superuser '{username}'."))
