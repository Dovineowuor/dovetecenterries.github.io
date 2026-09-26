from django.db import migrations


def seed_templates(apps, schema_editor):
    QuestionnaireTemplate = apps.get_model('app', 'QuestionnaireTemplate')
    Question = apps.get_model('app', 'Question')
    defaults = [
        ('Discovery — needs & goals', 'discovery', [
            'What business problem are you trying to solve?',
            'Who are the primary users of this solution?',
            'What does success look like in 6–12 months?',
            'Are there existing systems we must integrate with?',
            'What is your rough budget range?',
        ]),
        ('Client onboarding', 'onboarding', [
            'Primary point of contact and preferred channel?',
            'Key stakeholders and roles?',
            'Access credentials / environments needed?',
            'Brand guidelines or design references?',
            'Preferred communication cadence?',
        ]),
        ('End-of-service handover', 'end_of_service', [
            'Confirm deliverables received.',
            'Any outstanding items or punch-list?',
            'Training completed for your team?',
            'Where should documentation be stored?',
        ]),
        ('Satisfaction survey', 'satisfaction', [
            'How satisfied are you with the delivery overall?',
            'How responsive was our team?',
            'Would you recommend us? Why / why not?',
            'What should we improve next time?',
        ]),
    ]
    for title, context, questions in defaults:
        template, created = QuestionnaireTemplate.objects.get_or_create(
            title=title,
            defaults={'context': context, 'is_active': True, 'intro': ''},
        )
        if created or not template.questions.exists():
            for i, text in enumerate(questions, start=1):
                Question.objects.create(
                    template=template,
                    text=text,
                    question_type='textarea',
                    required=False,
                    order=i,
                    context=context,
                )


def unseed_templates(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0013_questionnairetemplate_question_context_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
