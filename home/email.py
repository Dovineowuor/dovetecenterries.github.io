"""Styled transactional email support.

Every outgoing transactional email in this project is rendered from a
template under ``templates/emails/`` and sent as a multipart message so
mail clients get real HTML rather than raw markup. Plain-text parts are
derived from the HTML so the two never drift apart.

Usage::

    from home.email import send_styled_email

    send_styled_email(
        "Verify your email",
        "emails/account_verification.html",
        {"user": user, "otp": otp, "verification_link": link},
        [user.email],
    )
"""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

# Elements whose contents must never leak into the plain-text part.
_DROPPED_BLOCKS = re.compile(
    r"<(script|style|head|title)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL
)
_BLOCK_END = re.compile(
    r"</(p|div|tr|table|h1|h2|h3|h4|h5|h6|li|ul|ol|blockquote|section)\s*>", re.IGNORECASE
)
_LINE_BREAK = re.compile(r"<(br|hr)\s*/?>", re.IGNORECASE)
# Keep the destination visible for links, since a bare URL is often dropped.
_LINK = re.compile(
    r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL
)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_HIDDEN = re.compile(
    r"<(div|span|p)\b[^>]*"
    r"(display\s*:\s*none|font-size\s*:\s*0|mso-hide\s*:\s*all|opacity\s*:\s*0)"
    r"[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_MULTI_BLANK = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")


def site_url() -> str:
    """Absolute site root without a trailing slash."""
    return (getattr(settings, "SITE_URL", "") or "").rstrip("/")


def absolute_url(path: str) -> str:
    """Turn a site-relative path into an absolute URL usable in email."""
    if not path:
        return site_url()
    if path.startswith(("http://", "https://", "mailto:")):
        return path
    return f"{site_url()}/{path.lstrip('/')}"


def html_to_text(value: str) -> str:
    """Convert an HTML email body into a readable plain-text alternative."""
    if not value:
        return ""
    text = _COMMENT.sub("", value)
    text = _DROPPED_BLOCKS.sub("", text)
    text = _HIDDEN.sub("", text)

    def _link_sub(match: "re.Match[str]") -> str:
        label = strip_tags(match.group(2)).strip()
        href = match.group(1).strip()
        if not label:
            return href
        if href.rstrip("/").endswith(label) or label.rstrip("/") == href.rstrip("/"):
            return label
        return f"{label} ({href})"

    text = _LINK.sub(_link_sub, text)
    text = _LINE_BREAK.sub("\n", text)
    text = _BLOCK_END.sub("\n\n", text)
    text = strip_tags(text)
    text = html.unescape(text)
    text = _MULTI_SPACE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    text = _MULTI_BLANK.sub("\n\n", text)
    return text.strip()


def base_context(request=None, **extra) -> dict:
    """Context every transactional email template can rely on."""
    context = {
        "site_url": site_url(),
        "year": datetime.now().year,
        "site_name": getattr(settings, "SITE_NAME", "Dovetec Enterprises"),
        "site_tagline": getattr(
            settings,
            "SITE_TAGLINE",
            "Software engineering and IT solutions from Nairobi, Kenya",
        ),
        "support_email": getattr(settings, "CONTACT_EMAIL", None)
        or getattr(settings, "DEFAULT_FROM_EMAIL", ""),
        "request": request,
    }
    context.update(extra)
    return context


def render_email(template_name: str, context: dict) -> tuple[str, str]:
    """Render ``template_name`` into (html, text)."""
    full_context = base_context(**context)
    html_body = render_to_string(template_name, full_context)
    return html_body, html_to_text(html_body)


def send_styled_email(
    subject: str,
    template_name: str,
    context: dict | None = None,
    recipients: "list[str] | tuple[str] | str" = (),
    from_email: str | None = None,
    reply_to: "list[str] | tuple[str] | str | None" = None,
    text_body: str | None = None,
    fail_silently: bool = False,
    connection=None,
) -> int:
    """Render a styled email template and send it as multipart/alternative.

    Returns the number of messages sent (0 on failure when
    ``fail_silently``). Raises ``Exception`` from the mail backend otherwise.
    """
    recipients = [recipients] if isinstance(recipients, str) else [r for r in recipients if r]
    if not recipients:
        logger.info("send_styled_email: no recipients for %r; nothing sent.", subject)
        return 0

    html_body, derived_text = render_email(template_name, context or {})
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body if text_body is not None else derived_text,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        connection=connection,
        reply_to=[reply_to] if isinstance(reply_to, str) else reply_to,
    )
    message.attach_alternative(html_body, "text/html")
    try:
        return message.send(fail_silently=fail_silently)
    except Exception:
        logger.exception("Failed to send styled email %r to %s", subject, recipients)
        raise
