from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


class ForgotPasswordFlowTests(TestCase):
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_forgot_password_with_unknown_email_shows_form_error(self):
        response = self.client.post(
            reverse('forgot_password'),
            {'email': 'missing@example.com'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No account found')
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_forgot_password_for_valid_user_sends_otp_and_redirects(self):
        User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='StrongPass123!',
            first_name='Alice',
        )

        response = self.client.post(
            reverse('forgot_password'),
            {'email': 'alice@example.com'},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('verify_otp', args=['alice@example.com']))
        self.assertEqual(len(mail.outbox), 1)

    def test_verify_otp_page_renders_without_template_reverse_error(self):
        user = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='StrongPass123!',
            first_name='Bob',
        )
        profile = user.profile
        profile.otp = '123456'
        profile.otp_timestamp = timezone.now()
        profile.save()

        response = self.client.get(reverse('verify_otp', args=['bob@example.com']))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verify Your OTP')
        self.assertContains(response, 'Request new code')
