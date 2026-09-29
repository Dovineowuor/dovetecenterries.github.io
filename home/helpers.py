import logging
from django.utils.text import slugify
from django.shortcuts import redirect
from django.conf import settings
import string
import secrets


def generate_random_string(N: int) -> str:
    """Generate a cryptographically secure random string."""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(N))


def generate_slug(text: str) -> str:
    """Generate a unique slug for a given text."""
    new_slug = slugify(text)
    from home.models import Article

    if Article.objects.filter(slug=new_slug).first():
        return generate_slug(text + generate_random_string(5))
    return new_slug


# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def send_mail_to_user(email: str, token: str) -> bool:
    """Send an account verification email using the styled email templates."""
    from home.email import absolute_url, send_styled_email

    subject = "Verify your email address"
    verification_link = absolute_url(f"/verify/{token}/")

    try:
        logger.debug("Initiating email connection.")
        sent = send_styled_email(
            subject,
            "emails/account_verification.html",
            {"verification_link": verification_link, "otp": "", "hide_otp": True},
            [email],
            fail_silently=False,
        )
        logger.info(f"Email successfully sent to {email}.")
        return sent > 0
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")
        return False


def send_mail_to_admin(subject: str, message: str) -> bool:
    """Send a styled notification email to the site administrators."""
    from home.email import send_styled_email

    recipient_list = [addr for _, addr in (settings.ADMINS or []) if addr]
    recipient_list.append(settings.EMAIL_HOST_USER)
    recipient_list = [addr for addr in dict.fromkeys(recipient_list) if addr]

    try:
        logger.debug("Initiating email connection.")
        sent = send_styled_email(
            subject,
            "emails/notification.html",
            {
                "heading": subject[:120],
                "preheader": subject[:120],
                "intro": "Message received by the Dovetec Enterprises website.",
                "body": message,
            },
            recipient_list,
            fail_silently=False,
        )
        logger.info(f"Email successfully sent to {recipient_list}.")
        return sent > 0
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_list}: {e}")
        return False
    



def set_language(request):
    """Set the language preference for the user."""
    lang = request.GET.get('lang')
    request.session['lang'] = lang
    referer = request.META.get('HTTP_REFERER', '/')
    if not referer.startswith(request.get_host()):
        return redirect('/')
    return redirect(referer)
