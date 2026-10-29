from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('offers/', views.offers_list, name='offers'),
    path('inventory/', views.inventory_list, name='inventory'),
    path('inventory/<int:pk>/', views.inventory_update, name='inventory_update'),
    path('alerts/', views.stock_alerts, name='stock_alerts'),
    path('alerts/<int:pk>/resolve/', views.stock_alert_resolve, name='stock_alert_resolve'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('sales/', views.sales, name='sales'),
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('newsletter/', views.newsletter_list, name='newsletter'),
    path('newsletter/<int:pk>/toggle/', views.newsletter_toggle, name='newsletter_toggle'),
    path('messages/', views.messages_list, name='messages'),
    path('messages/<int:pk>/read/', views.message_mark_read, name='message_read'),
    path('settings/', views.settings_view, name='settings'),
]
