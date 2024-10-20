# Generated by Django 5.1.1 on 2024-10-13 09:15

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('template', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Dir',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display', models.CharField(max_length=255)),
                ('dir', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='yesand.dir')),
            ],
            options={
                'verbose_name': 'directory',
                'verbose_name_plural': 'directories',
            },
        ),
        migrations.CreateModel(
            name='AIModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display', models.CharField(max_length=255)),
                ('dir', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(class)ss', to='yesand.dir')),
            ],
            options={
                'verbose_name': 'AI model',
                'verbose_name_plural': 'AI models',
            },
        ),
        migrations.CreateModel(
            name='Prompt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display', models.CharField(max_length=255)),
                ('text', models.TextField(blank=True)),
                ('aimodels', models.ManyToManyField(blank=True, related_name='prompts', to='yesand.aimodel')),
                ('dir', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(class)ss', to='yesand.dir')),
                ('fields', models.ManyToManyField(blank=True, related_name='prompts', to='yesand.field')),
            ],
            options={
                'verbose_name': 'prompt',
                'verbose_name_plural': 'prompts',
            },
        ),
    ]
