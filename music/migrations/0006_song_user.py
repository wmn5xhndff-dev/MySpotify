# Generated manually — adds per-user favorites

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0005_song_is_favorite'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add nullable user FK
        migrations.AddField(
            model_name='song',
            name='user',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='songs',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Пользователь',
            ),
        ),
    ]
