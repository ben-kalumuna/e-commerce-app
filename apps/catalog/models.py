from decimal import Decimal

from django.db import models
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

DEFAULT_LOW_STOCK_THRESHOLD = 10


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='children',
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('catalog:category', kwargs={'slug': self.slug})


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Original/list price shown as strikethrough when higher than price.',
    )
    image = models.ImageField(upload_to='products/', blank=True)
    stock = models.PositiveIntegerField(default=100)
    low_stock_threshold = models.PositiveIntegerField(
        default=DEFAULT_LOW_STOCK_THRESHOLD,
        help_text='Alert admin when stock falls to this level or below.',
    )
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)
        sync_stock_alert(self)

    def get_absolute_url(self):
        return reverse('catalog:product_detail', kwargs={'slug': self.slug})

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def is_out_of_stock(self):
        return self.stock == 0

    @property
    def is_low_stock(self):
        """True when stock is at/below threshold (includes out of stock)."""
        return self.stock <= self.low_stock_threshold

    @property
    def stock_status(self):
        if self.stock == 0:
            return 'out'
        if self.is_low_stock:
            return 'low'
        return 'ok'

    @property
    def on_sale(self):
        return bool(self.compare_at_price and self.compare_at_price > self.price)

    @property
    def discount_amount(self):
        if self.on_sale:
            return self.compare_at_price - self.price
        return Decimal('0.00')


class StockAlert(models.Model):
    """Open alert while a product remains at or below its low-stock threshold."""

    class Severity(models.TextChoices):
        LOW = 'low', 'Low stock'
        OUT = 'out', 'Out of stock'

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_alerts',
    )
    severity = models.CharField(max_length=10, choices=Severity.choices)
    stock_at_alert = models.PositiveIntegerField()
    threshold_at_alert = models.PositiveIntegerField()
    is_resolved = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_resolved', '-created_at']),
        ]

    def __str__(self):
        state = 'resolved' if self.is_resolved else 'open'
        return f'{self.product.name} [{self.severity}] ({state})'

    def resolve(self, note=''):
        self.is_resolved = True
        self.resolved_at = timezone.now()
        if note:
            self.note = note
        self.save(update_fields=['is_resolved', 'resolved_at', 'note'])


def sync_stock_alert(product):
    """
    Create/update an open StockAlert when stock is low/out.
    Resolve open alerts when stock rises above the threshold.
    """
    open_alert = (
        StockAlert.objects.filter(product=product, is_resolved=False)
        .order_by('-created_at')
        .first()
    )

    if product.stock > product.low_stock_threshold:
        if open_alert:
            open_alert.resolve(note='Stock replenished above threshold.')
        return None

    severity = (
        StockAlert.Severity.OUT if product.stock == 0 else StockAlert.Severity.LOW
    )

    if open_alert:
        # Refresh severity / stock snapshot if it changed (e.g. low → out)
        if (
            open_alert.severity != severity
            or open_alert.stock_at_alert != product.stock
        ):
            open_alert.severity = severity
            open_alert.stock_at_alert = product.stock
            open_alert.threshold_at_alert = product.low_stock_threshold
            open_alert.save(
                update_fields=['severity', 'stock_at_alert', 'threshold_at_alert']
            )
        return open_alert

    return StockAlert.objects.create(
        product=product,
        severity=severity,
        stock_at_alert=product.stock,
        threshold_at_alert=product.low_stock_threshold,
    )


def low_stock_products():
    """Products currently at or below their own threshold."""
    return Product.objects.filter(stock__lte=F('low_stock_threshold')).select_related(
        'category'
    ).order_by('stock', 'name')


def open_stock_alerts():
    return StockAlert.objects.filter(is_resolved=False).select_related(
        'product', 'product__category'
    )
