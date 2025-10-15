"""Remove legacy messaging conversation participant join table."""

from django.db import migrations


DROP_PARTICIPANTS_TABLE_SQL = """
DROP TABLE IF EXISTS messaging_conversation_participants CASCADE;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_drop_messaging_tables"),
    ]

    operations = [
        migrations.RunSQL(
            sql=DROP_PARTICIPANTS_TABLE_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]

