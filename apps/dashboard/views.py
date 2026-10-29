import json
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from apps.catalog.models import Category, Product, StockAlert, low_stock_products, open_stock_alerts
from apps.orders.models import Order, OrderItem, clear_user_cart
from apps.pages.models import ContactMessage, NewsletterSubscriber

from .decorators import staff_required
from .forms import (
    DashboardCategoryForm,
    DashboardOrderStatusForm,
    DashboardProductForm,
)


def _nav(active):
    return {'nav_active': active}


@staff_required
def overview(request):
    now = timezone.now()
    since = now - timedelta(days=30)

    orders_qs = Order.objects.exclude(status=Order.Status.CANCELLED)
    recent_orders = orders_qs.filter(created_at__gte=since)
    revenue = recent_orders.aggregate(total=Sum('total'))['total'] or Decimal('0')
    order_count = recent_orders.count()
    customer_count = User.objects.filter(is_staff=False).count()
    pending_count = Order.objects.filter(status=Order.Status.PENDING).count()

    # Sales chart — last 7 days
    chart_start = (now - timedelta(days=6)).date()
    daily = (
        orders_qs.filter(created_at__date__gte=chart_start)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(income=Sum('total'), count=Count('id'))
        .order_by('day')
    )
    by_day = {row['day']: row for row in daily}
    chart_labels = []
    chart_values = []
    for i in range(7):
        d = chart_start + timedelta(days=i)
        chart_labels.append(d.strftime('%b %d'))
        chart_values.append(float(by_day.get(d, {}).get('income') or 0))

    income = revenue
    # Simple stand-in metrics for the analytic cards
    expenses = (income * Decimal('0.35')).quantize(Decimal('0.01')) if income else Decimal('0')
    balance = income - expenses

    top_selling = (
        OrderItem.objects.filter(order__in=recent_orders)
        .values('product_id', 'product_name')
        .annotate(sold=Sum('quantity'))
        .order_by('-sold')[:6]
    )
    product_ids = [t['product_id'] for t in top_selling if t['product_id']]
    products_map = {p.id: p for p in Product.objects.filter(id__in=product_ids)}
    top_products = []
    for row in top_selling:
        p = products_map.get(row['product_id'])
        top_products.append({
            'name': row['product_name'],
            'sold': row['sold'],
            'product': p,
            'stock': p.stock if p else 0,
        })

    low_stock = low_stock_products()[:8]
    low_stock_count = low_stock_products().count()
    on_sale = Product.objects.filter(is_active=True, compare_at_price__isnull=False).count()
    out_of_stock = Product.objects.filter(stock=0).count()
    open_alerts = open_stock_alerts()

    ctx = {
        **_nav('dashboard'),
        'page_title': 'Overview',
        'kpi': {
            'revenue': revenue,
            'orders': order_count,
            'customers': customer_count,
            'pending': pending_count,
        },
        'analytic': {
            'income': income,
            'expenses': expenses,
            'balance': balance,
        },
        'chart_labels': mark_safe(json.dumps(chart_labels)),
        'chart_values': mark_safe(json.dumps(chart_values)),
        'top_products': top_products,
        'low_stock': low_stock,
        'low_stock_count': low_stock_count,
        'on_sale_count': on_sale,
        'out_of_stock': out_of_stock,
        'open_alerts': open_alerts[:8],
        'open_alert_count': open_alerts.count(),
        'recent_orders': Order.objects.select_related('user').order_by('-created_at')[:6],
    }
    return render(request, 'dashboard/overview.html', ctx)


# ── Products ──────────────────────────────────────────────

@staff_required
def product_list(request):
    q = request.GET.get('q', '').strip()
    products = Product.objects.select_related('category').all()
    if q:
        products = products.filter(Q(name__icontains=q) | Q(category__name__icontains=q))
    return render(request, 'dashboard/products/list.html', {
        **_nav('products'),
        'page_title': 'Products',
        'products': products,
        'q': q,
    })


@staff_required
def product_create(request):
    form = DashboardProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Product created.')
        return redirect('dashboard:product_list')
    return render(request, 'dashboard/products/form.html', {
        **_nav('products'),
        'page_title': 'Add Product',
        'form': form,
        'mode': 'create',
    })


@staff_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = DashboardProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Product updated.')
        return redirect('dashboard:product_list')
    return render(request, 'dashboard/products/form.html', {
        **_nav('products'),
        'page_title': f'Edit — {product.name}',
        'form': form,
        'product': product,
        'mode': 'edit',
    })


@staff_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    product.delete()
    messages.success(request, f'Deleted “{name}”.')
    return redirect('dashboard:product_list')


# ── Categories / Offers ───────────────────────────────────

@staff_required
def category_list(request):
    categories = Category.objects.select_related('parent').annotate(
        product_count=Count('products')
    )
    return render(request, 'dashboard/categories/list.html', {
        **_nav('offers'),
        'page_title': 'Categories',
        'categories': categories,
    })


@staff_required
def category_create(request):
    form = DashboardCategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Category created.')
        return redirect('dashboard:category_list')
    return render(request, 'dashboard/categories/form.html', {
        **_nav('offers'),
        'page_title': 'Add Category',
        'form': form,
    })


@staff_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = DashboardCategoryForm(request.POST or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Category updated.')
        return redirect('dashboard:category_list')
    return render(request, 'dashboard/categories/form.html', {
        **_nav('offers'),
        'page_title': f'Edit — {category.name}',
        'form': form,
        'category': category,
    })


@staff_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if category.products.exists():
        messages.error(request, 'Cannot delete a category that still has products.')
        return redirect('dashboard:category_list')
    category.delete()
    messages.success(request, 'Category deleted.')
    return redirect('dashboard:category_list')


@staff_required
def offers_list(request):
    products = Product.objects.filter(
        Q(is_featured=True) | Q(compare_at_price__isnull=False)
    ).select_related('category')
    return render(request, 'dashboard/offers.html', {
        **_nav('offers'),
        'page_title': 'Offers & Featured',
        'products': products,
    })


# ── Inventory ─────────────────────────────────────────────

@staff_required
def inventory_list(request):
    q = request.GET.get('q', '').strip()
    filter_stock = request.GET.get('stock', '')
    products = Product.objects.select_related('category').order_by('stock', 'name')
    if q:
        products = products.filter(name__icontains=q)
    if filter_stock == 'low':
        products = low_stock_products().filter(stock__gt=0)
    elif filter_stock == 'out':
        products = products.filter(stock=0)
    elif filter_stock == 'alerts':
        alert_ids = open_stock_alerts().values_list('product_id', flat=True)
        products = products.filter(id__in=alert_ids)
    return render(request, 'dashboard/inventory.html', {
        **_nav('inventory'),
        'page_title': 'Inventory',
        'products': products,
        'q': q,
        'filter_stock': filter_stock,
    })


@staff_required
@require_POST
def inventory_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        stock = int(request.POST.get('stock', product.stock))
        if stock < 0:
            raise ValueError('Stock cannot be negative.')
    except (TypeError, ValueError):
        messages.error(request, 'Invalid stock value.')
        return redirect('dashboard:inventory')
    product.stock = stock
    product.is_active = request.POST.get('is_active') == 'on'
    product.save(update_fields=['stock', 'is_active', 'updated_at'])
    if product.is_low_stock:
        messages.warning(
            request,
            f'{product.name}: stock is {product.stock} (alert threshold {product.low_stock_threshold}).',
        )
    else:
        messages.success(request, f'Stock updated for {product.name}.')
    return redirect('dashboard:inventory')


@staff_required
def stock_alerts(request):
    show = request.GET.get('show', 'open')
    alerts = StockAlert.objects.select_related('product', 'product__category')
    if show == 'resolved':
        alerts = alerts.filter(is_resolved=True)
    else:
        alerts = alerts.filter(is_resolved=False)
        show = 'open'
    return render(request, 'dashboard/stock_alerts.html', {
        **_nav('alerts'),
        'page_title': 'Stock Alerts',
        'alerts': alerts,
        'show': show,
        'open_count': StockAlert.objects.filter(is_resolved=False).count(),
    })


@staff_required
@require_POST
def stock_alert_resolve(request, pk):
    alert = get_object_or_404(StockAlert, pk=pk)
    alert.resolve(note='Manually dismissed by admin.')
    messages.success(request, f'Alert for {alert.product.name} dismissed.')
    return redirect('dashboard:stock_alerts')


# ── Orders ────────────────────────────────────────────────

@staff_required
def order_list(request):
    status = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()
    orders = Order.objects.select_related('user').prefetch_related('items')
    if status:
        orders = orders.filter(status=status)
    if q:
        orders = orders.filter(
            Q(full_name__icontains=q)
            | Q(phone__icontains=q)
            | Q(user__username__icontains=q)
            | Q(pk__icontains=q)
        )
    return render(request, 'dashboard/orders/list.html', {
        **_nav('orders'),
        'page_title': 'Orders',
        'orders': orders,
        'status': status,
        'q': q,
        'status_choices': Order.Status.choices,
    })


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('items'),
        pk=pk,
    )
    previous_status = order.status
    form = DashboardOrderStatusForm(request.POST or None, instance=order)
    if request.method == 'POST' and form.is_valid():
        form.save()
        # If admin marks delivered, clear customer cart (same as customer confirm).
        if (
            previous_status != Order.Status.DELIVERED
            and order.status == Order.Status.DELIVERED
        ):
            clear_user_cart(order.user)
            messages.success(
                request,
                f'Order #{order.pk} marked delivered. Customer cart cleared.',
            )
        else:
            messages.success(request, f'Order #{order.pk} updated.')
        return redirect('dashboard:order_detail', pk=order.pk)
    return render(request, 'dashboard/orders/detail.html', {
        **_nav('orders'),
        'page_title': f'Order #{order.pk}',
        'order': order,
        'form': form,
    })


# ── Sales ─────────────────────────────────────────────────

@staff_required
def sales(request):
    delivered = Order.objects.filter(status=Order.Status.DELIVERED)
    confirmed = Order.objects.filter(
        status__in=[
            Order.Status.CONFIRMED,
            Order.Status.OUT_FOR_DELIVERY,
            Order.Status.DELIVERED,
        ]
    )
    total_sales = delivered.aggregate(t=Sum('total'))['t'] or Decimal('0')
    pipeline = confirmed.aggregate(t=Sum('total'))['t'] or Decimal('0')
    by_status = (
        Order.objects.values('status')
        .annotate(count=Count('id'), revenue=Sum('total'))
        .order_by('status')
    )
    return render(request, 'dashboard/sales.html', {
        **_nav('sales'),
        'page_title': 'Sales',
        'total_sales': total_sales,
        'pipeline': pipeline,
        'by_status': by_status,
        'recent': Order.objects.select_related('user').order_by('-created_at')[:20],
    })


# ── Customers ─────────────────────────────────────────────

@staff_required
def customer_list(request):
    q = request.GET.get('q', '').strip()
    customers = (
        User.objects.filter(is_staff=False)
        .annotate(order_count=Count('orders'))
        .order_by('-date_joined')
    )
    if q:
        customers = customers.filter(
            Q(username__icontains=q) | Q(email__icontains=q) | Q(profile__phone__icontains=q)
        )
    return render(request, 'dashboard/customers.html', {
        **_nav('customers'),
        'page_title': 'Customers',
        'customers': customers,
        'q': q,
    })


@staff_required
def customer_detail(request, pk):
    customer = get_object_or_404(User, pk=pk, is_staff=False)
    orders = customer.orders.all()[:20]
    return render(request, 'dashboard/customer_detail.html', {
        **_nav('customers'),
        'page_title': customer.username,
        'customer': customer,
        'orders': orders,
    })


# ── Newsletter / Messages ─────────────────────────────────

@staff_required
def newsletter_list(request):
    subs = NewsletterSubscriber.objects.all()
    return render(request, 'dashboard/newsletter.html', {
        **_nav('newsletter'),
        'page_title': 'Newsletter',
        'subscribers': subs,
    })


@staff_required
@require_POST
def newsletter_toggle(request, pk):
    sub = get_object_or_404(NewsletterSubscriber, pk=pk)
    sub.is_active = not sub.is_active
    sub.save(update_fields=['is_active'])
    messages.success(request, 'Subscriber updated.')
    return redirect('dashboard:newsletter')


@staff_required
def messages_list(request):
    msgs = ContactMessage.objects.all()
    return render(request, 'dashboard/messages.html', {
        **_nav('newsletter'),
        'page_title': 'Contact Messages',
        'messages_list': msgs,
    })


@staff_required
@require_POST
def message_mark_read(request, pk):
    msg = get_object_or_404(ContactMessage, pk=pk)
    msg.is_read = True
    msg.save(update_fields=['is_read'])
    return redirect('dashboard:messages')


# ── Settings ──────────────────────────────────────────────

@staff_required
def settings_view(request):
    stats = {
        'products': Product.objects.count(),
        'categories': Category.objects.count(),
        'orders': Order.objects.count(),
        'customers': User.objects.filter(is_staff=False).count(),
        'subscribers': NewsletterSubscriber.objects.filter(is_active=True).count(),
    }
    return render(request, 'dashboard/settings.html', {
        **_nav('settings'),
        'page_title': 'Settings',
        'stats': stats,
        'admin_user': request.user,
    })
