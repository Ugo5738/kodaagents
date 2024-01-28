from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.factories import OrganizationProfileFactory, UserFactory


class Command(BaseCommand):
    help = "Populates the database with dummy data"

    def handle(self, *args, **options):
        User = get_user_model()

        # Set your custom superuser data
        username = settings.USERNAME
        email = settings.EMAIL
        password = settings.PASSWORD

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username, email=email, password=password
            )
            self.stdout.write(
                self.style.SUCCESS(f"Superuser {username} created successfully")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"Superuser {username} already exists")
            )

        # Create Users
        for _ in range(10):
            UserFactory.create()

        # Create Organization Profiles
        for _ in range(5):
            OrganizationProfileFactory.create()

        # ... create other objects

        self.stdout.write(
            self.style.SUCCESS("Successfully populated the database with dummy data")
        )
