from django.core.management.base import BaseCommand
from app.models import WhatsAppNotification
from app.crm import send_whatsapp


class Command(BaseCommand):
    help = 'Retry failed WhatsApp messages.'

    def add_arguments(self, parser):
        parser.add_argument('--channel', type=str, default=None, help='Filter by channel')
        parser.add_argument('--limit', type=int, default=50, help='Max messages to retry')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be retried')

    def handle(self, *args, **options):
        qs = WhatsAppNotification.objects.filter(status=WhatsAppNotification.STATUS_FAILED)
        if options['channel']:
            qs = qs.filter(channel=options['channel'])
        qs = qs.order_by('-created_at')[:options['limit']]
        count = qs.count()
        self.stdout.write(f'Found {count} failed WhatsApp message(s)')
        if options['dry_run']:
            for wa in qs:
                self.stdout.write(f'  DRY RUN: {wa.recipient_phone} [{wa.channel}] {wa.message[:80]}')
            return
        retried = 0
        for wa in qs:
            result = send_whatsapp(wa.recipient_phone, wa.message, channel=wa.channel, notification=wa.notification)
            if result:
                retried += 1
        self.stdout.write(self.style.SUCCESS(f'Retried {retried}/{count} message(s)'))
