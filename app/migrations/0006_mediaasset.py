from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import app.models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
        ('app', '0005_question_answer_questionnaire_question_questionnaire'),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaAsset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(blank=True, null=True, upload_to=app.models.media_asset_upload_path)),
                ('original_name', models.CharField(max_length=255)),
                ('mime_type', models.CharField(blank=True, max_length=150)),
                ('size_bytes', models.PositiveBigIntegerField(default=0)),
                ('kind', models.CharField(choices=[('image', 'Image'), ('document', 'Document'), ('archive', 'Archive'), ('other', 'Other')], default='other', max_length=20)),
                ('status', models.CharField(choices=[('uploaded', 'Uploaded'), ('ready', 'Ready'), ('failed', 'Failed')], db_index=True, default='uploaded', max_length=20)),
                ('failure_reason', models.TextField(blank=True)),
                ('alt_text', models.CharField(blank=True, max_length=255)),
                ('is_public', models.BooleanField(default=False)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('object_id', models.PositiveBigIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='contenttypes.contenttype')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='media_assets', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddIndex(model_name='mediaasset', index=models.Index(fields=['content_type', 'object_id'], name='app_mediaas_content_3eaa95_idx')),
        migrations.AddIndex(model_name='mediaasset', index=models.Index(fields=['owner', 'status'], name='app_mediaas_owner_i_1f9c6f_idx')),
    ]
