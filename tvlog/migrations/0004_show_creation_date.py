# Generated by Django 4.2.11 on 2024-04-02 02:41

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('tvlog', '0003_remove_currentlywatching_show'),
    ]

    operations = [
        migrations.AddField(
            model_name='show',
            name='creation_date',
            field=models.DateField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
