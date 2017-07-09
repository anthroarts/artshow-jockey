from django.db.models.signals import post_migrate


# noinspection PyUnusedLocal
def update_permissions_after_migration(sender, **kwargs):
    """
    Update app permission just after every migration.
    This is based on app django_extensions update_permissions management command.
    """
    from django.conf import settings
    from django.apps import apps
    from django.contrib.auth.management import create_permissions

    create_permissions(sender, apps.get_models(), 2 if settings.DEBUG else 0)


post_migrate.connect(update_permissions_after_migration)
