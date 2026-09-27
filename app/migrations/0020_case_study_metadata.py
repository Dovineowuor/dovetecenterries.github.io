from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0019_featuretask_microtask'),
    ]

    operations = [
        migrations.AddField(
            model_name='casestudy',
            name='canonical_url',
            field=models.URLField(blank=True, help_text='Canonical URL for SEO', max_length=500),
        ),
        migrations.AddField(
            model_name='casestudy',
            name='meta_description',
            field=models.CharField(blank=True, help_text='Override meta description for SEO', max_length=500),
        ),
        migrations.AddField(
            model_name='casestudy',
            name='meta_title',
            field=models.CharField(blank=True, help_text='Override meta title for SEO', max_length=200),
        ),
        migrations.AddField(
            model_name='casestudy',
            name='og_description',
            field=models.CharField(blank=True, help_text='Open Graph description', max_length=500),
        ),
        migrations.AddField(
            model_name='casestudy',
            name='og_image',
            field=models.ImageField(blank=True, help_text='Open Graph image', null=True, upload_to='og_images/'),
        ),
        migrations.AddField(
            model_name='casestudy',
            name='og_title',
            field=models.CharField(blank=True, help_text='Open Graph title', max_length=200),
        ),
        migrations.AddField(
            model_name='casestudy',
            name='twitter_card',
            field=models.CharField(blank=True, help_text='Twitter card type (summary, summary_large_image)', max_length=50),
        ),
        migrations.AddField(
            model_name='casestudy',
            name='twitter_description',
            field=models.CharField(blank=True, help_text='Twitter description', max_length=500),
        ),
        migrations.AddField(
            model_name='casestudy',
            name='twitter_image',
            field=models.ImageField(blank=True, help_text='Twitter image', null=True, upload_to='twitter_images/'),
        ),
        migrations.AddField(
            model_name='casestudy',
            name='twitter_title',
            field=models.CharField(blank=True, help_text='Twitter title', max_length=200),
        ),
    ]
