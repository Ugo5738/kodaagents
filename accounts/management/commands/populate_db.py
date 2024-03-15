from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError

from accounts.factories import OrganizationProfileFactory, UserFactory


class Command(BaseCommand):
    help = "Populates the database with dummy data"

    def handle(self, *args, **options):
        User = get_user_model()

        # Set your custom superuser data
        username = settings.ADMIN_USERNAME
        email = settings.ADMIN_EMAIL
        password = settings.ADMIN_PASSWORD

        try:
            # Attempt to create a new superuser
            User.objects.create_superuser(
                username=username, email=email, password=password
            )
            self.stdout.write(
                self.style.SUCCESS(f"Superuser {username} created successfully")
            )
        except IntegrityError:
            self.stdout.write(
                self.style.WARNING(f"Superuser {username} already exists")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}"))

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
