from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import models
from django.db.models import Q
from django.urls import reverse

# Create your views here.
from django.template import loader
from .models import *
from .crm import create_ticket
from shop.models import Product

# Create your views here.


from home.models import Article # Import Article model

# Create your views here.


def index(request):
    context = {
        'page_title': 'Dovetec Enterprises | Solving Workforce Complexities',
        'seo_desc': 'Leading technology company in Nairobi, Kenya. Dovetec Enterprises delivers software engineering, IT solutions, digital transformation, and consulting services.',
        'og_title': 'Dovetec Enterprises - Software Engineering & IT Solutions',
        'og_desc': 'Leading technology company in Nairobi, Kenya. Empowering businesses across East Africa.',
        'og_type': 'website',
        'twitter_title': 'Dovetec Enterprises - Software Engineering & IT Solutions',
        'twitter_desc': 'Leading technology company in Nairobi, Kenya.',
    }
    articles = Article.objects.filter(status='published').order_by('-created_at')[:14]
    context['articles'] = articles
    return render(request, 'app/index.html', context)

def about(request):
    context = {
        'page_title': 'About Us - Dovetec Enterprises',
        'seo_desc': 'Learn about Dovetec Enterprises - a leading provider of innovative technological solutions dedicated to solving complex challenges.',
        'og_title': 'About Us - Dovetec Enterprises',
        'og_desc': 'Learn about Dovetec Enterprises - a leading provider of innovative technological solutions.',
        'og_type': 'website',
        'twitter_title': 'About Us - Dovetec Enterprises',
        'twitter_desc': 'Learn about Dovetec Enterprises - a leading provider of innovative technological solutions.',
    }
    return render(request, 'about.html', context)

def contact(request):
    context = {
        'page_title': 'Contact Us - Dovetec Enterprises',
        'seo_desc': 'Contact Dovetec Enterprises for software engineering, IT solutions, and consulting services in Nairobi, Kenya.',
        'og_title': 'Contact Us - Dovetec Enterprises',
        'og_type': 'website',
        'twitter_title': 'Contact Us - Dovetec Enterprises',
        'twitter_desc': 'Contact Dovetec Enterprises for software engineering, IT solutions, and consulting services.',
        'industries': INDUSTRY_CHOICES,
        'budget_choices': ServiceInquiry.BUDGET_CHOICES,
        'service_choices': ServiceInquiry.SERVICE_CHOICES,
    }
    if request.method == 'POST':
        email = request.POST.get('email')
        message = request.POST.get('message')

        if email and message:
            ticket, uploaded_assets = create_ticket(
                subject=request.POST.get('subject', '').strip(),
                description=message,
                email=email,
                first_name=request.POST.get('fname', ''),
                last_name=request.POST.get('lname', ''),
                phone=request.POST.get('phone', ''),
                message=message,
                organization_name=request.POST.get('organization', ''),
                industry=request.POST.get('industry', ''),
                service=request.POST.get('service', 'other'),
                budget_range=request.POST.get('budget_range', ServiceInquiry.BUDGET_UNSPECIFIED),
                timeline=request.POST.get('timeline', ''),
                preferred_contact_method=request.POST.get('preferred_contact_method', 'email'),
                ticket_type=request.POST.get('ticket_type', Ticket.TYPE_ISSUE),
                attachments=request.FILES.getlist('attachments'),
                owner=request.user,
            )
            failed_uploads = sum(not stored for _, stored in uploaded_assets)
            message_text = (
                f'Thank you! Your request {ticket.reference} has been received '
                'and assigned to our team. We will get back to you shortly!'
            )
            if failed_uploads:
                message_text += f' {failed_uploads} attachment(s) could not be accepted.'
            messages.success(request, message_text)
            return redirect('contact_us')

    return render(request, 'app/contact.html', context)

def services(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        service = request.POST.get('service')
        message = request.POST.get('message')

        if name and email and service and message:
            first_name, _, last_name = name.strip().partition(' ')
            ticket, _ = create_ticket(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                service=service,
                message=message,
                organization_name=request.POST.get('organization', ''),
                industry=request.POST.get('industry', ''),
                budget_range=request.POST.get('budget_range', ServiceInquiry.BUDGET_UNSPECIFIED),
                timeline=request.POST.get('timeline', ''),
                preferred_contact_method=request.POST.get('preferred_contact_method', 'email'),
                source=ServiceInquiry.SOURCE_SERVICE_PAGE,
                ticket_type=Ticket.TYPE_ENQUIRY,
                attachments=request.FILES.getlist('attachments'),
                owner=request.user,
            )
            messages.success(
                request,
                f'Your inquiry {ticket.reference} has been submitted successfully. '
                'We will get back to you shortly!',
            )
            return redirect('services')

    context = {
        'page_title': 'Our Services - Dovetec Enterprises',
        'seo_desc': 'Explore our comprehensive range of software engineering, IT solutions, and consulting services at Dovetec Enterprises.',
        'og_title': 'Our Services - Dovetec Enterprises',
        'og_desc': 'Explore our comprehensive range of software engineering, IT solutions, and consulting services.',
        'og_type': 'website',
        'twitter_title': 'Our Services - Dovetec Enterprises',
        'twitter_desc': 'Explore our comprehensive range of software engineering, IT solutions, and consulting services.',
        'industries': INDUSTRY_CHOICES,
        'budget_choices': ServiceInquiry.BUDGET_CHOICES,
        'service_choices': ServiceInquiry.SERVICE_CHOICES,
    }
    return render(request, 'app/services.html', context)

def portfolio(request):
    context = {
        'page_title': 'Our Portfolio - Dovetec Enterprises',
        'seo_desc': 'Explore our portfolio of successful projects and case studies at Dovetec Enterprises.',
        'og_title': 'Our Portfolio - Dovetec Enterprises',
        'og_type': 'website',
        'twitter_title': 'Our Portfolio - Dovetec Enterprises',
        'twitter_desc': 'Explore our portfolio of successful projects and case studies.',
    }
    return render(request, 'app/portfolio.html', context)

def portfolio_showcase(request):
    case_studies = CaseStudy.objects.filter(status=CaseStudy.STATUS_PUBLISHED).order_by('-featured', '-published_at')
    context = {
        'page_title': 'Case Studies | Dovetec Enterprises',
        'seo_desc': 'Explore our portfolio of successful case studies and client transformations at Dovetec Enterprises.',
        'og_title': 'Case Studies - Dovetec Enterprises',
        'og_desc': 'Explore our portfolio of successful case studies and client transformations.',
        'og_type': 'website',
        'twitter_title': 'Case Studies - Dovetec Enterprises',
        'twitter_desc': 'Explore our portfolio of successful case studies and client transformations.',
        'case_studies': case_studies,
    }
    return render(request, 'app/portfolio-case-studies.html', context)

def case_study_detail(request, slug):
    case_study = get_object_or_404(CaseStudy, slug=slug, status=CaseStudy.STATUS_PUBLISHED)
    cs = case_study
    accent = cs.accent_color
    primary = cs.primary_color
    secondary = cs.secondary_color
    bg = cs.bg_color
    bg_secondary = cs.bg_secondary_color
    gradient = cs.gradient_css
    
    # Parse JSON fields if needed
    import json
    def parse_json_field(text):
        try:
            return json.loads(text) if text else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    persona = parse_json_field(cs.persona_data)
    matrix = parse_json_field(cs.matrix_data)
    competitor_sections = parse_json_field(cs.competitor_data)
    
    # Build section data for template
    sections = []
    if cs.problem_statement:
        sections.append({'number': '01', 'title': 'Problem Statement', 'content': cs.problem_statement})
    if cs.objectives:
        sections.append({'number': '02', 'title': 'Objectives & Goals', 'content': cs.objectives})
    if cs.business_challenge:
        sections.append({'number': '03', 'title': 'Business Challenge', 'content': cs.business_challenge})
    if cs.research_findings:
        sections.append({'number': '04', 'title': 'Quantitative Research', 'content': cs.research_findings})
    if cs.user_needs:
        sections.append({'number': '05', 'title': 'User Needs', 'content': cs.user_needs})
    if cs.features:
        sections.append({'number': '06', 'title': 'Features & Functionalities', 'content': cs.features})
    if cs.user_challenges:
        sections.append({'number': '07', 'title': 'Product User Challenges', 'content': cs.user_challenges})
    if cs.unique_features:
        sections.append({'number': '08', 'title': 'Unique Features', 'content': cs.unique_features})
    if cs.task_mapping:
        sections.append({'number': '09', 'title': 'Task Mapping', 'content': cs.task_mapping})
    if cs.root_cause:
        sections.append({'number': '10', 'title': 'Root Cause Analysis', 'content': cs.root_cause})
    if cs.task_flows:
        sections.append({'number': '11', 'title': 'Task Flows', 'content': cs.task_flows})
    if cs.sketches:
        sections.append({'number': '12', 'title': 'Sketches', 'content': cs.sketches})
    if cs.major_screens:
        sections.append({'number': '13', 'title': 'Major Screens', 'content': cs.major_screens})
    if cs.screens:
        sections.append({'number': '14', 'title': 'Screens', 'content': cs.screens})
    
    context = {
        'page_title': f'{cs.name} | Case Study - Dovetec Enterprises',
        'seo_desc': cs.description[:160] if cs.description else f'Case study: {cs.name} by Dovetec Enterprises.',
        'og_title': f'{cs.name} | Case Study',
        'og_desc': cs.description[:160] if cs.description else f'Explore the {cs.name} case study.',
        'og_type': 'article',
        'og_image': cs.hero_image.url if cs.hero_image else '',
        'twitter_title': f'{cs.name} | Case Study',
        'twitter_desc': cs.description[:160] if cs.description else f'Explore the {cs.name} case study.',
        'cs': cs,
        'sections': sections,
        'accent': accent,
        'primary': primary,
        'secondary': secondary,
        'bg': bg,
        'bg_secondary': bg_secondary,
        'gradient': gradient,
        'persona': persona,
        'matrix': matrix,
        'competitor_sections': competitor_sections,
    }
    return render(request, 'app/case-study-detail.html', context)

# Portfolio Massionary
def portfolio_massionry(request):
    context = {
        'page_title': 'Portfolio - Dovetec Enterprises',
        'seo_desc': 'Portfolio massionry and project showcase from Dovetec Enterprises.',
        'og_title': 'Portfolio - Dovetec Enterprises',
        'og_type': 'website',
        'twitter_title': 'Portfolio - Dovetec Enterprises',
        'twitter_desc': 'Portfolio massionry and project showcase from Dovetec Enterprises.',
    }
    return render(request, 'app/portfolio-masonry.html', context)
# Case Studies
def case_study(request, slug=None):
    if slug:
        return case_study_detail(request, slug)
    case_studies = CaseStudy.objects.filter(status=CaseStudy.STATUS_PUBLISHED).order_by('-featured', '-published_at')
    context = {
        'page_title': 'Case Studies | Dovetec Enterprises',
        'seo_desc': 'Explore our portfolio of successful case studies and client transformations at Dovetec Enterprises.',
        'og_title': 'Case Studies - Dovetec Enterprises',
        'og_desc': 'Explore our portfolio of successful case studies and client transformations.',
        'og_type': 'website',
        'twitter_title': 'Case Studies - Dovetec Enterprises',
        'twitter_desc': 'Explore our portfolio of successful case studies and client transformations.',
        'case_studies': case_studies,
    }
    return render(request, 'app/portfolio-case-studies.html', context)
# Join our team
def join_our_team(request):
    context = {
        'page_title': 'Join Our Team - Dovetec Enterprises',
        'seo_desc': 'Join the Dovetec Enterprises team. Explore career opportunities in software engineering, IT solutions, design, and consulting.',
        'og_title': 'Join Our Team - Dovetec Enterprises',
        'og_desc': 'Join the Dovetec Enterprises team and shape the future of technology.',
        'og_type': 'website',
        'twitter_title': 'Join Our Team - Dovetec Enterprises',
        'twitter_desc': 'Join the Dovetec Enterprises team and shape the future of technology.',
    }
    return render(request, 'app/join-our-team.html', context)
# Product Demo
def product_demo(request):
    context = {
        'page_title': 'Request a Product Demo - Dovetec Enterprises',
        'seo_desc': 'Request a product demo from Dovetec Enterprises. See our software solutions in action.',
        'og_title': 'Request a Product Demo - Dovetec Enterprises',
        'og_desc': 'See our software solutions in action with a product demo.',
        'og_type': 'website',
        'twitter_title': 'Request a Product Demo - Dovetec Enterprises',
        'twitter_desc': 'See our software solutions in action with a product demo.',
    }
    return render(request, 'app/product-demo.html', context)

# Gallery
def gallery(request):
    context = {
        'page_title': 'Gallery - Dovetec Enterprises',
        'seo_desc': 'Explore our rich gallery of projects, events, and team moments at Dovetec Enterprises.',
        'og_title': 'Gallery - Dovetec Enterprises',
        'og_desc': 'Explore our rich gallery of projects, events, and team moments.',
        'og_type': 'website',
        'twitter_title': 'Gallery - Dovetec Enterprises',
        'twitter_desc': 'Explore our rich gallery of projects, events, and team moments.',
    }
    return render(request, 'app/gallery.html', context)

# Gallery
def products(request):
    context = {
        'page_title': 'Our Products - Dovetec Enterprises',
        'seo_desc': 'Browse our products at Dovetec Enterprises. Software solutions and IT services from Kenya.',
        'og_title': 'Our Products - Dovetec Enterprises',
        'og_desc': 'Browse our products at Dovetec Enterprises.',
        'og_type': 'website',
        'twitter_title': 'Our Products - Dovetec Enterprises',
        'twitter_desc': 'Browse our products at Dovetec Enterprises.',
    }
    products = Product.objects.all().order_by('-created_at')
    return render(request, 'app/products.html', context)

# Careers
def careers(request):
    context = {
        'page_title': 'Careers - Dovetec Enterprises',
        'seo_desc': 'Join the Dovetec Enterprises team. Explore career opportunities in software engineering, IT solutions, design, and consulting in Nairobi, Kenya.',
        'og_title': 'Careers - Dovetec Enterprises',
        'og_desc': 'Join the Dovetec Enterprises team. Explore career opportunities.',
        'og_type': 'website',
        'twitter_title': 'Careers - Dovetec Enterprises',
        'twitter_desc': 'Join the Dovetec Enterprises team.',
    }
    return render(request, 'app/careers.html', context)


# ── Feature-request board (public) ─────────────────────────────────

def feature_board(request):
    """Public feature board with status filter, search, and upvotes."""
    features = FeatureRequest.objects.filter(status__in=FeatureRequest.PUBLIC_STATUSES)
    status_f = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()
    if status_f and status_f in dict(FeatureRequest.STATUS_CHOICES):
        features = features.filter(status=status_f)
    if q:
        features = features.filter(Q(title__icontains=q) | Q(description__icontains=q))

    voted_ids = set()
    if request.user.is_authenticated:
        voted_ids = set(
            FeatureVote.objects.filter(user=request.user)
            .values_list('feature_request_id', flat=True)
        )

    context = {
        'page_title': 'Feature Requests - Dovetec Enterprises',
        'seo_desc': 'Vote on and discuss product feature requests for the Dovetec client portal and platform.',
        'og_title': 'Feature Requests - Dovetec Enterprises',
        'og_desc': 'Tell us what to build next. Upvote ideas and track roadmap status.',
        'og_type': 'website',
        'twitter_title': 'Feature Requests - Dovetec Enterprises',
        'twitter_desc': 'Tell us what to build next.',
        'features': features,
        'status_f': status_f,
        'q': q,
        'status_choices': FeatureRequest.STATUS_CHOICES,
        'category_choices': FeatureRequest.CATEGORY_CHOICES,
        'voted_ids': voted_ids,
    }
    return render(request, 'features.html', context)


def feature_detail(request, slug):
    feature = get_object_or_404(
        FeatureRequest, slug=slug, status__in=FeatureRequest.PUBLIC_STATUSES,
    )
    context = {
        'page_title': f'{feature.title} - Feature Requests',
        'seo_desc': feature.description[:160],
        'og_title': feature.title,
        'og_desc': feature.description[:160],
        'og_type': 'article',
        'twitter_title': feature.title,
        'twitter_desc': feature.description[:160],
        'feature': feature,
        'has_voted': feature.user_has_voted(request.user),
        'status_choices': FeatureRequest.STATUS_CHOICES,
        'category_choices': FeatureRequest.CATEGORY_CHOICES,
    }
    return render(request, 'feature_detail.html', context)


def feature_vote(request, slug):
    """Toggle an upvote for the current user (auth required)."""
    feature = get_object_or_404(
        FeatureRequest, slug=slug, status__in=FeatureRequest.PUBLIC_STATUSES,
    )
    if request.method != 'POST':
        return redirect('feature_detail', slug=feature.slug)
    if not request.user.is_authenticated:
        messages.info(request, 'Log in to vote on feature requests.')
        return redirect(f"{reverse('login_view')}?next={reverse('feature_detail', args=[feature.slug])}")

    vote = FeatureVote.objects.filter(user=request.user, feature_request=feature).first()
    if vote:
        vote.delete()
        FeatureRequest.objects.filter(pk=feature.pk).exclude(vote_count=0).update(
            vote_count=models.F('vote_count') - 1
        )
        messages.info(request, 'Vote removed.')
    else:
        FeatureVote.objects.create(user=request.user, feature_request=feature)
        FeatureRequest.objects.filter(pk=feature.pk).update(vote_count=models.F('vote_count') + 1)
        messages.success(request, 'Vote counted — thanks!')
    return redirect('feature_detail', slug=feature.slug)


def feature_create(request):
    """Authenticated users can suggest a new feature."""
    if not request.user.is_authenticated:
        messages.info(request, 'Log in to suggest a feature.')
        return redirect(f"{reverse('login_view')}?next={reverse('feature_board')}")
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', FeatureRequest.CATEGORY_OTHER)
        if not title or not description:
            messages.error(request, 'Title and description are required.')
        else:
            if category not in dict(FeatureRequest.CATEGORY_CHOICES):
                category = FeatureRequest.CATEGORY_OTHER
            feature = FeatureRequest.objects.create(
                title=title[:200],
                description=description,
                category=category,
                author=request.user,
            )
            messages.success(request, f'“{feature.title}” submitted — thank you!')
            return redirect('feature_detail', slug=feature.slug)
    context = {
        'page_title': 'Suggest a Feature - Dovetec Enterprises',
        'seo_desc': 'Suggest a feature for the Dovetec platform and client portal.',
        'og_title': 'Suggest a Feature',
        'og_type': 'website',
        'twitter_title': 'Suggest a Feature',
        'category_choices': FeatureRequest.CATEGORY_CHOICES,
    }
    return render(request, 'feature_form.html', context)