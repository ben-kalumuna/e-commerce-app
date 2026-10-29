from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, ListView, TemplateView

from .models import Category, Product


class HomeView(TemplateView):
    template_name = 'catalog/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        active = Product.objects.filter(is_active=True).select_related('category')
        ctx['featured_products'] = active.filter(is_featured=True)[:8]
        if ctx['featured_products'].count() < 4:
            ctx['featured_products'] = active[:8]
        ctx['top_products'] = active.order_by('-created_at')[:8]
        ctx['hot_offers'] = active.filter(compare_at_price__isnull=False)[:8]
        if not ctx['hot_offers']:
            ctx['hot_offers'] = active[:4]
        return ctx


class CategoryDetailView(ListView):
    template_name = 'catalog/category.html'
    context_object_name = 'products'
    paginate_by = 16

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'], is_active=True)
        qs = Product.objects.filter(is_active=True).select_related('category')
        # Include child categories
        child_ids = list(self.category.children.filter(is_active=True).values_list('id', flat=True))
        return qs.filter(Q(category=self.category) | Q(category_id__in=child_ids))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['category'] = self.category
        return ctx


class ProductDetailView(DetailView):
    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related('category')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['related_products'] = (
            Product.objects.filter(is_active=True, category=self.object.category)
            .exclude(pk=self.object.pk)[:8]
        )
        return ctx


class SearchView(ListView):
    template_name = 'catalog/search.html'
    context_object_name = 'products'
    paginate_by = 16

    def get_queryset(self):
        self.query = self.request.GET.get('q', '').strip()
        qs = Product.objects.filter(is_active=True).select_related('category')
        if self.query:
            qs = qs.filter(
                Q(name__icontains=self.query)
                | Q(description__icontains=self.query)
                | Q(category__name__icontains=self.query)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['query'] = getattr(self, 'query', '')
        return ctx


class BestDealsView(ListView):
    template_name = 'catalog/category.html'
    context_object_name = 'products'
    paginate_by = 16

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .filter(Q(is_featured=True) | Q(compare_at_price__isnull=False))
            .select_related('category')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['category'] = None
        ctx['page_title'] = 'Best Deals'
        return ctx
