# Generated by Django 2.2.1 on 2019-06-04 20:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0008_auto_20190604_2019'),
    ]

    operations = [
        migrations.RenameField(
            model_name='node',
            old_name='statusSent',
            new_name='status_sent',
        ),
    ]
