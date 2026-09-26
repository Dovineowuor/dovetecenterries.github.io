from django.db import migrations

DEFAULT_CATEGORIES = [
    ('Technology', 'Discussion about technology trends, tools, and platforms.'),
    ('Software', 'Software engineering, architecture, and development practices.'),
    ('Design', 'UI/UX, product design, and creative work.'),
    ('Career', 'Jobs, mentorship, growth, and professional development.'),
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model('community', 'Category')
    for name, description in DEFAULT_CATEGORIES:
        Category.objects.get_or_create(name=name, defaults={'description': description})


def unseed_categories(apps, schema_editor):
    Category = apps.get_model('community', 'Category')
    Category.objects.filter(name__in=[name for name, _ in DEFAULT_CATEGORIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0008_event'),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
