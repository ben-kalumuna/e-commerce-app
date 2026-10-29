from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    phone = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return f'Profile({self.user.username})'


class Address(models.Model):
    class AddressType(models.TextChoices):
        HOME = 'home', 'Home'
        OFFICE = 'office', 'Office'
        COMMERCIAL = 'commercial', 'Commercial'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses',
    )
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32)
    landmark = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120)
    address_line = models.CharField(max_length=255, blank=True)
    address_type = models.CharField(
        max_length=20,
        choices=AddressType.choices,
        default=AddressType.HOME,
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'addresses'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f'{self.full_name} — {self.city}'

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)
