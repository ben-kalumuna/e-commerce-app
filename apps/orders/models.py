from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.catalog.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        OUT_FOR_DELIVERY = 'out_for_delivery', 'Out for delivery'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentMethod(models.TextChoices):
        COD = 'cod', 'Cash on Delivery'

    OPEN_STATUSES = (
        Status.PENDING,
        Status.CONFIRMED,
        Status.OUT_FOR_DELIVERY,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.COD,
    )
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32)
    landmark = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120)
    address_line = models.CharField(max_length=255, blank=True)
    address_type = models.CharField(max_length=20, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True)
    customer_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the customer confirmed they received the COD order.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.pk} — {self.user} ({self.status})'

    @property
    def can_cancel(self):
        return self.status == self.Status.PENDING

    @property
    def is_open(self):
        """Order not yet delivered or cancelled — cart should keep items."""
        return self.status in self.OPEN_STATUSES

    @property
    def can_confirm_delivery(self):
        """Customer may confirm receipt after the store has accepted/shipped the order."""
        return self.status in (
            self.Status.CONFIRMED,
            self.Status.OUT_FOR_DELIVERY,
        ) and self.customer_confirmed_at is None

    @classmethod
    def open_orders_for(cls, user):
        return cls.objects.filter(user=user, status__in=cls.OPEN_STATUSES)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='order_items',
    )
    product_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.quantity} x {self.product_name}'


def clear_user_cart(user):
    """Remove all items from the authenticated user's cart."""
    from apps.cart.models import Cart

    cart = Cart.objects.filter(user=user).first()
    if cart:
        cart.items.all().delete()


@transaction.atomic
def create_order_from_cart(*, user, cart, address_data, service_charge=Decimal('0.00')):
    """
    Create an order from cart items and reserve stock.

    Cart items are kept until the customer confirms delivery (or the order
    is cancelled and they shop again). Duplicate checkouts are blocked while
    an open order exists.
    """
    if Order.open_orders_for(user).exists():
        raise ValueError(
            'You already have an order awaiting delivery. '
            'Confirm you received it (or cancel if still pending) before placing a new one.'
        )

    items = list(cart.items.select_related('product'))
    if not items:
        raise ValueError('Cart is empty.')

    for item in items:
        if not item.product.is_active:
            raise ValueError(f'{item.product.name} is no longer available.')
        if item.quantity > item.product.stock:
            raise ValueError(
                f'Not enough stock for {item.product.name} '
                f'(available: {item.product.stock}).'
            )

    subtotal = sum((i.line_total for i in items), Decimal('0.00'))
    order = Order.objects.create(
        user=user,
        full_name=address_data['full_name'],
        phone=address_data['phone'],
        landmark=address_data.get('landmark', ''),
        city=address_data['city'],
        address_line=address_data.get('address_line', ''),
        address_type=address_data.get('address_type', ''),
        subtotal=subtotal,
        service_charge=service_charge,
        total=subtotal + service_charge,
        payment_method=Order.PaymentMethod.COD,
        status=Order.Status.PENDING,
    )

    for item in items:
        product = item.product
        product.stock -= item.quantity
        product.save(update_fields=['stock', 'updated_at'])
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            unit_price=product.price,
            quantity=item.quantity,
            line_total=item.line_total,
        )

    # Intentionally do NOT clear the cart — items stay until delivery is confirmed.
    return order


@transaction.atomic
def confirm_delivery_by_customer(order):
    """Customer confirms COD receipt → Delivered on admin side + clear cart."""
    if not order.can_confirm_delivery:
        raise ValueError('This order cannot be marked as received yet.')

    order.status = Order.Status.DELIVERED
    order.customer_confirmed_at = timezone.now()
    note = 'Customer confirmed receipt (COD paid on delivery).'
    if order.notes:
        order.notes = f'{order.notes}\n{note}'
    else:
        order.notes = note
    order.save(update_fields=['status', 'customer_confirmed_at', 'notes', 'updated_at'])
    clear_user_cart(order.user)
    return order


@transaction.atomic
def mark_order_delivered(order, *, by_customer=False):
    """Mark delivered (admin or customer) and clear the customer's cart."""
    previous = order.status
    order.status = Order.Status.DELIVERED
    if by_customer and not order.customer_confirmed_at:
        order.customer_confirmed_at = timezone.now()
    order.save(update_fields=['status', 'customer_confirmed_at', 'updated_at'] if by_customer else ['status', 'updated_at'])
    if previous != Order.Status.DELIVERED:
        clear_user_cart(order.user)
    return order
