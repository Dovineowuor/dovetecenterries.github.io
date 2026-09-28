import uuid
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.db.models.signals import post_migrate
from django.dispatch import receiver

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
from .models import Article, Newsletter, NewsletterSubscription, Profile
from shop.models import Product
from community.models import Topic, Post
from django.utils import timezone
from django.urls import reverse
from .roles import ensure_role_groups

def get_styled_content(title, body, cta_link, cta_text, theme_color="#007bff"):
    """
    Generate a premium HTML wrapper for automated newsletters.
    """
    return f'''
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; border: 1px solid #f0f0f0; border-radius: 15px; background-color: #ffffff;">
        <div style="text-align: center; margin-bottom: 25px;">
            <h1 style="color: {theme_color}; margin: 0; font-size: 24px;">DoveTec News</h1>
        </div>
        <div style="border-top: 3px solid {theme_color}; padding-top: 20px;">
            <h2 style="color: #2d3436; margin-top: 0;">{title}</h2>
            <div style="color: #636e72; line-height: 1.7; font-size: 16px; margin-bottom: 25px;">
                {body}
            </div>
            <div style="text-align: center;">
                <a href="{cta_link}" style="display: inline-block; padding: 12px 30px; background-color: {theme_color}; color: #ffffff; text-decoration: none; border-radius: 50px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    {cta_text}
                </a>
            </div>
        </div>
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; font-size: 12px; color: #b2bec3;">
            <p>You're part of our inner circle. Thanks for being with us!</p>
            <p>Don't want these emails? <a href="#" style="color: {theme_color}; text-decoration: none;">Manage Subscriptions</a></p>
        </div>
    </div>
    '''

@receiver(post_save, sender=Article)
def create_article_newsletter(sender, instance, created, **kwargs):
    if created and instance.status == 'published':
        content = get_styled_content(
            title=instance.title,
            body=f"{instance.content[:250]}...",
            cta_link=f"/blog-detail/{instance.slug}",
            cta_text="Read Full Article"
        )
        newsletter = Newsletter.objects.create(
            subject=f"📖 New Read: {instance.title}",
            content=content,
            status='scheduled',
            scheduled_for=timezone.now()
        )
        newsletter.recipients.add(*NewsletterSubscription.objects.filter(unsubscribed_at__isnull=True))

@receiver(post_save, sender=Product)
def create_product_newsletter(sender, instance, created, **kwargs):
    if created:
        content = get_styled_content(
            title=f"New Arrival: {instance.name}",
            body=f"Exciting news! We've just added <b>{instance.name}</b> to our collection. Get yours today for just ${instance.price}.",
            cta_link="/shop/",
            cta_text="Shop Now",
            theme_color="#28a745"
        )
        newsletter = Newsletter.objects.create(
            subject=f"🛍️ Just Landed: {instance.name}",
            content=content,
            status='scheduled',
            scheduled_for=timezone.now()
        )
        newsletter.recipients.add(*NewsletterSubscription.objects.filter(unsubscribed_at__isnull=True))

@receiver(post_save, sender=Topic)
def create_topic_newsletter(sender, instance, created, **kwargs):
    """
    Recommend new communities to users.
    """
    if created:
        content = get_styled_content(
            title=f"New Community: {instance.name}",
            body=f"A new space has been created: <b>{instance.name}</b>. {instance.description or 'Join the conversation today!'}",
            cta_link=f"/community/topic/{instance.id}/",
            cta_text="Explore Community",
            theme_color="#6c5ce7"
        )
        newsletter = Newsletter.objects.create(
            subject=f"🤝 New Community Recommendation: {instance.name}",
            content=content,
            status='scheduled',
            scheduled_for=timezone.now()
        )
        newsletter.recipients.add(*NewsletterSubscription.objects.filter(unsubscribed_at__isnull=True))

@receiver(post_save, sender=Post)
def create_post_newsletter(sender, instance, created, **kwargs):
    """
    Notify subscribers about trending or new community threads.
    """
    if created:
        content = get_styled_content(
            title=instance.title,
            body=f"Check out this new thread in <b>{instance.topic.name}</b>: <br><i>{instance.content[:150]}...</i>",
            cta_link=f"/community/post/{instance.id}/",
            cta_text="Join Discussion",
            theme_color="#e84393"
        )
        newsletter = Newsletter.objects.create(
            subject=f"🔥 New Discussion: {instance.title}",
            content=content,
            status='scheduled',
            scheduled_for=timezone.now()
        )
        newsletter.recipients.add(*NewsletterSubscription.objects.filter(unsubscribed_at__isnull=True))


# ── Auto-create Profile when a User is registered ──────────────────
# NOTE: use the real User model class here — passing the 'home.User'
# string would silently never fire.
User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile automatically when a new User is created."""
    if created:
        Profile.objects.get_or_create(user=instance, defaults={
            'is_verified': False,
            'token': str(uuid.uuid4()),
        })


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the user's profile whenever the user is saved."""
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        # Profile doesn't exist yet — the create_user_profile signal handles it
        pass


@receiver(post_save, sender=User)
def sync_user_primary_role_group(sender, instance, created=False, raw=False, **kwargs):
    """Keep each account in its primary role group (Clients / Staff / Administrators)."""
    if raw:
        return
    from .roles import ensure_role_groups

    client_group, staff_group, admin_group = ensure_role_groups()
    if instance.is_superuser:
        target = admin_group
    elif instance.is_staff:
        target = staff_group
    else:
        target = client_group
    instance.groups.add(target)


@receiver(post_migrate)
def provision_platform_role_groups(sender, **kwargs):
    """Provision platform role groups after migrations have created Django permissions."""
    from .roles import ensure_role_groups
    ensure_role_groups()
