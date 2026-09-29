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

    def test_every_dashboard_chart_gets_matched_labels_values_and_colour_keys(self):
        """A chart with mismatched series silently renders wrong or throws.

        The colour maps are keyed on the raw status key, not the display
        label, so both have to reach the template. Getting this wrong is what
        left every slice of a doughnut the same colour, and a mistyped ORM
        keyword is a 500 rather than a visual regression, so assert the whole
        contract rather than just the page returning 200.
        """
        administrator = self.create_user('admin3@example.com', superuser=True, staff=True)
        self.client.force_login(administrator)

        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

        # (canvas id, label/keys context keys, value context keys)
        charts = [
            ('leadPipelineChart', ['lead_chart_labels', 'lead_chart_keys'],
             ['lead_chart_values', 'lead_chart_values_kes']),
            ('articleWorkflowChart', ['article_chart_labels', 'article_chart_keys'],
             ['article_chart_values']),
            ('projectStatusChart', ['project_chart_labels', 'project_chart_keys'],
             ['project_chart_values', 'project_chart_budget']),
            ('newsletterTurnoutChart', ['newsletter_chart_labels'],
             ['newsletter_chart_values', 'newsletter_chart_rates']),
        ]
        for canvas_id, label_keys, value_keys in charts:
            with self.subTest(chart=canvas_id):
                self.assertContains(response, canvas_id)
                labels = None
                for key in label_keys:
                    self.assertIn(key, response.context, f'{canvas_id} missing {key}')
                    labels = response.context[key]
                for key in value_keys:
                    self.assertIn(key, response.context, f'{canvas_id} missing {key}')
                    values = response.context[key]
                    self.assertEqual(
                        len(labels), len(values),
                        f'{canvas_id}: {key} has {len(values)} values '
                        f'but there are {len(labels)} labels',
                    )

    def test_dashboard_charts_survive_an_empty_database(self):
        """Charts must render with no rows, not crash or lose their axes.

        The view pads missing stages with zeroes on purpose so the funnel does
        not change width as data arrives; that padding is what keeps the page
        alive on a brand-new install.
        """
        administrator = self.create_user('admin4@example.com', superuser=True, staff=True)
        self.client.force_login(administrator)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'leadPipelineChart')
        self.assertContains(response, 'newsletterTurnoutChart')
        self.assertEqual(response.context['lead_chart_values'],
                         [0] * len(response.context['lead_chart_labels']))
        self.assertEqual(response.context['newsletter_chart_values'],
                         [0] * len(response.context['newsletter_chart_labels']))
