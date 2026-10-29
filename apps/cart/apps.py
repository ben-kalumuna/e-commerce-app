from django.apps import AppConfig


class CartConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cart'
    label = 'cart'

    def ready(self):
        from . import utils  # noqa: F401  # registers user_logged_in cart merge
