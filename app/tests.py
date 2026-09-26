from django.test import TestCase
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from .media import store_uploaded_media
from .crm import (
    attach_questionnaire_for_context, create_service_inquiry, create_ticket,
    convert_won_inquiry_to_project, email_questionnaire_to_client,
    import_questions_into, questionnaire_context_directives,
)
from .models import (
    Answer, Contact, FeatureRequest, FeatureVote, MediaAsset, Organization, Plan,
    Project, Question, Questionnaire, QuestionnaireEvent, QuestionnaireTemplate,
    ServiceInquiry, Subscription, Ticket,
)


class MediaAssetTests(TestCase):
    def test_invalid_upload_creates_a_failure_record_without_a_file(self):
        upload = SimpleUploadedFile('unsafe.exe', b'not-an-executable', content_type='application/octet-stream')

        asset, stored = store_uploaded_media(upload)

        self.assertFalse(stored)
        self.assertEqual(asset.status, MediaAsset.STATUS_FAILED)
        self.assertFalse(asset.file)
        self.assertIn('not allowed', asset.failure_reason)

    def test_intake_reuses_contact_and_organization(self):
        first, _ = create_service_inquiry(
            first_name='Ada', last_name='Lovelace', email='ada@example.com', message='First brief',
            organization_name='Analytical Engines', service='software',
        )
        second, _ = create_service_inquiry(
            first_name='Ada', last_name='Lovelace', email='ada@example.com', message='Second brief',
            organization_name='Analytical Engines', service='consulting',
        )

        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(first.contact_id, second.contact_id)
        self.assertEqual(first.organization_id, second.organization_id)


class TicketIntakeTests(TestCase):
    def test_public_intake_creates_assigned_ticket(self):
        ticket, assets = create_ticket(
            first_name='Jane', last_name='Doe', email='jane@example.com',
            message='System down', service='it',
            subject='Printer offline', priority=Ticket.PRIORITY_URGENT,
        )
        self.assertTrue(ticket.reference.startswith('TK-'))
        self.assertEqual(ticket.status, Ticket.STATUS_NEW)
        self.assertEqual(ticket.type, Ticket.TYPE_ISSUE)
        self.assertTrue(ticket.activity_log.filter(action='created').exists())

    def test_legacy_helper_still_returns_linked_inquiry(self):
        inquiry, _ = create_service_inquiry(
            first_name='Ada', last_name='Lovelace', email='ada2@example.com',
            message='Need a quote', organization_name='AE Ltd', service='software',
        )
        self.assertIsInstance(inquiry, ServiceInquiry)
        self.assertTrue(inquiry.tickets.exists())


class FeatureBoardTests(TestCase):
    def test_seeded_plans_include_free_default_and_paid_tiers(self):
        self.assertTrue(Plan.objects.filter(is_default=True, price=0).exists())
        self.assertTrue(Plan.objects.filter(is_active=True).exclude(price=0).exists())

    def test_feature_vote_toggles_and_updates_count(self):
        feature = FeatureRequest.objects.create(
            title='Dark mode', description='Please add a dark theme.',
            category=FeatureRequest.CATEGORY_PLATFORM,
        )
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            email='voter@example.com', password='pass12345',
        )
        from django.test import Client
        client = Client()
        client.force_login(user)
        client.post(f'/features/{feature.slug}/vote/')
        feature.refresh_from_db()
        self.assertEqual(feature.vote_count, 1)
        self.assertEqual(FeatureVote.objects.filter(user=user, feature_request=feature).count(), 1)
        client.post(f'/features/{feature.slug}/vote/')
        feature.refresh_from_db()
        self.assertEqual(feature.vote_count, 0)

    def test_seeded_sample_templates_have_typed_questions(self):
        templates = QuestionnaireTemplate.objects.filter(context__in=[
            QuestionnaireTemplate.CONTEXT_DISCOVERY,
            QuestionnaireTemplate.CONTEXT_ONBOARDING,
            QuestionnaireTemplate.CONTEXT_END_OF_SERVICE,
        ])
        self.assertTrue(templates.exists())
        with_questions = [t for t in templates if t.questions.exists()]
        self.assertTrue(with_questions)


class ProjectCompletionQuestionnaireTests(TestCase):
    def test_completing_project_attaches_end_of_service_questionnaire(self):
        inquiry, _ = create_service_inquiry(
            first_name='Pat', last_name='Lee', email='pat@example.com',
            message='Build a portal', organization_name='Lee Co', service='software',
        )
        project = Project.objects.create(
            name='Lee portal', converted_from_inquiry=inquiry,
        )
        project.status = Project.STATUS_COMPLETED
        project.save()
        self.assertTrue(
            Questionnaire.objects.filter(
                inquiry=inquiry,
                context=QuestionnaireTemplate.CONTEXT_END_OF_SERVICE,
            ).exists()
        )

    def test_attach_is_idempotent_per_context(self):
        inquiry, _ = create_service_inquiry(
            first_name='Sam', last_name='Ray', email='sam@example.com',
            message='Consult', organization_name='Ray Ltd', service='consulting',
        )
        q1, status1 = attach_questionnaire_for_context(
            inquiry, QuestionnaireTemplate.CONTEXT_END_OF_SERVICE,
        )
        q2, status2 = attach_questionnaire_for_context(
            inquiry, QuestionnaireTemplate.CONTEXT_END_OF_SERVICE,
        )
        self.assertEqual(status1, 'created')
        self.assertEqual(status2, 'exists')
        self.assertEqual(
            Questionnaire.objects.filter(
                inquiry=inquiry,
                context=QuestionnaireTemplate.CONTEXT_END_OF_SERVICE,
            ).count(),
            1,
        )


class WonToProjectTests(TestCase):
    def test_won_inquiry_creates_linked_project(self):
        from decimal import Decimal
        inquiry, _ = create_service_inquiry(
            first_name='Zoe', last_name='Bee', email='zoe@example.com',
            message='E-commerce build', organization_name='Zobee', service='software',
        )
        inquiry.stage = ServiceInquiry.STAGE_WON
        inquiry.estimated_value = Decimal('8300')
        inquiry.save()

        project, created = convert_won_inquiry_to_project(inquiry)

        self.assertTrue(created)
        self.assertEqual(project.converted_from_inquiry_id, inquiry.id)
        self.assertEqual(project.status, Project.STATUS_ACTIVE)
        self.assertEqual(project.estimated_budget, Decimal('8300'))
        self.assertEqual(project.organization_id, inquiry.organization_id)
        self.assertTrue(project.name)

    def test_conversion_is_idempotent(self):
        inquiry, _ = create_service_inquiry(
            first_name='Micheal', last_name='Int', email='m@example.com',
            message='Consulting', organization_name='Micheal Interiors',
            service='consulting',
        )
        p1, created1 = convert_won_inquiry_to_project(inquiry)
        p2, created2 = convert_won_inquiry_to_project(inquiry)
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(p1.id, p2.id)
        self.assertEqual(
            Project.objects.filter(converted_from_inquiry=inquiry).count(), 1,
        )


class SubscriptionTests(TestCase):
    def test_plan_for_falls_back_to_default_free_plan(self):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            email='free@example.com', password='pass12345',
        )
        plan = Subscription.plan_for(user)
        self.assertIsNotNone(plan)
        self.assertTrue(plan.is_free)

    def test_has_premium_false_for_free_plan(self):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            email='free2@example.com', password='pass12345',
        )
        self.assertFalse(Subscription.has_premium(user))


class QuestionnaireMergeImportTests(TestCase):
    def setUp(self):
        self.inquiry, _ = create_service_inquiry(
            first_name='Ada', last_name='Lovelace', email='merge@example.com',
            message='Discovery help', organization_name='AE', service='software',
        )
        self.questionnaire = Questionnaire.objects.create(
            inquiry=self.inquiry,
            title='Discovery + Compliance',
            context=QuestionnaireTemplate.CONTEXT_DISCOVERY,
            status='completed',
        )
        self.q1 = Question.objects.create(
            questionnaire=self.questionnaire,
            text='What are your primary goals?',
            order=1,
        )
        Answer.objects.create(question=self.q1, answer='Ship a portal by Q3')
        self.discovery = QuestionnaireTemplate.objects.create(
            title='Discovery Pack', context=QuestionnaireTemplate.CONTEXT_DISCOVERY,
        )
        Question.objects.create(
            template=self.discovery, text='What are your primary goals?', order=1,
        )
        Question.objects.create(
            template=self.discovery, text='Who are the stakeholders?', order=2,
        )
        self.compliance = QuestionnaireTemplate.objects.create(
            title='Compliance Pack', context=QuestionnaireTemplate.CONTEXT_CUSTOM,
        )
        Question.objects.create(
            template=self.compliance, text='Any data-residency requirements?', order=1,
        )

    def test_import_merges_without_clearing_answers(self):
        result = import_questions_into(self.questionnaire, self.discovery)
        result2 = import_questions_into(self.questionnaire, self.compliance)

        self.assertEqual(result['added'], 1)  # goals already present
        self.assertEqual(result['skipped'], 1)
        self.assertEqual(result2['added'], 1)
        self.assertEqual(self.questionnaire.questions.count(), 3)
        self.q1.refresh_from_db()
        answer = Answer.objects.get(question=self.q1)
        self.assertEqual(answer.answer, 'Ship a portal by Q3')

    def test_import_reopens_completed_and_keeps_status_unlocked(self):
        import_questions_into(self.questionnaire, self.compliance)
        self.questionnaire.refresh_from_db()
        self.assertNotEqual(self.questionnaire.status, 'completed')
        self.assertIn(self.questionnaire.status, ('sent', 'in_progress'))
        self.assertIsNone(self.questionnaire.completed_at)
        self.assertTrue(
            QuestionnaireEvent.objects.filter(
                questionnaire=self.questionnaire,
                action=QuestionnaireEvent.ACTION_QUESTIONS_IMPORTED,
            ).exists()
        )

    def test_context_directives_differ_by_context(self):
        discovery = questionnaire_context_directives(QuestionnaireTemplate.CONTEXT_DISCOVERY)
        onboarding = questionnaire_context_directives(QuestionnaireTemplate.CONTEXT_ONBOARDING)
        self.assertTrue(discovery)
        self.assertNotEqual(discovery, onboarding)
        self.assertTrue(any('stakeholder' in d.lower() for d in discovery))

    def test_email_includes_portal_link_and_directives(self):
        sent = email_questionnaire_to_client(self.questionnaire, kind='sent')
        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn('Discovery', body)
        self.assertIn('/dashboard/client/questionnaires/', body)
        self.assertIn('Directives', body)
        self.assertIn('stakeholders', body.lower())


class ClientQuestionnaireFillLogTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Group
        from home.models import User
        self.client_user = User.objects.create_user(
            email='fill@example.com', password='pass12345',
            first_name='Fill', last_name='Client',
        )
        clients, _ = Group.objects.get_or_create(name='Clients')
        self.client_user.groups.add(clients)
        self.inquiry, _ = create_service_inquiry(
            first_name='Fill', last_name='Client', email='fill@example.com',
            message='Need survey', organization_name='FillCo', service='software',
        )
        self.questionnaire = Questionnaire.objects.create(
            inquiry=self.inquiry,
            title='Onboarding',
            context=QuestionnaireTemplate.CONTEXT_ONBOARDING,
            status='sent',
        )
        self.q1 = Question.objects.create(
            questionnaire=self.questionnaire,
            text='Primary contact email?',
            order=1,
        )

    def test_submit_logs_answers_and_emails_client(self):
        self.client.force_login(self.client_user)
        response = self.client.post(
            reverse('client_questionnaire_fill', args=[self.questionnaire.id]),
            {f'question_{self.q1.id}': 'ops@example.com'},
            SERVER_NAME='localhost',
        )
        self.assertEqual(response.status_code, 302)
        self.questionnaire.refresh_from_db()
        self.assertEqual(self.questionnaire.status, 'completed')
        self.assertTrue(
            QuestionnaireEvent.objects.filter(
                questionnaire=self.questionnaire,
                action=QuestionnaireEvent.ACTION_ANSWERED,
                answer_snapshot='ops@example.com',
            ).exists()
        )
        self.assertTrue(
            QuestionnaireEvent.objects.filter(
                questionnaire=self.questionnaire,
                action=QuestionnaireEvent.ACTION_COMPLETED,
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Responses received', mail.outbox[0].subject)
        self.assertIn('onboarding', mail.outbox[0].body.lower())

    def test_resubmit_logs_updated_answer_history(self):
        Answer.objects.create(question=self.q1, answer='old@example.com')
        self.questionnaire.status = 'in_progress'
        self.questionnaire.save()
        self.client.force_login(self.client_user)
        self.client.post(
            reverse('client_questionnaire_fill', args=[self.questionnaire.id]),
            {f'question_{self.q1.id}': 'new@example.com'},
            SERVER_NAME='localhost',
        )
        event = QuestionnaireEvent.objects.filter(
            questionnaire=self.questionnaire,
            action=QuestionnaireEvent.ACTION_UPDATED,
        ).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.answer_snapshot, 'new@example.com')
        self.assertIn('old@example.com', event.content)
