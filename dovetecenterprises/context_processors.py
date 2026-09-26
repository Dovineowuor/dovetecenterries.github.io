def site_metadata(request):
    """Context processor providing site-wide metadata defaults."""
    from app.models import CaseStudy
    latest_cases = CaseStudy.objects.filter(status=CaseStudy.STATUS_PUBLISHED).order_by('-featured', '-published_at')[:2]
    user = getattr(request, 'user', None)
    is_authenticated = False
    is_staff = False
    is_superuser = False
    user_groups = []
    unread_notifications = 0
    open_ticket_count = 0
    if user and hasattr(user, 'is_authenticated'):
        is_authenticated = user.is_authenticated
        is_staff = getattr(user, 'is_staff', False)
        is_superuser = getattr(user, 'is_superuser', False)
        try:
            user_groups = list(user.groups.values_list('name', flat=True))
        except Exception:
            pass
        if is_authenticated:
            try:
                from home.models import Notification
                unread_notifications = Notification.objects.filter(
                    recipient=user, read_at__isnull=True,
                ).count()
            except Exception:
                unread_notifications = 0
            if is_staff or is_superuser:
                try:
                    from app.models import Ticket
                    open_ticket_count = Ticket.objects.filter(
                        status__in=Ticket.OPEN_STATUSES,
                    ).count()
                except Exception:
                    open_ticket_count = 0
    return {
        'site_name': 'Dovetec Enterprises',
        'site_url': request.build_absolute_uri('/') if request else 'https://dovetecenterprises.site',
        'default_meta_title': 'Dovetec Enterprises - Software Engineering, IT Solutions & Consulting',
        'default_meta_description': 'Empowering your digital evolution - Leading the way in software engineering and IT solutions, we guide businesses of all sizes to thrive in the digital era, maximizing growth and innovation in Kenya and East Africa.',
        'default_og_image': '/static/images/logo-dovetek.png',
        'default_og_type': 'website',
        'site_author': 'Dovetec Enterprises',
        'geo_region': 'KE',
        'geo_placename': 'Nairobi',
        'geo_position': '-1.2921;36.8219',
        'latest_case_studies': latest_cases,
        'auth_user': user if is_authenticated else None,
        'is_authenticated': is_authenticated,
        'is_staff': is_staff,
        'is_superuser': is_superuser,
        'user_groups': user_groups,
        'unread_notifications': unread_notifications,
        'open_ticket_count': open_ticket_count,
    }