from django.db import migrations


ROLE_GROUPS = {
    'client': 'Clients',
    'staff': 'Staff',
    'admin': 'Administrators',
}


def provision_groups_and_assign_users(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    User = apps.get_model('home', 'User')

    # ContentType rows are created post-migrate; a fresh DB has none yet.
    user_content_type, _ = ContentType.objects.get_or_create(
        app_label='home',
        model='user',
    )
    dashboard_permission, _ = Permission.objects.get_or_create(
        content_type=user_content_type,
        codename='access_dashboard',
        defaults={'name': 'Can access the staff dashboard'},
    )
    groups = {role: Group.objects.get_or_create(name=name)[0] for role, name in ROLE_GROUPS.items()}
    groups['staff'].permissions.add(dashboard_permission)
    groups['admin'].permissions.add(dashboard_permission)

    # Existing staff accounts predate the role field and must not become clients.
    User.objects.filter(is_superuser=True).update(role='admin')
    User.objects.filter(is_staff=True, role='client').update(role='staff')
    for role, group in groups.items():
        group.user_set.add(*User.objects.filter(role=role))


def remove_role_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=ROLE_GROUPS.values()).delete()


class Migration(migrations.Migration):
    dependencies = [('home', '0012_user_role')]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'permissions': [('access_dashboard', 'Can access the staff dashboard')]},
        ),
        migrations.RunPython(provision_groups_and_assign_users, remove_role_groups),
    ]
