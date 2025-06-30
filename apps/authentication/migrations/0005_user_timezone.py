from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0004_user_is_us_certified"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="timezone",
            field=models.CharField(
                max_length=50,
                default="UTC",
                verbose_name="timezone",
                help_text="Preferred IANA timezone name for this user (e.g. 'Europe/Paris').",
            ),
        ),
    ]
