class BaseRouter:
    """
    A router to control all database operations on models for all apps to the 'default' database.
    """

    def db_for_read(self, model, **hints):
        """
        All models are read from the 'default' database.
        """
        return "default"

    def db_for_write(self, model, **hints):
        """
        All models are written to the 'default' database.
        """
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations between objects in different apps.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure that all models are migrated to the 'default'.
        """
        return db == "default"
