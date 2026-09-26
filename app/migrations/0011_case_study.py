from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0005_category_canonical_url_category_meta_description_and_more'),
        ('app', '0010_project_canonical_url_project_meta_description_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CaseStudy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, help_text='Brand/project name')),
                ('slug', models.SlugField(max_length=250, unique=True, null=True, blank=True)),
                ('tagline', models.CharField(max_length=300, blank=True, help_text='Short tagline for the case study')),
                ('description', models.TextField(help_text='Full description of the case study')),
                ('overview', models.TextField(blank=True, help_text='High-level overview paragraph')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('review', 'In Review'), ('published', 'Published'), ('archived', 'Archived')], default='draft', max_length=20)),
                ('accent_color', models.CharField(default='#0071e3', help_text='Brand accent color (hex)', max_length=7)),
                ('primary_color', models.CharField(default='#1d1d1f', help_text='Brand primary color (hex)', max_length=7)),
                ('secondary_color', models.CharField(default='#5856d6', help_text='Brand secondary color (hex)', max_length=7)),
                ('bg_color', models.CharField(default='#ffffff', help_text='Background color (hex)', max_length=7)),
                ('bg_secondary_color', models.CharField(default='#f5f5f7', help_text='Secondary background color (hex)', max_length=7)),
                ('logo_image', models.ImageField(blank=True, help_text='Brand logo', null=True, upload_to='case_studies/logos/')),
                ('hero_image', models.ImageField(blank=True, help_text='Hero/cover image', null=True, upload_to='case_studies/heroes/')),
                ('favicon', models.ImageField(blank=True, null=True, upload_to='case_studies/favicons/')),
                ('featured', models.BooleanField(default=False)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('problem_statement', models.TextField(blank=True)),
                ('objectives', models.TextField(blank=True)),
                ('business_challenge', models.TextField(blank=True)),
                ('research_findings', models.TextField(blank=True)),
                ('user_needs', models.TextField(blank=True)),
                ('features', models.TextField(blank=True)),
                ('user_challenges', models.TextField(blank=True)),
                ('competitor_data', models.TextField(blank=True)),
                ('unique_features', models.TextField(blank=True)),
                ('persona_data', models.TextField(blank=True)),
                ('task_mapping', models.TextField(blank=True)),
                ('matrix_data', models.TextField(blank=True)),
                ('root_cause', models.TextField(blank=True)),
                ('task_flows', models.TextField(blank=True)),
                ('sketches', models.TextField(blank=True)),
                ('major_screens', models.TextField(blank=True)),
                ('screens', models.TextField(blank=True)),
                ('category', models.ForeignKey(blank=True, help_text='Category from existing shop entities', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='case_studies', to='shop.category')),
            ],
            options={
                'ordering': ['-published_at', '-created_at'],
                'indexes': [
                    models.Index(fields=['status', 'featured'], name='idx_cs_status_featured'),
                    models.Index(fields=['category'], name='idx_cs_category'),
                    models.Index(fields=['published_at'], name='idx_cs_published'),
                ],
            },
        ),
    ]
