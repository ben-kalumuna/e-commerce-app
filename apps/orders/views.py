from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.forms import AddressForm
from apps.accounts.models import Address
from apps.cart.utils import get_cart

from .models import Order, create_order_from_cart

SERVICE_CHARGE = Decimal('0.00')


@login_required
def checkout(request):
    active = Order.open_orders_for(request.user).order_by('-created_at').first()
    if active:
        messages.warning(
            request,
            f'Order #{active.pk} is still awaiting delivery. '
            f'Confirm you received it before placing a new order.',
        )
        return redirect('accounts:order_detail', pk=active.pk)

    cart = get_cart(request, create=True)
    items = list(cart.items.select_related('product'))
    if not items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart:detail')

    addresses = request.user.addresses.all()
    form = AddressForm()

    if request.method == 'POST':
        use_address_id = request.POST.get('address_id')
        address_data = None
        if use_address_id:
            addr = get_object_or_404(Address, pk=use_address_id, user=request.user)
            address_data = {
                'full_name': addr.full_name,
                'phone': addr.phone,
                'landmark': addr.landmark,
                'city': addr.city,
                'address_line': addr.address_line,
                'address_type': addr.address_type,
            }
        else:
            form = AddressForm(request.POST)
            if form.is_valid():
                addr = form.save(commit=False)
                addr.user = request.user
                if not addresses.exists():
                    addr.is_default = True
                addr.save()
                address_data = {
                    'full_name': addr.full_name,
                    'phone': addr.phone,
                    'landmark': addr.landmark,
                    'city': addr.city,
                    'address_line': addr.address_line,
                    'address_type': addr.address_type,
                }
            else:
                messages.error(request, 'Please correct the address details.')

        if address_data:
            try:
                order = create_order_from_cart(
                    user=request.user,
                    cart=cart,
                    address_data=address_data,
                    service_charge=SERVICE_CHARGE,
                )
                messages.success(
                    request,
                    f'Order #{order.pk} placed. Items stay in your cart until you '
                    f'confirm delivery and pay cash on delivery.',
                )
                return redirect('orders:success', pk=order.pk)
            except ValueError as exc:
                messages.error(request, str(exc))

    return render(
        request,
        'orders/checkout.html',
        {
            'cart': cart,
            'items': items,
            'subtotal': cart.subtotal,
            'service_charge': SERVICE_CHARGE,
            'total': cart.subtotal + SERVICE_CHARGE,
            'form': form,
            'addresses': addresses,
        },
    )


@login_required
def order_success(request, pk):
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        pk=pk,
        user=request.user,
    )
    return render(request, 'orders/success.html', {'order': order})
