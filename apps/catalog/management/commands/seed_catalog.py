import json
import re
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.catalog.models import Category, Product


def extract_products_from_html(base_dir: Path):
    """Parse original template HTML for product cards."""
    products = []
    seen = set()
    thumb_re = re.compile(
        r'<div class="snipcart-thumb[^"]*">\s*(?:<a[^>]*>)?\s*'
        r'<img[^>]+src="(images/(?!offer\.png|tag\.png)[^"]+)"[^>]*>'
        r'.*?<p>([^<]+)</p>.*?<h4>\$([0-9.]+)\s*(?:<span>\$([0-9.]+)</span>)?',
        re.S | re.I,
    )
    for html in sorted(base_dir.glob('*.html')):
        text = html.read_text(errors='ignore')
        for m in thumb_re.finditer(text):
            img, label, price, compare = m.groups()
            name = re.sub(r'\s*\([^)]*\)\s*$', '', label).strip()
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            products.append({
                'name': name,
                'label': label.strip(),
                'image': img,
                'price': price,
                'compare_at_price': compare,
                'source': html.name,
            })
    return products

SOURCE_CATEGORY_MAP = {
    'index.html': 'branded-foods',
    'products.html': 'branded-foods',
    'vegetables.html': 'vegetables-fruits',
    'drinks.html': 'beverages',
    'household.html': 'households',
    'kitchen.html': 'kitchen',
    'pet.html': 'pet-food',
    'frozen.html': 'frozen-foods',
    'bread.html': 'bread-bakery',
    'single.html': 'branded-foods',
}

CATEGORIES = [
    {'name': 'Branded Foods', 'slug': 'branded-foods', 'sort_order': 1},
    {'name': 'Households', 'slug': 'households', 'sort_order': 2},
    {
        'name': 'Veggies & Fruits',
        'slug': 'veggies-fruits',
        'sort_order': 3,
        'children': [
            {'name': 'Vegetables & Fruits', 'slug': 'vegetables-fruits'},
        ],
    },
    {'name': 'Kitchen', 'slug': 'kitchen', 'sort_order': 4},
    {
        'name': 'Beverages',
        'slug': 'beverages-parent',
        'sort_order': 5,
        'children': [
            {'name': 'Beverages', 'slug': 'beverages'},
        ],
    },
    {'name': 'Pet Food', 'slug': 'pet-food', 'sort_order': 6},
    {
        'name': 'Frozen Foods',
        'slug': 'frozen-parent',
        'sort_order': 7,
        'children': [
            {'name': 'Frozen Foods', 'slug': 'frozen-foods'},
        ],
    },
    {'name': 'Bread & Bakery', 'slug': 'bread-bakery', 'sort_order': 8},
]


class Command(BaseCommand):
    help = 'Seed categories and products from the original static template data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush-products',
            action='store_true',
            help='Delete existing products before seeding.',
        )

    def handle(self, *args, **options):
        if options['flush_products']:
            Product.objects.all().delete()
            self.stdout.write('Cleared existing products.')

        categories = {}
        for data in CATEGORIES:
            parent, _ = Category.objects.update_or_create(
                slug=data['slug'],
                defaults={
                    'name': data['name'],
                    'sort_order': data['sort_order'],
                    'is_active': True,
                    'parent': None,
                },
            )
            categories[parent.slug] = parent
            for child in data.get('children', []):
                obj, _ = Category.objects.update_or_create(
                    slug=child['slug'],
                    defaults={
                        'name': child['name'],
                        'parent': parent,
                        'sort_order': 0,
                        'is_active': True,
                    },
                )
                categories[obj.slug] = obj

        seed_path = Path(settings.BASE_DIR) / 'seed_products.json'
        if seed_path.exists():
            products = json.loads(seed_path.read_text())
        else:
            products = extract_products_from_html(Path(settings.BASE_DIR))
            seed_path.write_text(json.dumps(products, indent=2))
            self.stdout.write(f'Extracted {len(products)} products from HTML templates.')
        media_dir = Path(settings.MEDIA_ROOT) / 'products'
        media_dir.mkdir(parents=True, exist_ok=True)
        created = 0
        updated = 0

        for i, item in enumerate(products):
            source = item.get('source', 'products.html')
            cat_slug = SOURCE_CATEGORY_MAP.get(source, 'branded-foods')
            category = categories.get(cat_slug) or categories['branded-foods']
            name = item['name']
            slug = slugify(name) or f'product-{i}'
            price = Decimal(item['price'])
            compare = Decimal(item['compare_at_price']) if item.get('compare_at_price') else None
            # Prefer label for nicer display names when present
            display_name = item.get('label') or name

            product, was_created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': display_name[:200],
                    'category': category,
                    'description': f'{display_name} — available at Alesi Grocery Store.',
                    'price': price,
                    'compare_at_price': compare,
                    'stock': 50,
                    'is_featured': i < 8,
                    'is_active': True,
                },
            )

            image_rel = item.get('image', '')
            src = Path(settings.BASE_DIR) / image_rel
            if src.exists() and src.is_file():
                dest_name = src.name
                # Avoid spaces issues in filenames for upload
                dest_name = dest_name.replace(' ', '_')
                if not product.image or Path(product.image.name).name != dest_name:
                    with src.open('rb') as fh:
                        product.image.save(dest_name, File(fh), save=True)

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seeded categories={len(categories)} products created={created} updated={updated}'
        ))
