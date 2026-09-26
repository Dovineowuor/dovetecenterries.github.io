from django.core.management.base import BaseCommand
from django.utils import timezone
from home.models import Newsletter, Article
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Processes scheduled newsletters and content.'

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(self.style.NOTICE(f"[{now}] Initializing Scheduling Cycle..."))

        # 1. Process Scheduled Newsletters
        scheduled_newsletters = Newsletter.objects.filter(
            status='scheduled',
            scheduled_for__lte=now
        )
        
        if scheduled_newsletters.exists():
            self.stdout.write(self.style.MIGRATE_HEADING(f"Newsletters: {scheduled_newsletters.count()} due."))
            for newsletter in scheduled_newsletters:
                try:
                    self.stdout.write(f"  - Dispatching: {newsletter.subject}")
                    if newsletter.send_newsletter():
                        self.stdout.write(self.style.SUCCESS(f"    [OK] Sent to all recipients."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    [FAIL] {str(e)}"))
        else:
            self.stdout.write("Newsletters: No items pending.")

        # 2. Process Scheduled Articles
        # Articles set to 'scheduled' with a past time should be flipped to 'published'
        pending_articles = Article.objects.filter(
            status='scheduled',
            scheduled_at__lte=now
        )

        if pending_articles.exists():
            self.stdout.write(self.style.MIGRATE_HEADING(f"Articles: {pending_articles.count()} to publish."))
            for article in pending_articles:
                try:
                    article.status = 'published'
                    article.save()
                    self.stdout.write(self.style.SUCCESS(f"  - Published article: {article.title}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  - Failed to publish {article.id}: {str(e)}"))
        else:
            self.stdout.write("Articles: All items synced.")

        self.stdout.write(self.style.SUCCESS(f"[{timezone.now()}] Cycle completed successfully."))
