from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from .forms import ContactForm, NewsletterForm


class AboutView(TemplateView):
    template_name = 'pages/about.html'


class ServicesView(TemplateView):
    template_name = 'pages/services.html'


class EventsView(TemplateView):
    template_name = 'pages/events.html'


class FaqsView(TemplateView):
    template_name = 'pages/faqs.html'


class PrivacyView(TemplateView):
    template_name = 'pages/privacy.html'


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Thanks! We received your message.')
            return redirect('pages:contact')
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'pages/contact.html', {'form': form})


def newsletter_subscribe(request):
    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            from .models import NewsletterSubscriber

            obj, created = NewsletterSubscriber.objects.get_or_create(email=email)
            if not created and not obj.is_active:
                obj.is_active = True
                obj.save(update_fields=['is_active'])
            messages.success(request, 'Subscribed to our newsletter.')
        else:
            messages.error(request, 'Enter a valid email address.')
    next_url = request.META.get('HTTP_REFERER') or '/'
    return redirect(next_url)
