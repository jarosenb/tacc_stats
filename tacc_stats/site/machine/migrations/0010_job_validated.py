# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-12-05 15:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machine', '0009_job_blockavebw'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='validated',
            field=models.BooleanField(default=False),
        ),
    ]