from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.core.files.temp import NamedTemporaryFile
from app.models import CaseStudy, ShopCategory
import json

class Command(BaseCommand):
    help = 'Create default case studies for Dovetec Enterprises'

    def handle(self, *args, **options):
        categories_map = {}
        for cat_name in ['E-Commerce', 'Cloud', 'Digital Transformation', 'Consulting', 'SaaS']:
            cat, _ = ShopCategory.objects.get_or_create(
                name=cat_name,
                defaults={'description': f'{cat_name} services'}
            )
            categories_map[cat_name] = cat

        case_studies_data = [
            {
                'name': 'E-Commerce Platform',
                'slug': 'e-commerce-platform',
                'tagline': 'Modernized an outdated e-commerce platform, resulting in a 45% increase in conversion rates and 30% improvement in page load times.',
                'description': 'We transformed a struggling e-commerce platform into a high-performing digital storefront. The project involved redesigning the user experience, optimizing backend performance, and implementing modern payment integrations. The result was a 45% increase in conversion rates and a 30% improvement in page load times, driving significant revenue growth for our client.',
                'overview': 'A comprehensive e-commerce overhaul that modernized the entire digital shopping experience, from frontend interface to backend infrastructure.',
                'category': categories_map.get('E-Commerce'),
                'status': CaseStudy.STATUS_PUBLISHED,
                'accent_color': '#FE8E38',
                'primary_color': '#1d1d1f',
                'secondary_color': '#5856d6',
                'bg_color': '#ffffff',
                'bg_secondary_color': '#f5f5f7',
                'featured': True,
                'problem_statement': 'The existing e-commerce platform suffered from slow load times, poor mobile responsiveness, and a confusing checkout process that was causing high cart abandonment rates.',
                'objectives': 'Increase conversion rates by 40%, improve page load times by 25%, and provide a seamless mobile shopping experience.',
                'business_challenge': 'The client was losing customers at an alarming rate due to poor site performance and outdated design. Competitors were outperforming them in both speed and user experience.',
                'research_findings': 'User testing revealed that 60% of visitors abandoned the site within the first 30 seconds. Mobile users had a 50% higher bounce rate than desktop users.',
                'user_needs': 'Fast page loads, intuitive navigation, seamless checkout, and mobile-first design.',
                'features': 'Modern responsive design, optimized product search, one-click checkout, real-time inventory, and comprehensive analytics dashboard.',
                'unique_features': 'AI-powered product recommendations, AR product preview, and personalized shopping experience based on browsing history.',
            },
            {
                'name': 'Cloud Migration',
                'slug': 'cloud-migration',
                'tagline': 'Successfully migrated a financial services firm to AWS, reducing infrastructure costs by 35% and improving system reliability.',
                'description': 'We orchestrated the complete migration of a financial services firm\'s infrastructure to AWS. The project involved careful planning, phased execution, and rigorous testing to ensure zero downtime. The result was a 35% reduction in infrastructure costs and significantly improved system reliability with 99.99% uptime.',
                'overview': 'A mission-critical cloud migration that ensured business continuity while dramatically reducing costs and improving scalability.',
                'category': categories_map.get('Cloud'),
                'status': CaseStudy.STATUS_PUBLISHED,
                'accent_color': '#0071e3',
                'primary_color': '#1d1d1f',
                'secondary_color': '#0a84ff',
                'bg_color': '#f5f5f7',
                'bg_secondary_color': '#e8e8ed',
                'featured': True,
                'problem_statement': 'The financial services firm was operating on outdated on-premise servers that were costly to maintain and prone to downtime, posing significant risks to business operations.',
                'objectives': 'Reduce infrastructure costs by 30%, achieve 99.99% uptime, and ensure compliance with financial industry regulations.',
                'business_challenge': 'Migrating a financial services firm requires careful consideration of security, compliance, and data integrity. Any disruption could result in significant financial and regulatory consequences.',
                'research_findings': 'The existing infrastructure cost $500K annually with 99.5% uptime. Cloud migration could reduce costs to $325K while achieving 99.99% uptime.',
                'user_needs': 'Secure data handling, regulatory compliance, minimal downtime, and cost-effective scaling.',
                'features': 'AWS migration, microservices architecture, CI/CD pipeline, automated backups, real-time monitoring, and compliance reporting.',
                'unique_features': 'End-to-end encryption, automated compliance auditing, and disaster recovery with sub-minute failover.',
            },
            {
                'name': 'Digital Transformation',
                'slug': 'digital-transformation',
                'tagline': 'Developed a comprehensive digital strategy for a healthcare provider, enabling telemedicine capabilities and streamlined patient management.',
                'description': 'We developed a comprehensive digital transformation strategy for a healthcare provider, enabling telemedicine capabilities and streamlined patient management. The project involved integrating telemedicine platforms, developing a patient portal, and implementing electronic health records. The result was improved patient outcomes and operational efficiency.',
                'overview': 'A holistic digital transformation that modernized healthcare delivery through technology integration and patient-centric design.',
                'category': categories_map.get('Digital Transformation'),
                'status': CaseStudy.STATUS_PUBLISHED,
                'accent_color': '#2b5f57',
                'primary_color': '#1d1d1f',
                'secondary_color': '#34c759',
                'bg_color': '#ffffff',
                'bg_secondary_color': '#f5f5f7',
                'featured': True,
                'problem_statement': 'The healthcare provider was struggling to meet growing patient demands with outdated systems. Patient engagement was low, and administrative processes were inefficient.',
                'objectives': 'Enable telemedicine capabilities, improve patient engagement by 50%, and streamline administrative processes.',
                'business_challenge': 'Healthcare regulations, patient privacy requirements, and the need for seamless integration with existing medical systems presented significant challenges.',
                'research_findings': 'Patient satisfaction scores were below industry average. 70% of patients preferred telemedicine options but the provider had no capabilities.',
                'user_needs': 'Secure patient data handling, intuitive patient portal, telemedicine integration, and efficient administrative workflows.',
                'features': 'Telemedicine platform, patient portal, electronic health records, appointment scheduling, prescription management, and analytics dashboard.',
                'unique_features': 'HIPAA-compliant architecture, AI-powered symptom checker, and integrated pharmacy system.',
            },
        ]

        created = 0
        for data in case_studies_data:
            category = data.pop('category', None)
            defaults = data.copy()
            defaults['category'] = category
            cs, was_created = CaseStudy.objects.update_or_create(
                slug=data['slug'],
                defaults=defaults
            )
            if was_created:
                self.stdout.write(self.style.SUCCESS(f'Created case study: {cs.name}'))
                created += 1
            else:
                self.stdout.write(self.style.WARNING(f'Case study already exists: {cs.name}'))

        self.stdout.write(self.style.SUCCESS(f'\nTotal case studies created/updated: {created}'))
