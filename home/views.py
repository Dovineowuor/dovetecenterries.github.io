import hashlib
import logging
import base64
import uuid
import secrets
import string
from django.core.cache import cache
from datetime import datetime, timezone
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Q
from .form import RegistrationForm
from .models import Newsletter, NewsletterSubscription, NewsletterLog, User, Profile
from shop.models import Product

from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.contrib.auth.forms import AuthenticationForm
from community.forms import CommentForm
from community.models import Post, Topic
from home.form import ArticleForm
from .models import Article, Comment, Profile, Reply, Tag
from django.contrib.auth import authenticate, login
from django.urls import reverse
from django.utils import timezone

def unhash_author_id(hashed_id):
    """Reverse the hashing process of the author_id."""
    for user in User.objects.all():
        if hashlib.md5(str(user.id).encode()).hexdigest() == hashed_id:
            return user.id
    return None
def authors(request):
    authors = Profile.objects.all()
    context = {
        'authors': authors
    }
    return render(request, 'authors.html', context)

def author(request, hashed_id):
    # Fetch the author's profile using the hashed_id directly
    profile = get_object_or_404(Profile, user__id=hashed_id)
    
    # Fetch articles written by the author
    articles_by_author = Article.objects.filter(author=profile)
    
    # Fetch related articles based on tags or categories
    related_articles = Article.objects.filter(tags__in=articles_by_author.values('tags')).exclude(author=profile)
    
    # Fetch all tags associated with the author's articles for display
    author_tags = Tag.objects.filter(article__author=profile).distinct()

    context = {
        'author': profile.user,
        'articles_by_author': articles_by_author,
        'related_articles': related_articles,
        'author_tags': author_tags,
    }

    return render(request, 'author.html', context)

def generate_otp(length=6):
    """Generate a cryptographically secure OTP of specified length."""
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def register_view(request):
    if request.user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Get cleaned data from form
                email = form.cleaned_data['email']
                password = form.cleaned_data['password']
                first_name = form.cleaned_data['first_name']
                last_name = form.cleaned_data['last_name']

                # Set is_active to False initially
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=False
                )

                # Create verification token and OTP
                token = str(uuid.uuid4())
                otp = generate_otp()
                
                                # Create or update user profile with verification info
                profile, _ = Profile.objects.get_or_create(
                    user=user,
                    defaults={
                        'token': token,
                        'otp': otp,
                        'is_verified': False,
                        'otp_timestamp': timezone.now()
                    }
                )
                # Update fields if profile already existed (created by signal)
                profile.token = token
                profile.otp = otp
                profile.is_verified = False
                profile.otp_timestamp = timezone.now()
                profile.save()

                verification_link = request.build_absolute_uri(f'/verify/{token}/')
            
                # Render the verification email template
                email_context = {
                    'verification_link': verification_link,
                    'user': user,
                    'otp': otp
                }
                message = render_to_string('verify_account.html', email_context)

                send_mail(
                    'Verify your email',
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                    html_message=message  # Send the HTML version
                )

                profile.otp = otp
                profile.save()

                messages.success(request, 'Registration successful. Please check your email for verification.')
                return redirect('/login/')

            except Exception as e:
                print(e)
                messages.error(request, 'Something went wrong during registration. Please try again.')
                return render(request, 'register.html', {'form': form})
    else:
        form = RegistrationForm()

    return render(request, 'register.html', {'form': form})

def verify(request, token):
    """Verify email using token and OTP."""
    profile_obj = get_object_or_404(Profile, token=token)
    user = profile_obj.user
    verified = profile_obj.is_verified

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        if profile_obj.otp == entered_otp:
            # Mark user and profile as verified
            profile_obj.is_verified = True
            profile_obj.user.is_active = True
            profile_obj.save()
            profile_obj.user.save()
            
            # Auto-subscribe user to newsletter on verification
            NewsletterSubscription.objects.get_or_create(
                email=user.email,
                defaults={'user': user}
            )
            
            messages.success(request, 'Your email has been verified successfully. You can now log in.')
            return redirect('login_view')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
    
    # For GET request, show verification page
    context = {
        'verified': verified,
        'user': user,
    }
    return render(request, "verify_email.html", context)

def logout_view(request):
    logout(request)
    return redirect('/')

def home(request):
    # Fetch all published articles that are not scheduled for future
    articles = Article.objects.filter(
        status='published', 
        deleted=False
    ).filter(
        Q(scheduled_at__isnull=True) | Q(scheduled_at__lte=timezone.now())
    ).order_by('-created_at')
    categories = Article.objects.filter(status='published', deleted=False).values_list('category', flat=True).distinct()
    context = {
        'blogs': articles,
        'articles': articles,
        'categories': categories,
    }
    return render(request, 'app/index.html', context)

def is_safe_url(url, request):
    """Check if a URL is safe to redirect to (local only)."""
    from urllib.parse import urlparse
    if not url or not url.startswith('/'):
        return False
    parsed = urlparse(url)
    return not parsed.netloc or parsed.netloc == request.get_host()


def login_view(request):
    """
    Handle user authentication using the custom User model with email.
    """
    if request.user.is_authenticated:
        return redirect(request.GET.get('next', '/'))
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email or not password:
            messages.error(request, 'Please enter both email and password.')
            return render(request, 'app/login.html')

        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                messages.error(request, 'Your account is not activated. Please check your email for verification instructions.')
                return render(request, 'app/login.html')
            
            # Authenticate the user
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                next_page = request.GET.get('next', '/')
                if not is_safe_url(next_page, request):
                    next_page = '/'
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                return redirect(next_page)
            else:
                messages.error(request, 'Invalid password.')
        except User.DoesNotExist:
            messages.error(request, 'Invalid email address.')
            return render(request, 'app/login.html')
    
    return render(request, 'app/login.html')

def blog_detail(request, slug):
    context = {
        'page_title': 'Article Detail',
        'seo_desc': 'Read the full article on Dovetec Enterprises.',
        'og_type': 'article',
    }
    try:
        article_obj = get_object_or_404(Article, slug=slug)
        context['article_obj'] = article_obj
        if article_obj.meta_title:
            context['page_title'] = article_obj.meta_title
        if article_obj.og_title:
            context['page_title'] = article_obj.og_title
        if article_obj.meta_description:
            context['seo_desc'] = article_obj.meta_description
        if article_obj.og_description:
            context['seo_desc'] = article_obj.og_description
        if article_obj.og_image:
            context['og_image'] = article_obj.og_image.url
        
        related_articles = Article.objects.filter(
            status='published', deleted=False
        ).exclude(
            id=article_obj.id
        ).order_by('-created_at')[:4]
        
        if len(related_articles) < 4:
            remaining = 4 - len(related_articles)
            random_articles = Article.objects.filter(
                status='published', deleted=False
            ).exclude(
                id=article_obj.id
            ).exclude(
                id__in=[a.id for a in related_articles]
            ).order_by('?')[:remaining]
            related_articles = list(related_articles) + list(random_articles)
            
        context['related_articles'] = related_articles
        context['all_categories'] = Article.objects.values_list('category', flat=True).distinct()
        context['all_tags'] = Tag.objects.all()
        
    except Exception as e:
        print(f"Error in blog_detail: {e}")
        context['error'] = "An error occurred while loading the article."
        
    return render(request, 'blog_detail.html', context)

def featured_articles(request):
    """
    View to display featured articles.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The rendered template with featured articles.
    """
    featured_articles = Article.objects.filter(featured=True)
    context = {
        'featured_articles': featured_articles
    }
    return render(request, 'forum/featured_articles.html', context)

def trending_articles(request):
    """
    View to display trending articles based on views.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The rendered template with trending articles.
    """
    trending_articles = Article.objects.order_by('-views')[:10]
    context = {
        'trending_articles': trending_articles
    }
    return render(request, 'forum/trending_articles.html', context)

def latest_articles(request):
    context = {
        'page_title': 'Latest Articles - Dovetec Enterprises',
        'seo_desc': 'Read the latest articles on technology, software engineering, and IT solutions from Dovetec Enterprises.',
        'og_title': 'Latest Articles - Dovetec Enterprises',
        'og_type': 'website',
    }
    latest_articles = Article.objects.order_by('-created_at')[:10]
    context['latest_articles'] = latest_articles
    return render(request, 'latest_articles.html', context)

def popular_articles(request):
    context = {
        'page_title': 'Popular Articles - Dovetec Enterprises',
        'seo_desc': 'The most popular articles based on likes at Dovetec Enterprises.',
        'og_title': 'Popular Articles - Dovetec Enterprises',
        'og_type': 'website',
    }
    popular_articles = Article.objects.order_by('-likes')[:10]
    context['popular_articles'] = popular_articles
    return render(request, 'forum/popular_articles.html', context)

def most_commented_articles(request):
    context = {
        'page_title': 'Most Commented Articles - Dovetec Enterprises',
        'seo_desc': 'The most commented articles at Dovetec Enterprises. Join the discussion.',
        'og_title': 'Most Commented Articles - Dovetec Enterprises',
        'og_type': 'website',
    }
    most_commented_articles = Article.objects.annotate(num_comments=Count('comments')).order_by('-num_comments')[:10]
    context['most_commented_articles'] = most_commented_articles
    return render(request, 'forum/most_commented_articles.html', context)

def random_articles(request):
    context = {
        'page_title': 'Random Articles - Dovetec Enterprises',
        'seo_desc': 'Randomly selected articles from Dovetec Enterprises.',
        'og_title': 'Random Articles - Dovetec Enterprises',
        'og_type': 'website',
    }
    random_articles = Article.objects.order_by('?')[:10]
    context['random_articles'] = random_articles
    return render(request, 'forum/random_articles.html', context)



# Set up logging
logger = logging.getLogger(__name__)

def see_blog(request):
    context = {
        'page_title': 'Insights & Tech Articles',
        'seo_desc': 'Latest technology insights, software engineering tips, and IT solutions from Dovetec Enterprises. Explore articles on digital transformation, cloud computing, and more.',
        'og_title': 'Insights & Tech Articles - Dovetec Enterprises',
        'og_desc': 'Latest technology insights from Dovetec Enterprises.',
        'og_image': f'{request.build_absolute_uri("/")}static/images/logo-dovetek.png',
        'og_type': 'website',
        'twitter_title': 'Insights & Tech Articles - Dovetec Enterprises',
        'twitter_desc': 'Latest technology insights from Dovetec Enterprises.',
    }
    try:
        # Base Query: All published and not-scheduled articles
        article_objs = Article.objects.filter(
            status='published',
            deleted=False
        ).filter(
            Q(scheduled_at__isnull=True) | Q(scheduled_at__lte=timezone.now())
        ).order_by('-created_at')
        
        # If user is logged in, also show their draft articles
        if request.user.is_authenticated:
            user_articles = Article.objects.filter(user=request.user, status='draft')
            article_objs = (article_objs | user_articles).order_by('-created_at')
            context['author'] = request.user

        # Paginate the article list
        from django.core.paginator import Paginator
        paginator = Paginator(article_objs, 9)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        # Get the main (hero) article — most recent published
        main_article = article_objs.first()
        
        # Get featured articles (next 4 most recent after hero)
        featured_articles = list(article_objs[1:5]) if article_objs.count() > 1 else []
        
        # If we don't have enough featured articles, fill with random published ones
        if len(featured_articles) < 4:
            remaining = 4 - len(featured_articles)
            exclude_ids = [a.id for a in featured_articles]
            if main_article:
                exclude_ids.append(main_article.id)
            random_articles = Article.objects.filter(
                status='published', deleted=False
            ).exclude(id__in=exclude_ids).order_by('?')[:remaining]
            featured_articles = featured_articles + list(random_articles)
            
        context['article_obj'] = main_article
        context['featured_articles'] = featured_articles[:4]
        context['page_obj'] = page_obj
        context['articles'] = page_obj

        # Fetch all categories and tags for the sidebar
        all_categories = Article.objects.filter(status='published', deleted=False).values_list('category', flat=True).distinct()
        all_tags = Tag.objects.all()
        context['all_categories'] = all_categories
        context['all_tags'] = all_tags

    except Exception as e:
        logger.error(f"Error fetching blog articles: {e}")
        context['error'] = "An error occurred while fetching your blog articles. Please try again later."

    return render(request, 'blog_list.html', context)

def add_blog(request):
    context = {'form': ArticleForm()}
    
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)  # Include files in the form instance
        
        if form.is_valid():
            try:
                article_obj = form.save(commit=False)  # Don't save to the database yet
                article_obj.user = request.user if request.user.is_authenticated else None
                article_obj.status = 'draft' # Force to pending review
                article_obj.save()  # Now save the blog object
                form.save_m2m() # Ensure many-to-many tags are saved

                messages.success(request, 'Your article has been submitted and is pending review by the Dovetec team.')
                # Redirect to the blog list page after successful submission
                return redirect('see_blog')
            
            except Exception as e:
                print(f"Error adding blog: {e}")
                context['error'] = "An error occurred while adding the blog. Please try again."

        # If the form is not valid, pass it back to the context for rendering
        context['form'] = form

    return render(request, 'add_blog.html', context)


def blog_update(request, slug):
    context = {}
    try:
        article_obj = get_object_or_404(Article, slug=slug)

        if article_obj.user != request.user:
            return redirect('/')

        initial_dict = {'content': article_obj.content}
        form = ArticleForm(initial=initial_dict)
        if request.method == 'POST':
            form = ArticleForm(request.POST)
            image = request.FILES.get('image', '')
            title = request.POST.get('title')
            user = request.user

            if form.is_valid():
                content = form.cleaned_data['content']
                article_obj.title = title
                article_obj.content = content
                article_obj.image = image
                article_obj.save()

        context['article_obj'] = article_obj
        context['form'] = form
    except Exception as e:
        print(e)

    return render(request, 'update_blog.html', context)

def blog_delete(request, id):
    try:
        article_obj = get_object_or_404(Article, id=id)

        if article_obj.user == request.user:
            article_obj.delete()

    except Exception as e:
        print(e)

    return redirect('see_blog')



def profile(request):
    return render(request, 'profile.html', {
        'page_title': 'My Profile - Dovetec Enterprises',
        'seo_desc': 'View and edit your profile on Dovetec Enterprises.',
        'og_title': 'My Profile - Dovetec Enterprises',
        'og_type': 'website',
    })

def contact_us(request):
    """Legacy path — CRM intake lives in app.views.contact."""
    from app.views import contact as crm_contact
    return crm_contact(request)

def team(request):
    return render(request, 'team.html')



def advertise(request):
    return render(request, 'advertise.html')



def search(request):
    """
    Handles the search functionality for articles.

    This view function retrieves the search query from the request's GET parameters,
    performs a case-insensitive search on the title and content of articles, and
    returns the results to the 'search.html' template.

    Args:
        request (HttpRequest): The HTTP request object containing the search query.

    Returns:
        HttpResponse: The rendered 'search.html' template with the search query and
                      the list of articles matching the search criteria.

    Context:
        query (str): The search query string.
        articles (Page): The paginated page object containing the list of articles
                         matching the search criteria.
    """
    query = request.GET.get('q', '')  # Retrieve the search query from GET parameters
    articles = Article.objects.none()  # Initialize an empty queryset to avoid errors

    if query:
        # Use Q objects to perform a case-insensitive search on the title and content fields
        articles = Article.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).distinct()  # Use distinct() to eliminate duplicate entries

    # Paginate the results, displaying 10 articles per page
    paginator = Paginator(articles, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'query': query,
        'articles': page_obj,
        'page_title': f'Search Results for "{query}" - Dovetec Enterprises',
        'seo_desc': f'Search results for "{query}" at Dovetec Enterprises.',
        'og_title': f'Search Results for "{query}" - Dovetec Enterprises',
        'og_desc': f'Search results for "{query}" at Dovetec Enterprises.',
        'og_type': 'website',
        'twitter_title': f'Search Results for "{query}" - Dovetec Enterprises',
        'twitter_desc': f'Search results for "{query}" at Dovetec Enterprises.',
    }

    # Render the search results page with the context
    return render(request, 'search.html', context)

def category(request, category):
    """
    Handles the request to display articles belonging to a specific category.
    """
    context = {
        'page_title': f'Category: {category} - Dovetec Enterprises',
        'seo_desc': f'Browse all articles in the "{category}" category at Dovetec Enterprises. Technology insights and IT solutions.',
        'og_title': f'Category: {category} - Dovetec Enterprises',
        'og_desc': f'Browse all articles in the "{category}" category.',
        'og_type': 'website',
        'twitter_title': f'Category: {category} - Dovetec Enterprises',
        'twitter_desc': f'Browse all articles in the "{category}" category.',
    }
    try:
        articles = Article.objects.filter(category__iexact=category)
        all_categories = Article.objects.values_list('category', flat=True).distinct()
        all_tags = Tag.objects.all()
        context.update({
            'articles': articles,
            'category': category,
            'all_categories': all_categories,
            'all_tags': all_tags,
        })
        return render(request, 'category.html', context)
    except Exception as e:
        logger.error(f"Error fetching category articles: {e}")
        context['error'] = "An error occurred while fetching articles."
        return render(request, 'category.html', context)

def tag(request, tag):
    """
    Display articles associated with a specific tag.
    """
    context = {
        'page_title': f'#{tag} Articles - Dovetec Enterprises',
        'seo_desc': f'Explore all articles tagged with #{tag} at Dovetec Enterprises.',
        'og_title': f'Articles tagged #{tag} - Dovetec Enterprises',
        'og_desc': f'Explore all articles tagged with #{tag}.',
        'og_type': 'website',
        'twitter_title': f'Articles tagged #{tag} - Dovetec Enterprises',
        'twitter_desc': f'Explore all articles tagged with #{tag}.',
    }
    try:
        articles = Article.objects.filter(
            tags__name=tag,
            status='published',
            deleted=False,
        ).order_by('-created_at').distinct()
        all_categories = Article.objects.filter(
            status='published', deleted=False
        ).values_list('category', flat=True).distinct()
        all_tags = Tag.objects.all().order_by('name')
        context.update({
            'tag': tag,
            'articles': articles,
            'all_categories': all_categories,
            'all_tags': all_tags,
        })
        return render(request, 'tag.html', context)
    except Exception as e:
        logger.error(f"Error fetching tag articles: {e}")
        context['error'] = "An error occurred while fetching tagged articles."
        return render(request, 'tag.html', context)

def tags(request):
    context = {
        'tags': Tag.objects.all()
    }
    return render(request, 'tags.html', context)

def like(request, id):
    """Handle the liking of an article by a user."""
    article = get_object_or_404(Article, id=id)
    if request.user.is_authenticated:
        if not Like.objects.filter(user=request.user, article=article).exists():
            Like.objects.create(user=request.user, article=article)
            article.likes += 1
            article.save()
            messages.success(request, 'You liked this article.')
        else:
            messages.error(request, 'You have already liked this article.')
    else:
        messages.error(request, 'You must be logged in to like articles.')
    return redirect('blog_detail', slug=article.slug)

def dislike(request, id):
    """Handle the dislike action for an article."""
    article = get_object_or_404(Article, id=id)
    if request.user.is_authenticated:
        if not Dislike.objects.filter(user=request.user, article=article).exists():
            Dislike.objects.create(user=request.user, article=article)
            article.likes -= 1
            article.save()
            messages.success(request, 'You disliked this article.')
        else:
            messages.error(request, 'You have already disliked this article.')
    else:
        messages.error(request, 'You must be logged in to dislike articles.')
    return redirect('blog_detail', slug=article.slug)



# @login_required(login_url='login_view')  # Redirects to 'login_view' if not authenticated
def add_comment(request, post_slug):
    """
    Handle the addition of a comment to an article.
    """

    article = get_object_or_404(Article, slug=post_slug)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.article = article
            comment.user = request.user
            comment.save()
            messages.success(request, 'Comment added successfully.')
            return redirect('blog_detail', slug=article.slug)
        else:
            messages.error(request, 'There was an error adding your comment.')
    return redirect('blog_detail', slug=article.slug)

def add_reply(request, comment_id):
    """
    Add a reply to a specific comment.

    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.
        comment_id (int): The ID of the comment to which the reply is being added.

    Returns:
        HttpResponse: A redirect to the article detail page.

    Behavior:
        - If the request method is POST, it attempts to retrieve the 'content' from the POST data.
        - If 'content' is present, it creates a new Reply object associated with the comment and the current user.
        - If 'content' is empty, it adds an error message indicating that the reply content cannot be empty.
        - In both cases, it redirects to the article detail page.
        - If the request method is not POST, it simply redirects to the article detail page.
    """
    comment = get_object_or_404(Comment, id=comment_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Reply.objects.create(comment=comment, user=request.user, content=content)
            messages.success(request, 'Reply added successfully.')
        else:
            messages.error(request, 'Reply content cannot be empty.')
        return redirect('blog_detail', slug=comment.article.slug)
    return redirect('blog_detail', slug=comment.article.slug)

@login_required(login_url='login_view')  # Redirects to 'login_view' if not authenticated
def delete_reply(request, id):
    """
    Delete a specific reply.
    Args:
        request (HttpRequest): The HTTP request object.
        id (int): The ID of the reply to be deleted.
    Returns:
        HttpResponseRedirect: Redirects to the article detail page.
    Raises:
        Http404: If the reply with the given ID does not exist.
    Messages:
        Success: If the reply is deleted successfully.
        Error: If the user does not have permission to delete the reply.
    """
    """Delete a specific reply."""
    reply = get_object_or_404(Reply, id=id)
    if request.user == reply.user:
        reply.delete()
        messages.success(request, 'Reply deleted successfully.')
    else:
        messages.error(request, 'You do not have permission to delete this reply.')
    
    return redirect('blog_detail', slug=reply.comment.article.slug)

@login_required(login_url='login_view')  # Redirects to 'login_view' if not authenticated
def edit_reply(request, id):
    """
    Edit a specific reply.
    Args:
        request (HttpRequest): The HTTP request object.
        id (int): The ID of the reply to be edited.
    Returns:
        HttpResponse: The HTTP response object.
    The function retrieves the reply object based on the provided ID. If the request method is POST and the user is the owner of the reply, it updates the reply content and saves it. If the update is successful, it redirects to the article detail page and displays a success message. If the user does not have permission to edit the reply, it displays an error message. If the request method is not POST, it renders the edit reply page with the reply object.
    """
    reply = get_object_or_404(Reply, id=id)
    
    if request.method == 'POST':
        if request.user == reply.user:
            reply.content = request.POST.get('content')
            reply.save()
            messages.success(request, 'Reply updated successfully.')
            return redirect('blog_detail', slug=reply.comment.article.slug)
        else:
            messages.error(request, 'You do not have permission to edit this reply.')
    
    return render(request, "edit_reply.html", {'reply': reply})

@login_required(login_url='login_view')  # Redirects to 'login_view' if not authenticated
def delete_comment(request, comment_id):
    """
    Deletes a comment if the requesting user is the owner of the comment.
    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.
        comment_id (int): The ID of the comment to be deleted.
    Returns:
        HttpResponseRedirect: Redirects to the article detail page.
    Raises:
        Http404: If the comment with the given ID does not exist.
    Side Effects:
        - Deletes the comment from the database if the user is authorized.
        - Adds a success message if the comment is deleted.
        - Adds an error message if the user is not authorized to delete the comment.
    """
    
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user == comment.user:
        comment.delete()
        messages.success(request, 'Comment deleted successfully.')
    else:
        messages.error(request, 'You do not have permission to delete this comment.')
    return redirect('blog_detail', slug=comment.article.slug)

@login_required(login_url='login_view')  # Redirects to 'login_view' if not authenticated
def edit_comment(request, comment_id):
    """
    Edit a specific comment.

    This view handles the editing of a comment identified by its ID. It ensures that only the user who 
    created the comment can edit it. If the request method is POST and the user is the owner of the 
    comment, the comment's content is updated and saved. Appropriate success or error messages are 
    displayed based on the outcome.

    Args:
        request (HttpRequest): The HTTP request object.
        comment_id (int): The ID of the comment to be edited.

    Returns:
        HttpResponse: Renders the edit comment page with the comment object if the request method is 
        not POST or the user is not the owner. Redirects to the article detail page if the comment is 
        successfully updated.
    """
    comment = get_object_or_404(Comment, id=comment_id)
    if request.method == 'POST':
        if request.user == comment.user:
            comment.content = request.POST.get('content')
            comment.save()
            messages.success(request, 'Comment updated successfully.')
            return redirect('blog_detail', slug=comment.article.slug)
        else:
            messages.error(request, 'You do not have permission to edit this comment.')

    return render(request, "edit_comment.html", {'comment': comment})


@login_required(login_url='login_view')  # Redirects to 'login_view' if not authenticated
def edit_profile(request):
    """
    Edit user profile.
    This view handles the editing of a user's profile. If the request method is POST,
    it updates the user's email, first name, and last name with the data provided in
    the request. Upon successful update, it displays a success message and redirects
    the user to the profile page. If the request method is not POST, it renders the
    edit profile page.
    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.
    Returns:
        HttpResponse: A redirect to the profile page if the profile is updated successfully,
                      otherwise renders the edit profile page.
    """
    if request.method == 'POST':
        user = request.user
        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.save()
        
        # Update Profile Image
        profile = getattr(user, 'profile', None)
        if not profile:
            profile = Profile.objects.create(user=user)
            
        if request.FILES.get('image'):
            profile.image = request.FILES.get('image')
            profile.save()
            
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')
    
    return render(request, "edit_profile.html")

@login_required(login_url='login_view')  # Redirects to 'login_view' if not authenticated
def change_password(request):
    """
    Change user password with verification.

    This view handles the password change process for a logged-in user. It verifies the current password,
    checks if the new password and confirmation password match, and then updates the user's password.

    Args:
        request (HttpRequest): The HTTP request object containing POST data with 'current_password',
                               'new_password', and 'confirm_password'.

    Returns:
        HttpResponse: Redirects to 'change_password' with an error message if the current password is incorrect
                      or if the new passwords do not match. Redirects to 'profile' with a success message if the
                      password is changed successfully. Renders the 'change_password.html' template for GET requests.
    """
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('change_password')

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('change_password')

        request.user.set_password(new_password)
        request.user.save()
        messages.success(request, 'Password changed successfully.')
        return redirect('profile')

    return render(request, "change_password.html")

def send_otp(user):
    """
    Generate and send a One-Time Password (OTP) to the user's email.

    This function generates a 6-digit OTP, assigns it to the user's profile,
    records the current timestamp, saves the profile, and sends an email
    containing the OTP to the user's registered email address.

    Args:
        user (User): The user object to whom the OTP will be sent. The user
                     object is expected to have a related profile with 'otp'
                     and 'otp_timestamp' fields, and an 'email' attribute.

    Raises:
        smtplib.SMTPException: If there is an error sending the email.
    """
    otp = str(secrets.randbelow(900000) + 100000)
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.otp = otp
    profile.otp_timestamp = timezone.now()
    profile.save()

    send_mail(
        'Your OTP Code',
        f'Your OTP code is: {otp}',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

def forget_password(request):
    """
    Handle forgotten password by sending a reset link or OTP.
    This view handles POST requests to initiate the password reset process. 
    It performs the following steps:
    1. Retrieves the email from the POST request.
    2. Fetches the user associated with the provided email.
    3. Implements rate limiting to prevent abuse of OTP requests.
    4. Generates and sends an OTP to the user's email.
    5. Increments the OTP request count and sets a timeout for rate limiting.
    6. Displays success or error messages based on the process outcome.
    7. Redirects the user to the appropriate page.
    Args:
        request (HttpRequest): The HTTP request object containing method and POST data.
    Returns:
        HttpResponse: Renders the forget_password.html template for GET requests.
        HttpResponseRedirect: Redirects to the 'verify_otp' page for successful OTP generation.
        HttpResponseRedirect: Redirects to the 'forget_password' page if rate limit is exceeded.
    """
    
    if request.method == 'POST':
        email = request.POST.get('email')
        user = get_object_or_404(User, email=email)

        # Rate limiting for OTP requests
        otp_request_count = cache.get(f'otp_request_count_{email}', 0)
        if otp_request_count >= 5:
            messages.error(request, 'Too many requests. Please try again later.')
            return redirect('forgot_password')

        # Generate and send OTP
        try:
            send_otp(user)
        except Exception:
            logger.error('Error sending reset OTP', exc_info=True)
            messages.error(request, 'Could not send the verification email. Please try again later.')
            return redirect('forgot_password')

        # Increment the request count
        cache.set(f'otp_request_count_{email}', otp_request_count + 1, timeout=3600)  # Reset after 1 hour
        
        messages.success(request, 'An OTP has been sent to your email.')
        return redirect('verify_otp', email=email)

    return render(request, "forget_password.html")

def verify_otp(request, email):
    """
    Verify the OTP sent to user's email.
    
    This view handles the verification of OTP for email verification or password reset.
    It includes rate limiting for OTP attempts and proper security checks.
    
    Args:
        request (HttpRequest): The request object
        email (str): The email address to verify
        
    Returns:
        HttpResponse: Renders verify_otp.html or redirects based on verification result
    """
    try:
        user = get_object_or_404(User, email=email)
        profile, _ = Profile.objects.get_or_create(user=user)
        
        # Check if there is a pending OTP verification
        if not profile.otp or not profile.otp_timestamp:
            messages.error(request, 'No OTP verification pending. Please request a new OTP.')
            return redirect('forgot_password')
            
        if request.method == 'POST':
            otp = request.POST.get('otp')
            
            # Rate limiting for OTP attempts
            attempt_count = cache.get(f'otp_attempt_count_{email}', 0)
            if attempt_count >= 5:
                messages.error(request, 'Too many invalid attempts. Please request a new OTP.')
                return redirect('forgot_password')
                
            if not otp:
                messages.error(request, 'Please enter the OTP.')
                return render(request, "verify_otp.html", {'email': email})
                
            if profile.otp == otp:
                if not profile.is_otp_expired():
                    # Clear the OTP and rate limiting after successful verification
                    profile.otp = None
                    profile.otp_timestamp = None
                    profile.save()
                    
                    cache.delete(f'otp_attempt_count_{email}')
                    cache.delete(f'otp_request_count_{email}')
                    
                    messages.success(request, 'OTP verified successfully. You can reset your password now.')
                    return redirect('reset_password', email=email)
                else:
                    messages.error(request, 'OTP has expired. Please request a new OTP.')
                    return redirect('forgot_password')
            else:
                # Increment failed attempt counter
                cache.set(f'otp_attempt_count_{email}', attempt_count + 1, timeout=300)  # Reset after 5 minutes
                messages.error(request, 'Invalid OTP. Please try again.')
        
        remaining_attempts = 5 - cache.get(f'otp_attempt_count_{email}', 0)
        return render(request, "verify_otp.html", {
            'email': email,
            'remaining_attempts': remaining_attempts,
            'expiry_time': profile.otp_timestamp + timezone.timedelta(minutes=10)
        })
        
    except User.DoesNotExist:
        messages.error(request, 'Invalid email address.')
        return redirect('forgot_password')
    except Exception as e:
        logger.error(f'Error in verify_otp view: {e}')
        messages.error(request, 'An error occurred. Please try again later.')
        return redirect('forgot_password')

def reset_password(request, email):
    """Reset the user's password."""
    if request.method == 'POST':
        new_password = (request.POST.get('new_password') or '').strip()
        confirm_password = (request.POST.get('confirm_password') or '').strip()

        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return redirect('reset_password', email=email)

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('reset_password', email=email)

        user = get_object_or_404(User, email=email)
        user.set_password(new_password)
        user.save()

        messages.success(request, 'Your password has been reset successfully.')
        return redirect('login_view')

    return render(request, "reset_password.html", {'email': email})

# Additional pages

def privacy_policy(request):
    """
    View to display the privacy policy page.
    
    Args:
        request (HttpRequest): The HTTP request object.
        
    Returns:
        HttpResponse: Renders the privacy policy template.
    """
    return render(request, 'privacy_policy.html')

def terms_and_conditions(request):
    """
    View to display the terms and conditions page.
    
    Args:
        request (HttpRequest): The HTTP request object.
        
    Returns:
        HttpResponse: Renders the terms and conditions template.
    """
    return render(request, 'terms_and_conditions.html')

def cookie_policy(request):
    """
    View to display the cookie policy page.
    
    Args:
        request (HttpRequest): The HTTP request object.
        
    Returns:
        HttpResponse: Renders the cookie policy template.
    """
    return render(request, 'cookie_policy.html')

def sitemap(request):
    """
    View to display the sitemap page.
    
    Args:
        request (HttpRequest): The HTTP request object.
        
    Returns:
        HttpResponse: Renders the sitemap template.
    """
    return render(request, 'sitemap.html')

def sitemap_xml(request):
    """Serve an XML sitemap of the site's key public pages."""
    from django.http import HttpResponse
    from xml.sax.saxutils import escape as xml_escape

    base = request.build_absolute_uri('/')
    today = timezone.now().strftime('%Y-%m-%d')

    entries = [
        ('', 'daily', '1.0'),
        ('about/', 'monthly', '0.8'),
        ('services/', 'monthly', '0.8'),
        ('portfolio/', 'monthly', '0.8'),
        ('case-study/', 'weekly', '0.9'),
        ('blog/', 'daily', '0.9'),
        ('community/', 'weekly', '0.8'),
        ('products/', 'weekly', '0.7'),
        ('shop/', 'weekly', '0.7'),
        ('shop/categories/', 'weekly', '0.6'),
        ('contact/', 'monthly', '0.6'),
        ('careers/', 'monthly', '0.6'),
        ('gallery/', 'monthly', '0.5'),
        ('help/', 'monthly', '0.5'),
        ('help/faq/', 'monthly', '0.5'),
        ('privacy-policy/', 'yearly', '0.3'),
        ('terms-and-conditions/', 'yearly', '0.3'),
        ('cookie-policy/', 'yearly', '0.3'),
        ('sitemap/', 'monthly', '0.4'),
    ]

    try:
        articles = Article.objects.filter(status='published', deleted=False).order_by('-created_at')[:50]
        for a in articles:
            if a.slug:
                entries.append((f'blog-detail/{a.slug}', 'weekly', '0.7'))
    except Exception:
        pass

    try:
        from app.models import CaseStudy
        for cs in CaseStudy.objects.filter(status=CaseStudy.STATUS_PUBLISHED).order_by('-published_at')[:30]:
            if cs.slug:
                entries.append((f'case-study/{cs.slug}', 'monthly', '0.8'))
    except Exception:
        pass

    try:
        from community.models import Topic
        for t in Topic.objects.exclude(slug__isnull=True).exclude(slug='')[:30]:
            entries.append((f'community/topic/{t.slug}/', 'weekly', '0.6'))
    except Exception:
        pass

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, freq, prio in entries:
        url = loc if loc.startswith('http') else base + loc
        lines.append(
            f'  <url><loc>{xml_escape(url)}</loc>'
            f'<lastmod>{today}</lastmod>'
            f'<changefreq>{freq}</changefreq>'
            f'<priority>{prio}</priority></url>'
        )
    lines.append('</urlset>')
    return HttpResponse('\n'.join(lines), content_type='application/xml')

def robots(request):
    """
    View to serve the robots.txt file.
    
    Args:
        request (HttpRequest): The HTTP request object.
        
    Returns:
        HttpResponse: Renders the robots.txt template with proper content type.
    """
    return render(request, 'robots.txt', content_type='text/plain')

def ads(request):
    """
    View to serve the ads.txt file for AdSense.
    
    Args:
        request (HttpRequest): The HTTP request object.
        
    Returns:
        HttpResponse: Renders the ads.txt template with proper content type.
    """
    return render(request, 'ads.txt', content_type='text/plain')

def advertise_with_us(request):
    """
    View to display the advertising information page.
    
    Args:
        request (HttpRequest): The HTTP request object.
        
    Returns:
        HttpResponse: Renders the advertise with us template.
    """
    return render(request, 'advertise_with_us.html')

def feedback(request):
    """
    Handle user feedback submission.
    
    Args:
        request (HttpRequest): The HTTP request object containing the feedback form data.
        
    Returns:
        HttpResponse: Renders the feedback form template or processes the submitted feedback.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        # Send feedback email to administrators
        send_mail(
            f'Feedback from {name}',
            f'Message: {message}\n\nFrom: {email}',
            settings.DEFAULT_FROM_EMAIL,
            [settings.FEEDBACK_EMAIL],
            fail_silently=False,
        )
        
        messages.success(request, 'Thank you for your feedback!')
        return redirect('home')
        
    return render(request, 'feedback.html')

def report(request):
    """
    Handle content reporting.
    
    Args:
        request (HttpRequest): The HTTP request object containing the report form data.
        
    Returns:
        HttpResponse: Renders the report form template or processes the submitted report.
    """
    if request.method == 'POST':
        content_url = request.POST.get('content_url')
        reason = request.POST.get('reason')
        details = request.POST.get('details')
        reporter_email = request.POST.get('email')
        
        # Send report email to administrators
        send_mail(
            'Content Report',
            f'Content URL: {content_url}\nReason: {reason}\nDetails: {details}\nReporter: {reporter_email}',
            settings.DEFAULT_FROM_EMAIL,
            [settings.REPORT_EMAIL],
            fail_silently=False,
        )
        
        messages.success(request, 'Thank you for reporting this content. We will review it shortly.')
        return redirect('home')
        
    return render(request, 'report.html')

def subscribe(request):
    """
    Handle newsletter subscription.
    
    Args:
        request (HttpRequest): The HTTP request object containing the subscription form data.
        
    Returns:
        HttpResponse: Processes the subscription request and returns appropriate response.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # Link to user if logged in
            user = request.user if request.user.is_authenticated else None
            subscription, created = NewsletterSubscription.objects.get_or_create(
                email=email,
                defaults={'user': user, 'is_verified': False}
            )
            
            if not created and subscription.is_verified:
                messages.info(request, 'This email is already subscribed to our newsletter.')
                return redirect('home')

            # Create verification link
            verification_link = request.build_absolute_uri(
                reverse('verify_subscription', kwargs={'token': str(subscription.token)})
            )
            
            # Send verification email (HTML version)
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            from django.core.mail import EmailMultiAlternatives

            subject = 'Verify your Dovetec Insights subscription'
            html_content = render_to_string('emails/verification_email.html', {
                'verification_link': verification_link
            })
            text_content = strip_tags(html_content)

            email_msg = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [email]
            )
            email_msg.attach_alternative(html_content, "text/html")
            email_msg.send(fail_silently=False)
            
            messages.info(request, "Please check your email to verify your subscription!")
            return redirect('home')
        else:
            messages.error(request, 'Please provide a valid email address.')
            
        return redirect(request.META.get('HTTP_REFERER', '/'))
        
    return render(request, 'subscribe.html')


def verify_subscription(request, token):
    """
    Verify a newsletter subscription using a token.
    """
    subscription = get_object_or_404(NewsletterSubscription, token=token)
    if not subscription.is_verified:
        subscription.is_verified = True
        subscription.verified_at = timezone.now()
        subscription.save()
        messages.success(request, 'Your subscription has been verified successfully!')
    else:
        messages.info(request, 'Your subscription is already verified.')
        
    return render(request, 'home/subscription_verified.html', {'subscription': subscription})

def unsubscribe(request, token):
    """
    Handle newsletter unsubscription.
    
    Args:
        request (HttpRequest): The HTTP request object.
        token (str): Unique token for subscription identification.
        
    Returns:
        HttpResponse: Processes the unsubscription request and returns appropriate response.
    """
    try:
        subscription = NewsletterSubscription.objects.get(token=token)
        subscription.delete()
        messages.success(request, 'You have been successfully unsubscribed from our newsletter.')
    except NewsletterSubscription.DoesNotExist:
        messages.error(request, 'Invalid unsubscribe link.')
        
    return redirect('home')

def newsletter(request):
    """
    Landing page for the newsletter system, previewing the sections a digest
    can carry (articles, resources, services, products, case studies, adverts)
    together with live delivery statistics.
    """
    from app.models import CaseStudy
    from shop.models import Category as ShopCategory
    from .models import Advertisement, NewsletterLog

    published_articles = Article.objects.filter(status='published')
    context = {
        'articles': published_articles.exclude(is_resource=True).order_by('-created_at')[:3],
        'resources': published_articles.filter(is_resource=True).order_by('-created_at')[:3],
        'products': Product.objects.all().order_by('-created_at')[:3],
        'services': ShopCategory.objects.all()[:6],
        'case_studies': CaseStudy.objects.filter(status=CaseStudy.STATUS_PUBLISHED).order_by('-featured', '-published_at')[:3],
        'communities': Topic.objects.all().order_by('-created_at')[:3],
        'adverts': Advertisement.objects.all()[:3],
        'subscriber_count': NewsletterSubscription.objects.filter(
            unsubscribed_at__isnull=True, is_verified=True,
        ).count(),
        'kpis': NewsletterLog.objects.aggregate(
            delivered=Count('id', filter=Q(status__in=['sent', 'opened', 'clicked', 'read'])),
            opened=Count('id', filter=Q(opened=True)),
            clicked=Count('id', filter=Q(clicked=True)),
            read=Count('id', filter=Q(read=True)),
        ),
    }
    delivered = context['kpis']['delivered'] or 0
    context['kpis']['open_rate'] = round(context['kpis']['opened'] / delivered * 100, 1) if delivered else 0.0
    context['kpis']['click_rate'] = round(context['kpis']['clicked'] / delivered * 100, 1) if delivered else 0.0
    context['kpis']['read_rate'] = round(context['kpis']['read'] / delivered * 100, 1) if delivered else 0.0
    return render(request, 'newsletter.html', context)

def unsubscribe(request, token):

    """
    Handle newsletter unsubscription via unique token.
    """
    try:
        token = uuid.UUID(str(token))
    except (ValueError, AttributeError, TypeError):
        raise Http404("Invalid unsubscribe token.")

    subscription = get_object_or_404(NewsletterSubscription, token=token)
    if subscription.unsubscribed_at is None:
        subscription.unsubscribed_at = timezone.now()
        subscription.save(update_fields=['unsubscribed_at'])
        NewsletterLog.objects.filter(
            email__iexact=subscription.email, unsubscribed=False
        ).update(unsubscribed=True)

    messages.success(request, "You have been successfully unsubscribed from our newsletter.")
    return render(request, "unsubscribe_success.html", {"email": subscription.email})


def help_center(request):
    return render(request, "help_center.html")

def faq(request):
    return render(request, "faq.html")

def current_year(request):
    """
    Display the current year in the footer.

    Usage:
    <!-- Copyright - Component -->
    <div class="py-3 py-md-4 py-xl-5 border-top">
        <div class="container">
        <div class="row">
            <div class="col-12">
            <div class="copyright-wrapper mb-1 fs-7 text-md-center">
                &copy; {{current_year}}. All Rights Reserved.
            </div>
            <div class="credit-wrapper text-secondary fs-8 text-md-center">
                
            </div>
            </div>
        </div>
        </div>
    </div>
    """

    current_year = datetime.now().year
    return render(request, 'footer.html', {'current_year': current_year})


def _tracking_gif():
    """1x1 transparent GIF used as the newsletter open-tracking pixel."""
    from django.http import HttpResponse
    response = HttpResponse(
        base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'),
        content_type='image/gif',
    )
    response['Cache-Control'] = 'no-cache, no-store, no-private, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = 'Wed, 11 Jan 1984 05:00:00 GMT'
    return response


def _safe_redirect_target(url, fallback='/'):
    """Only allow redirects to our own site, to avoid an open redirect."""
    from urllib.parse import urlparse

    if not url:
        return fallback
    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme not in ('http', 'https'):
        return fallback
    site_url = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
    host = parsed.netloc
    if not parsed.netloc:
        return url
    if site_url:
        site_host = urlparse(site_url).netloc
        if host == site_host:
            return url
    if host == request.get_host():
        return url
    return fallback


def track_open(request, tracking_id):
    """Record a newsletter open fired by the tracking pixel."""
    from home.models import NewsletterLog

    log = NewsletterLog.objects.filter(tracking_id=tracking_id).first()
    if log is not None:
        log.mark_opened(
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
    return _tracking_gif()


def track_click(request, tracking_id):
    """Record a newsletter link click, then forward the reader to the target."""
    from home.models import NewsletterLog

    log = NewsletterLog.objects.filter(tracking_id=tracking_id).first()
    target = request.GET.get('url', '')
    if log is not None:
        log.mark_clicked(target)
    return redirect(_safe_redirect_target(target, fallback='/?utm_source=newsletter'))


def track_log_in(request, tracking_id):
    """Record that a recipient reached the site and send them to sign in."""
    from home.models import NewsletterLog

    log = NewsletterLog.objects.filter(tracking_id=tracking_id).first()
    if log is not None:
        log.mark_read()
    return redirect(f'/login/?next={request.GET.get("next", "/")}')
