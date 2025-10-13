from django.db import migrations


DROPS = [
    "DROP TABLE IF EXISTS messaging_message CASCADE",
    "DROP TABLE IF EXISTS messaging_notification CASCADE",
    "DROP TABLE IF EXISTS messaging_conversation CASCADE",
]


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_initial"),
    ]

    operations = [
        migrations.RunSQL("; ".join(DROPS) + ";", reverse_sql=migrations.RunSQL.noop),
    ]
