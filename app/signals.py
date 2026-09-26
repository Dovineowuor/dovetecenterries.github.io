from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from .models import Project, QuestionnaireTemplate
from .crm import attach_questionnaire_for_context, notify


@receiver(post_save, sender=Project)
def auto_attach_end_of_service_questionnaire(sender, instance, created, **kwargs):
    """When a delivery project is marked completed, attach the end-of-service survey."""
    if created or instance.status != Project.STATUS_COMPLETED:
        return
    inquiry = instance.converted_from_inquiry
    if not inquiry:
        return

    questionnaire, status = attach_questionnaire_for_context(
        inquiry,
        QuestionnaireTemplate.CONTEXT_END_OF_SERVICE,
        actor=None,
        auto_send=True,
    )
    if status != 'created':
        return

    recipients = []
    if inquiry.contact and inquiry.contact.portal_user:
        recipients.append(inquiry.contact.portal_user)
    if inquiry.assigned_to:
        recipients.append(inquiry.assigned_to)
    if recipients:
        notify(
            recipients=recipients,
            verb='questionnaire_sent',
            title=f"Project complete — {instance.name}",
            body="Please complete the end-of-service questionnaire.",
            link=reverse('client_questionnaires'),
        )
