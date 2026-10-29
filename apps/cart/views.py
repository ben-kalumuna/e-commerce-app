from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.models import Product
from apps.orders.models import Order

from .utils import add_to_cart, get_cart, remove_from_cart, update_cart_item


def _active_order(request):
    if request.user.is_authenticated:
        return Order.open_orders_for(request.user).order_by('-created_at').first()
    return None


def cart_detail(request):
    cart = get_cart(request, create=True)
    items = cart.items.select_related('product', 'product__category')
    active_order = _active_order(request)
    return render(
        request,
        'cart/cart.html',
        {
            'cart': cart,
            'items': items,
            'subtotal': cart.subtotal,
            'active_order': active_order,
            'cart_locked': bool(active_order),
        },
    )


@require_POST
def cart_add(request, product_id):
    active = _active_order(request)
    if active:
        messages.warning(
            request,
            f'Your cart is held for order #{active.pk} until you confirm delivery. '
            f'Open My Orders to track or confirm receipt.',
        )
        return redirect('accounts:order_detail', pk=active.pk)

    product = get_object_or_404(Product, pk=product_id, is_active=True)
    try:
        qty = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        qty = 1
    try:
        add_to_cart(request, product, quantity=qty)
        messages.success(request, f'Added {product.name} to your cart.')
    except ValueError as exc:
        messages.error(request, str(exc))
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
    return redirect(next_url)


@require_POST
def cart_update(request, product_id):
    active = _active_order(request)
    if active:
        messages.warning(
            request,
            f'Cart is locked while order #{active.pk} awaits delivery confirmation.',
        )
        return redirect('cart:detail')
    try:
        qty = int(request.POST.get('quantity', 1))
        update_cart_item(request, product_id, qty)
        messages.success(request, 'Cart updated.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('cart:detail')


@require_POST
def cart_remove(request, product_id):
    active = _active_order(request)
    if active:
        messages.warning(
            request,
            f'Cart is locked while order #{active.pk} awaits delivery confirmation.',
        )
        return redirect('cart:detail')
    remove_from_cart(request, product_id)
    messages.success(request, 'Item removed from cart.')
    return redirect('cart:detail')
