from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from home.models import User
from home.roles import ADMINISTRATOR_GROUP, CLIENT_GROUP, STAFF_GROUP
from shop.models import Product


class DashboardPermissionsTests(TestCase):
    def create_user(self, email, *, staff=False, superuser=False):
        user = User.objects.create_user(
            email=email,
            password='safe-test-password',
            first_name='Test',
            last_name='User',
            is_staff=staff,
            is_superuser=superuser,
        )
        if superuser:
            user.groups.add(Group.objects.get(name=ADMINISTRATOR_GROUP))
        elif staff:
            user.groups.add(Group.objects.get(name=STAFF_GROUP))
        else:
            user.groups.add(Group.objects.get(name=CLIENT_GROUP))
        return user

    def test_new_accounts_receive_their_primary_role_group(self):
        client = self.create_user('client@example.com')
        staff = self.create_user('staff@example.com', staff=True)
        administrator = self.create_user('admin@example.com', superuser=True, staff=True)

        self.assertTrue(client.groups.filter(name=CLIENT_GROUP).exists())
        self.assertTrue(staff.groups.filter(name=STAFF_GROUP).exists())
        self.assertTrue(administrator.groups.filter(name=ADMINISTRATOR_GROUP).exists())
        self.assertTrue(staff.has_perm('home.access_dashboard'))
        self.assertTrue(administrator.has_perm('home.access_dashboard'))

    def test_client_is_routed_to_client_portal(self):
        client = self.create_user('client@example.com')
        self.client.force_login(client)

        response = self.client.get(reverse('dashboard'))

        self.assertRedirects(response, reverse('client_dashboard'))

    def test_staff_needs_model_permission_for_generic_crud(self):
        staff = self.create_user('staff2@example.com', staff=True)
        self.client.force_login(staff)
        url = reverse('dashboard_add', args=['shop', 'product'])

        denied = self.client.get(url)
        self.assertEqual(denied.status_code, 403)

        staff.user_permissions.add(Permission.objects.get(codename='add_product'))
        allowed = self.client.get(url)
        self.assertEqual(allowed.status_code, 200)

    def test_dashboard_provides_operational_analytics(self):
        administrator = self.create_user('admin2@example.com', superuser=True, staff=True)
        self.client.force_login(administrator)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('lead_chart_labels', response.context)
        self.assertIn('article_chart_values', response.context)
        self.assertContains(response, 'leadPipelineChart')
