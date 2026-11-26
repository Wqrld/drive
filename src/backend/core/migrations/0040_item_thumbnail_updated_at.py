from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0039_item_created_at_idx'),
    ]

    operations = [
        # Fork only: office releases before v1.1.1 added this column as 0031, which
        # clusters upgraded from them still have, so it is only created when missing.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='item',
                    name='thumbnail_updated_at',
                    field=models.DateTimeField(blank=True, help_text='When the current thumbnail was rendered, null when there is none.', null=True),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    'ALTER TABLE "drive_item" ADD COLUMN IF NOT EXISTS "thumbnail_updated_at" timestamp with time zone NULL',
                    reverse_sql='ALTER TABLE "drive_item" DROP COLUMN IF EXISTS "thumbnail_updated_at"',
                ),
            ],
        ),
    ]
