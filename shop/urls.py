# urls.py
from django.urls import path
from .views import (
    product_list,
    product_list_by_category,
    cart_view,
    add_to_cart,
    update_cart_item,
    remove_from_cart,
    apply_discount,
    checkout,
    category_list,
    order_create,
    order_success,
    order_failure,
    process_payment,
    mpesa_callback,
    paypal_callback,
)

urlpatterns = [
    # Product URLs
    path('', product_list, name='shop'),
    path('products/category/<int:category_id>/', product_list_by_category, name='product_list_by_category'),

    # Category URLs
    path('categories/', category_list, name='category_list'),

    # Cart URLs
    path('cart/', cart_view, name='cart'),
    path('cart/add/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/apply-discount/', apply_discount, name='apply_discount'),
    path('cart/checkout/', checkout, name='checkout'),

    # Order URLs
    path('order/create/', order_create, name='order_create_cart'),
    path('order/create/<int:product_id>/', order_create, name='order_create'),
    path('order/success/<int:order_id>/', order_success, name='order_success'),
    path('order/failure/<int:order_id>/', order_failure, name='order_failure'),

    # Payment URLs
    path('payment/process/<int:order_id>/', process_payment, name='process_payment'),

    # Callback URLs
    path('payment/mpesa/callback/', mpesa_callback, name='mpesa_callback'),
    path('payment/paypal/callback/', paypal_callback, name='paypal_callback'),
]
