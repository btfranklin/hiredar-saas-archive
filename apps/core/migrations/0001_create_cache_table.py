from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    """Ensure the django_cache table exists for DatabaseCache backend."""
    # ``createcachetable`` is idempotent; safe to run multiple times.
    call_command("createcachetable", "django_cache", verbosity=0)


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(create_cache_table, migrations.RunPython.noop),
    ]
