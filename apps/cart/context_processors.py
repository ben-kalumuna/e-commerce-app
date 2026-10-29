from .utils import get_cart


def cart_summary(request):
    cart = get_cart(request, create=False)
    if not cart:
        return {'cart_item_count': 0}
    return {'cart_item_count': cart.total_quantity}
