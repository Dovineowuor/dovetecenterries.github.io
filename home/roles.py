"""Django Group helpers for the platform's three account roles.

Groups are: Clients, Staff, Administrators.
Permissions are assigned via Django's permission system or Django Admin.
"""

from django.contrib.auth.models import Group, Permission


CLIENT_GROUP = "Clients"
STAFF_GROUP = "Staff"
ADMINISTRATOR_GROUP = "Administrators"


def ensure_role_groups(**kwargs):
    """Create the platform role groups and keep their base permissions current."""
    client_group, _ = Group.objects.get_or_create(name=CLIENT_GROUP)
    staff_group, _ = Group.objects.get_or_create(name=STAFF_GROUP)
    administrator_group, _ = Group.objects.get_or_create(name=ADMINISTRATOR_GROUP)

    dashboard_permission, _ = Permission.objects.get_or_create(
        content_type__app_label="home",
        codename="access_dashboard",
    )
    if dashboard_permission:
        staff_group.permissions.add(dashboard_permission)
        administrator_group.permissions.add(dashboard_permission)

    # Administrators get all permissions for full CRUD access.
    administrator_group.permissions.set(Permission.objects.all())
    return client_group, staff_group, administrator_group
