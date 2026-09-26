from django.db.models import Q, Count, Max
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.utils import timezone
from community.forms import CommentForm, ReplyForm
from community.models import (
    Category, Comment, Event, Post, Reply, Topic, Like, Dislike, MODERATION_APPROVED,
)
from home.models import Article, Newsletter, Profile, Comment as HomeComment, Reply as HomeReply
from app.models import CaseStudy

User = get_user_model()

# Tab filters that appear on the feed (labels come from Category rows).
FALLBACK_TABS = ['Technology', 'Software', 'Design', 'Career']


def _tabs():
    names = list(Category.objects.order_by('name').values_list('name', flat=True))
    return names or list(FALLBACK_TABS)


def _filter_topics(topics, tab, q):
    if tab and tab.lower() != 'all':
        topics = topics.filter(
            Q(category__name__iexact=tab)
            | Q(tags__name__iexact=tab)
            | Q(posts__category__iexact=tab)
        ).distinct()
    if q:
        topics = topics.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(category__name__icontains=q)
            | Q(posts__title__icontains=q)
            | Q(posts__content__icontains=q)
        ).distinct()
    return topics


def _site_stats():
    return {
        'members': User.objects.filter(is_active=True).count(),
        'topics': Topic.objects.count(),
        'replies': HomeReply.objects.count(),
        'resources': (
            Article.objects.filter(status='published', deleted=False).count()
            + CaseStudy.objects.filter(status=CaseStudy.STATUS_PUBLISHED).count()
            + Newsletter.objects.filter(status__in=['sent', 'scheduled']).count()
        ),
    }


def _seo(title, desc):
    return {
        'page_title': title,
        'seo_desc': desc[:500],
        'og_title': title,
        'og_desc': desc[:500],
        'og_type': 'website',
        'twitter_title': title,
        'twitter_desc': desc[:500],
    }


def _layout(section, **extra):
    upcoming_events = Event.objects.filter(
        is_published=True, starts_at__gte=timezone.now()
    ).count()
    ctx = {
        'section': section,
        'tabs': _tabs(),
        'stats': _site_stats(),
        'categories': Category.objects.all().order_by('name'),
        'current_year': timezone.now().year,
        'newsletter_count': Newsletter.objects.filter(status__in=['sent', 'scheduled']).count(),
        'case_study_count': CaseStudy.objects.filter(status=CaseStudy.STATUS_PUBLISHED).count(),
        'story_count': Article.objects.filter(status='published', deleted=False).count(),
        'upcoming_event_count': upcoming_events,
        'member_count': User.objects.filter(is_active=True).exclude(is_superuser=True).count(),
    }
    ctx.update(extra)
    return ctx


# ── HomeFeed: Feed ─────────────────────────────────────────────
def topic_list(request):
    tab = request.GET.get('tab', 'all')
    q = request.GET.get('q', '').strip()

    topics = Topic.objects.exclude(slug='').exclude(slug=None)
    topics = _filter_topics(topics, tab, q)

    featured_topic = None
    if tab == 'all' and not q:
        featured_topic = topics.filter(featured=True).order_by('-created_at').first() or topics.order_by('-created_at').first()
        if featured_topic:
            topics = topics.exclude(id=featured_topic.id)

    recent_topics = topics.order_by('-created_at')[:12]

    ctx = _layout(
        'feed',
        featured_topic=featured_topic,
        recent_topics=recent_topics,
        active_tab=tab,
        query=q,
        **_seo(
            'Community Hub',
            'Join the Dovetec Enterprises community hub. Discuss technology, software engineering, IT solutions, and digital transformation with experts in Nairobi, Kenya.',
        ),
    )
    return render(request, 'forum/topic_list.html', ctx)


# ── HomeFeed: Trending ─────────────────────────────────────────
def trending(request):
    q = request.GET.get('q', '').strip()
    tab = request.GET.get('tab', 'all')

    trending_topics = Topic.objects.exclude(slug='').exclude(slug=None)
    trending_topics = _filter_topics(trending_topics, tab, q)
    trending_topics = (
        trending_topics.annotate(
            post_count=Count('posts', filter=Q(posts__moderation_state=MODERATION_APPROVED), distinct=True),
            comment_count=Count('posts__comments', distinct=True),
            last_activity=Max('posts__created_at'),
        )
        .order_by('-post_count', '-comment_count', '-last_activity', '-created_at')[:12]
    )

    trending_posts = Post.objects.filter(moderation_state=MODERATION_APPROVED)
    if q:
        trending_posts = trending_posts.filter(
            Q(title__icontains=q) | Q(content__icontains=q) | Q(topic__name__icontains=q)
        )
    if tab and tab.lower() != 'all':
        trending_posts = trending_posts.filter(
            Q(topic__name__iexact=tab) | Q(category__iexact=tab) | Q(tags__name__iexact=tab)
        )
    trending_posts = trending_posts.annotate(
        reaction_count=Count('likes', distinct=True) + Count('dislikes', distinct=True),
        reply_count=Count('comments__replies', distinct=True),
    ).order_by('-reaction_count', '-reply_count', '-views', '-created_at')[:12]

    ctx = _layout(
        'trending',
        trending_topics=trending_topics,
        trending_posts=trending_posts,
        active_tab=tab,
        query=q,
        **_seo(
            'Trending Discussions | Community Hub',
            'Trending discussions and posts from the Dovetec Enterprises community — what professionals across East Africa are talking about now.',
        ),
    )
    return render(request, 'forum/trending.html', ctx)


# ── Resources: Knowledge Base already maps to help_center ─────

# ── Resources: Product Updates ─────────────────────────────────
def product_updates(request):
    q = request.GET.get('q', '').strip()
    updates = Newsletter.objects.filter(status__in=['sent', 'scheduled', 'draft'])
    if q:
        updates = updates.filter(Q(subject__icontains=q) | Q(content__icontains=q))
    updates = updates.order_by('-scheduled_for', '-created_at')[:24]

    latest_articles = Article.objects.filter(status='published', deleted=False)
    if q:
        latest_articles = latest_articles.filter(
            Q(title__icontains=q) | Q(seo_description__icontains=q) | Q(content__icontains=q)
        )
    latest_articles = latest_articles.order_by('-published_at', '-created_at')[:12]

    ctx = _layout(
        'product_updates',
        updates=updates,
        articles=latest_articles,
        query=q,
        **_seo(
            'Product Updates | Community Hub',
            'Latest features, improvements, and what is coming next from Dovetec Enterprises.',
        ),
    )
    return render(request, 'forum/product_updates.html', ctx)


# ── Resources: Get Inspired ────────────────────────────────────
def get_inspired(request):
    q = request.GET.get('q', '').strip()

    case_studies = CaseStudy.objects.filter(status=CaseStudy.STATUS_PUBLISHED)
    if q:
        case_studies = case_studies.filter(
            Q(name__icontains=q) | Q(tagline__icontains=q) | Q(description__icontains=q)
        )
    case_studies = case_studies.order_by('-featured', '-published_at', '-created_at')[:12]

    stories = Article.objects.filter(status='published', deleted=False)
    if q:
        stories = stories.filter(
            Q(title__icontains=q) | Q(seo_description__icontains=q) | Q(content__icontains=q)
        )
    stories = stories.order_by('-featured', '-published_at', '-created_at')[:12]

    ctx = _layout(
        'get_inspired',
        case_studies=case_studies,
        stories=stories,
        query=q,
        **_seo(
            'Get Inspired | Community Hub',
            'Stories, case studies, and ideas from Dovetec Enterprises to fuel your next project.',
        ),
    )
    return render(request, 'forum/get_inspired.html', ctx)


# ── Connect: Support already maps to contact_us ────────────────

# ── Connect: Events ────────────────────────────────────────────
def events(request):
    q = request.GET.get('q', '').strip()
    now = timezone.now()

    event_qs = Event.objects.filter(is_published=True)
    if q:
        event_qs = event_qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
            | Q(location__icontains=q) | Q(event_type__icontains=q)
        )

    upcoming = [e for e in event_qs if e.is_upcoming]
    past = sorted(
        [e for e in event_qs if not e.is_upcoming],
        key=lambda e: e.starts_at,
        reverse=True,
    )

    ctx = _layout(
        'events',
        upcoming_events=upcoming,
        past_events=past[:12],
        query=q,
        **_seo(
            'Events | Community Hub',
            'Webinars, workshops, and community meetups from Dovetec Enterprises and partners across East Africa.',
        ),
    )
    return render(request, 'forum/events.html', ctx)


# ── Connect: Directory ─────────────────────────────────────────
def directory(request):
    q = request.GET.get('q', '').strip()

    profiles = (
        Profile.objects.select_related('user')
        .filter(user__is_active=True)
        .order_by('user__first_name', 'user__last_name')
    )
    if q:
        profiles = profiles.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__email__icontains=q)
            | Q(title__icontains=q)
            | Q(bio__icontains=q)
        )

    members = []
    for profile in profiles:
        user = profile.user
        if user.is_superuser:
            continue
        members.append({
            'profile': profile,
            'name': user.get_full_name() or user.display_name,
            'title': profile.title or 'Community Member',
            'bio': profile.bio or '',
            'image': profile.image,
            'joined': user.date_joined,
        })

    ctx = _layout(
        'directory',
        members=members[:48],
        member_count=len(members),
        query=q,
        **_seo(
            'Community Directory | Community Hub',
            'Connect with professionals across East Africa in the Dovetec Enterprises community directory.',
        ),
    )
    return render(request, 'forum/directory.html', ctx)


# ── Topic / post detail & actions ──────────────────────────────
def topic_detail(request, topic_slug):
    topic = get_object_or_404(Topic, slug=topic_slug)
    posts = Post.objects.filter(topic=topic, moderation_state=MODERATION_APPROVED).order_by('-created_at')
    seo_desc = (topic.meta_description or topic.description
                or f'Discuss {topic.name} at the Dovetec Forum. Technology insights and software engineering discussions.')
    return render(request, 'forum/topic_detail.html', {
        'topic': topic,
        'posts': posts,
        'page_title': topic.meta_title or f'{topic.name} - Dovetec Forum | Software Engineering',
        'seo_desc': seo_desc[:500],
        'og_title': topic.og_title or f'{topic.name} - Dovetec Forum',
        'og_desc': (topic.og_description or seo_desc)[:500],
        'og_type': 'website',
        'twitter_title': topic.twitter_title or f'{topic.name} - Dovetec Forum',
        'twitter_desc': (topic.twitter_description or seo_desc)[:500],
    })


def post_detail(request, post_slug):
    """View function to display a specific post and its comments."""
    post = get_object_or_404(Post, slug=post_slug, moderation_state=MODERATION_APPROVED)
    comments = post.comments.filter(moderation_state=MODERATION_APPROVED).all()

    return render(request, 'post_detail.html', {
        'post': post,
        'comments': comments,
    })


@login_required
def add_comment(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug, moderation_state=MODERATION_APPROVED)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Comment.objects.create(article=post, user=request.user, content=content, moderation_state=MODERATION_APPROVED if request.user.groups.filter(name='Staff').exists() else 'pending')
            messages.success(request, 'Comment added successfully! Pending moderator approval.')
        else:
            messages.error(request, 'Comment cannot be empty.')
    return redirect('post_detail', post_slug=post.slug)


@login_required
def add_reply(request):
    if request.method == 'POST':
        comment_id = request.POST.get('comment_id')
        content = request.POST.get('content')
        parent_comment = get_object_or_404(Comment, id=comment_id, moderation_state=MODERATION_APPROVED)
        post = parent_comment.post

        if content:
            Reply.objects.create(
                comment=parent_comment,
                user=request.user,
                content=content,
                moderation_state=MODERATION_APPROVED if request.user.groups.filter(name='Staff').exists() else 'pending'
            )
            messages.success(request, 'Reply added successfully! Pending moderator approval.')
        else:
            messages.error(request, 'Reply cannot be empty.')

        return redirect('post_detail', post_slug=post.slug)

    return redirect('community')


@login_required
def toggle_like(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug, moderation_state=MODERATION_APPROVED)
    like, created = Like.objects.get_or_create(post=post, user=request.user)

    if not created:
        like.delete()

    return redirect('post_detail', post_slug=post.slug)


@login_required
def toggle_dislike(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug, moderation_state=MODERATION_APPROVED)
    dislike, created = Dislike.objects.get_or_create(post=post, user=request.user)

    if not created:
        dislike.delete()

    return redirect('post_detail', post_slug=post.slug)
