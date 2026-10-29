from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import Cart, CartItem


def _ensure_session(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_cart(request, create=True):
    """Return the cart for the current user or guest session."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    session_key = request.session.session_key
    if not session_key:
        if not create:
            return None
        session_key = _ensure_session(request)

    cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    if cart is None and create:
        cart = Cart.objects.create(session_key=session_key)
    return cart


def add_to_cart(request, product, quantity=1):
    if quantity < 1:
        raise ValueError('Quantity must be at least 1.')
    if not product.is_active:
        raise ValueError('This product is not available.')
    if product.stock < 1:
        raise ValueError('This product is out of stock.')

    cart = get_cart(request, create=True)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    new_qty = quantity if created else item.quantity + quantity
    if new_qty > product.stock:
        raise ValueError(f'Only {product.stock} in stock.')
    item.quantity = new_qty
    item.save()
    return item


def update_cart_item(request, product_id, quantity):
    cart = get_cart(request, create=False)
    if not cart:
        raise ValueError('Cart is empty.')
    try:
        item = cart.items.select_related('product').get(product_id=product_id)
    except CartItem.DoesNotExist as exc:
        raise ValueError('Item not in cart.') from exc

    if quantity <= 0:
        item.delete()
        return None
    if quantity > item.product.stock:
        raise ValueError(f'Only {item.product.stock} in stock.')
    item.quantity = quantity
    item.save()
    return item


def remove_from_cart(request, product_id):
    cart = get_cart(request, create=False)
    if not cart:
        return
    cart.items.filter(product_id=product_id).delete()


def merge_session_cart_into_user(request, user):
    session_key = request.session.session_key
    if not session_key:
        return
    guest_cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    if not guest_cart:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)
    for item in guest_cart.items.select_related('product'):
        existing = user_cart.items.filter(product=item.product).first()
        if existing:
            existing.quantity = min(existing.quantity + item.quantity, item.product.stock)
            existing.save()
        else:
            CartItem.objects.create(
                cart=user_cart,
                product=item.product,
                quantity=min(item.quantity, item.product.stock),
            )
    guest_cart.delete()


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    merge_session_cart_into_user(request, user)
