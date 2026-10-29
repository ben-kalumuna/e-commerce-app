from django.urls import path

from . import views

app_name = 'pages'

urlpatterns = [
    path('about/', views.AboutView.as_view(), name='about'),
    path('services/', views.ServicesView.as_view(), name='services'),
    path('events/', views.EventsView.as_view(), name='events'),
    path('faqs/', views.FaqsView.as_view(), name='faqs'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    path('contact/', views.contact, name='contact'),
    path('newsletter/', views.newsletter_subscribe, name='newsletter'),
]
