from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_contacts(apps, schema_editor):
    Contact = apps.get_model('app', 'Contact')
    ServiceInquiry = apps.get_model('app', 'ServiceInquiry')
    for inquiry in ServiceInquiry.objects.filter(contact__isnull=True).iterator():
        first_name, _, last_name = (inquiry.name or '').strip().partition(' ')
        contact, _ = Contact.objects.get_or_create(
            email=inquiry.email.lower(),
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'phone': inquiry.phone or '',
            },
        )
        ServiceInquiry.objects.filter(pk=inquiry.pk).update(contact=contact)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('app', '0006_mediaasset'),
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('website', models.URLField(blank=True)),
                ('industry', models.CharField(blank=True, max_length=120)),
                ('phone', models.CharField(blank=True, max_length=30)),
                ('address', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(blank=True, max_length=100)),
                ('last_name', models.CharField(blank=True, max_length=100)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('phone', models.CharField(blank=True, max_length=30)),
                ('job_title', models.CharField(blank=True, max_length=120)),
                ('preferred_contact_method', models.CharField(choices=[('email', 'Email'), ('phone', 'Phone'), ('whatsapp', 'WhatsApp')], default='email', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contacts', to='app.organization')),
                ('portal_user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='crm_contact', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['first_name', 'last_name', 'email']},
        ),
        migrations.AddField(model_name='serviceinquiry', name='budget_range', field=models.CharField(choices=[('unspecified', 'Not specified'), ('under_50k', 'Under KES 50,000'), ('50k_250k', 'KES 50,000–250,000'), ('250k_1m', 'KES 250,000–1,000,000'), ('over_1m', 'Over KES 1,000,000')], default='unspecified', max_length=30)),
        migrations.AddField(model_name='serviceinquiry', name='contact', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inquiries', to='app.contact')),
        migrations.AddField(model_name='serviceinquiry', name='industry', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='serviceinquiry', name='organization', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inquiries', to='app.organization')),
        migrations.AddField(model_name='serviceinquiry', name='preferred_contact_method', field=models.CharField(choices=[('email', 'Email'), ('phone', 'Phone'), ('whatsapp', 'WhatsApp')], default='email', max_length=20)),
        migrations.AddField(model_name='serviceinquiry', name='source', field=models.CharField(choices=[('website', 'Website contact form'), ('service_page', 'Service request form'), ('referral', 'Referral'), ('manual', 'Manual entry')], default='website', max_length=30)),
        migrations.AddField(model_name='serviceinquiry', name='timeline', field=models.CharField(blank=True, max_length=120)),
        migrations.RunPython(backfill_contacts, migrations.RunPython.noop),
    ]
