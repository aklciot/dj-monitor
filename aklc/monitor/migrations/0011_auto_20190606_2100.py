# Generated by Django 2.2.2 on 2019-06-06 21:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0010_auto_20190604_2026'),
    ]

    operations = [
        migrations.RenameField(
            model_name='node',
            old_name='battValue',
            new_name='battLevel',
        ),
    ]
