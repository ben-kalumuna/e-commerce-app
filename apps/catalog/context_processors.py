from apps.catalog.models import Category, open_stock_alerts


def categories(request):
    return {
        'nav_categories': Category.objects.filter(
            is_active=True, parent__isnull=True
        ).prefetch_related('children')
    }


def stock_alerts(request):
    """Expose open low-stock alert count to dashboard templates."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_staff:
        return {
            'stock_alert_count': 0,
            'stock_alert_preview': [],
        }
    qs = open_stock_alerts()
    return {
        'stock_alert_count': qs.count(),
        'stock_alert_preview': list(qs[:5]),
    }
