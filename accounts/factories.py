import factory
from django.utils import timezone

from accounts.models import OrganizationProfile, User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.LazyAttribute(
        lambda a: f"{a.first_name.lower()}{a.last_name.lower()}"
    )
    phone = factory.Faker("phone_number")

    # email = factory.Sequence(lambda n: f"user{n}@example.com")
    # Using LazyAttribute to generate email based on first_name and last_name
    email = factory.LazyAttribute(
        lambda a: f"{a.first_name.lower()}.{a.last_name.lower()}{timezone.now().strftime('%Y%m%d%H%M%S%f')}@example.com"
    )

    date_of_birth = factory.Faker("date_of_birth")
    email_verified = True


class OrganizationProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrganizationProfile

    user = factory.SubFactory(UserFactory)
    name = factory.Faker("company")
    bio = factory.Faker("text", max_nb_chars=500)
    city = factory.Faker("city")
    address = factory.Faker("street_address")
    address2 = factory.Faker("secondary_address")
    country = factory.Faker("country_code")
    zip_code = factory.Faker("zipcode")
