from dateutil.parser import parse


class DateValidator:
    """Utility class for date validation."""

    @staticmethod
    def is_valid_date(string):
        try:
            parse(string, fuzzy=True)
            return True
        except ValueError:
            return False
