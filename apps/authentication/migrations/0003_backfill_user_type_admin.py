from django.db import migrations


def set_admin_user_type(apps, schema_editor):
    User = apps.get_model("authentication", "User")
    User.objects.filter(is_superuser=True).exclude(user_type="admin").update(
        user_type="admin"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0002_user_user_name_trgm"),
    ]

    operations = [
        migrations.RunPython(set_admin_user_type, migrations.RunPython.noop),
    ]
