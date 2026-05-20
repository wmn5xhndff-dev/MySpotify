from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0007_alter_song_options_alter_song_unique_together'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=10, choices=[('user', 'user'), ('bot', 'bot')])),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    null=True, blank=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='chat_messages',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['created_at']},
        ),
    ]
