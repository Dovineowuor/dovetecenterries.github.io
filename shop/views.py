import base64
from datetime import datetime
import json
import requests
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Category, Order, Payment, Product
from .forms import OrderForm
from shop.models import Product, Cart, CartItem


# Product Views
def product_list(request):
    context = {
        'page_title': 'Innovation Shop - Dovetec Enterprises | Products & Services',
        'seo_desc': 'Browse our products and services at Dovetec Enterprises. Software solutions, IT services, and consulting offerings from Kenya\'s leading tech company.',
        'og_title': 'Innovation Shop - Dovetec Enterprises',
        'og_desc': 'Browse our products and services at Dovetec Enterprises.',
        'og_type': 'website',
        'twitter_title': 'Innovation Shop - Dovetec Enterprises',
        'twitter_desc': 'Browse our products and services at Dovetec Enterprises.',
    }
    products = Product.objects.all()
    context['products'] = products
    return render(request, 'app/products.html', context)

def product_list_by_category(request, category_id=None):
    category = None
    if category_id:
        category = get_object_or_404(Category, id=category_id)
    page_title = f'{category.name if category else "Products"} - Dovetec Enterprises'
    seo_desc = f'Browse {category.name if category else "our products"} at Dovetec Enterprises. Software solutions, IT services, and innovative products from Kenya.'
    context = {
        'page_title': category.meta_title or page_title if category else page_title,
        'seo_desc': category.meta_description or seo_desc if category else seo_desc,
        'og_title': (category.og_title or page_title) if category else page_title,
        'og_desc': (category.og_description or seo_desc) if category else seo_desc,
        'og_type': 'website',
        'twitter_title': (category.twitter_title or page_title) if category else page_title,
        'twitter_desc': (category.twitter_description or seo_desc) if category else seo_desc,
    }
    products = Product.objects.filter(category_id=category_id) if category_id else Product.objects.all()
    context['products'] = products
    return render(request, 'shop/product_list.html', context)


# Cart Views
def cart_view(request):
    session_key = request.session.session_key or request.session.save() or request.session.session_key
    cart, _ = Cart.objects.get_or_create(session_key=session_key)
    items = cart.items.select_related('product').all()
    total = cart.total_price()
    return render(request, 'shop/cart.html', {
        'cart': cart,
        'items': items,
        'total': total,
        'page_title': 'Your Basket - Dovetec Enterprises',
        'seo_desc': 'Review items in your Dovetec Enterprises shopping basket and proceed to secure checkout.',
        'og_title': 'Your Basket - Dovetec Enterprises',
        'og_desc': 'Review items in your shopping basket and check out securely.',
    })


def add_to_cart(request, product_id):
    session_key = request.session.session_key or request.session.save() or request.session.session_key
    cart, _ = Cart.objects.get_or_create(session_key=session_key)
    product = Product.objects.get(id=product_id)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity += 1
        item.save()
    return redirect('cart')


def remove_from_cart(request, item_id):
    session_key = request.session.session_key or request.session.save() or request.session.session_key
    cart = Cart.objects.filter(session_key=session_key).first()
    if cart:
        CartItem.objects.filter(cart=cart, id=item_id).delete()
    return redirect('cart')


def update_cart_item(request, item_id):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        item = get_object_or_404(CartItem, id=item_id)
        if quantity > 0:
            item.quantity = quantity
            item.save()
        else:
            item.delete()
    return redirect('cart')


def apply_discount(request):
    """Placeholder for discount logic."""
    if request.method == 'POST':
        # Logic for discount validation goes here
        pass
    return redirect('cart')


def checkout(request):
    """Bridge from cart to the unified order creation page."""
    session_key = request.session.session_key
    cart = Cart.objects.filter(session_key=session_key).first()
    if not cart or not cart.items.exists():
        return redirect('cart')
    
    return redirect('order_create_cart')


# Category Views
def category_list(request):
    """Fetch and display all categories."""
    categories = Category.objects.all()
    return render(request, 'shop/categories.html', {
        'categories': categories,
        'page_title': 'Shop Categories - Dovetec Enterprises',
        'seo_desc': 'Browse all product categories at the Dovetec Enterprises shop — software solutions, IT services, and more.',
        'og_title': 'Shop Categories - Dovetec Enterprises',
        'og_desc': 'Browse all product categories at the Dovetec Enterprises shop.',
    })


# Order Views
from .models import OrderItem

def order_create(request, product_id=None):
    """Unified order creation for single-product or full-cart checkouts."""
    session_key = request.session.session_key
    cart = Cart.objects.filter(session_key=session_key).first()
    product = None

    if product_id:
        product = get_object_or_404(Product, id=product_id)
    elif not cart or not cart.items.exists():
        return redirect('shop')

    if request.method == 'POST':
        # Using simple POST data for demonstration; ideally use a ModelForm
        customer_name = request.POST.get('customer_name')
        customer_email = request.POST.get('customer_email')
        customer_phone = request.POST.get('customer_phone')
        address = request.POST.get('address')
        city = request.POST.get('city')

        if customer_name and customer_email:
            order = Order.objects.create(
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                address=address,
                city=city,
                total_amount=0  # Will update after adding items
            )

            if product:
                # Single product purchase
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=int(request.POST.get('quantity', 1)),
                    price_at_purchase=product.price
                )
            else:
                # Full cart purchase
                for item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price_at_purchase=item.product.price
                    )
                # Clear the cart
                cart.items.all().delete()

            order.update_total()
            return redirect('process_payment', order_id=order.id)
            
    return render(request, 'shop/order_create.html', {
        'product': product,
        'cart': cart if not product else None,
        'page_title': 'Checkout - Dovetec Enterprises',
        'seo_desc': 'Complete your Dovetec Enterprises order securely with M-Pesa or PayPal.',
        'og_title': 'Checkout - Dovetec Enterprises',
        'og_desc': 'Complete your order securely with M-Pesa or PayPal.',
    })


def order_success(request, order_id):
    """Display a success message after order creation."""
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'shop/order_success.html', {'order': order})


# Payment Views
def process_payment(request, order_id):
    """Process payment for a specific order."""
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        amount = order.total_amount

        if payment_method == 'Mpesa':
            mpesa_response = process_mpesa_payment(amount, order)
            return handle_payment_response(mpesa_response, order, amount, 'M-Pesa')

        elif payment_method == 'PayPal':
            paypal_response = process_paypal_payment(amount, order)
            if paypal_response.get('status') == 'success':
                # PayPal requires redirection to their approval page
                return redirect(paypal_response['redirect_url'])
            return handle_payment_response(paypal_response, order, amount, 'PayPal')

    return render(request, 'shop/payment.html', {'order': order})


def handle_payment_response(response, order, amount, payment_method):
    """Handle the payment response for both M-Pesa and PayPal."""
    if response.get('status') == 'success':
        Payment.objects.create(
            order=order,
            amount=amount,
            payment_method=payment_method,
            transaction_id=response['transaction_id'],
            is_successful=True
        )
        order.status = 'paid'
        order.save()
        return redirect('order_success', order_id=order.id)
    else:
        # Log error details for failed payment
        print(f"Payment failed: {response.get('message', 'Unknown error')}")
        return redirect('order_failure', order_id=order.id)  # Redirect to a failure page


def order_failure(request, order_id):
    """Display a message when payment fails."""
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'shop/order_failure.html', {'order': order})


# M-Pesa Functions
def get_mpesa_access_token():
    """Retrieve M-Pesa access token using Basic Auth."""
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    try:
        response = requests.get(api_url, auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET))
        return response.json().get('access_token')
    except Exception as e:
        print(f"M-Pesa Token Error: {e}")
        return None


def get_mpesa_password(timestamp):
    """Generate M-Pesa STK Push password."""
    data_to_encode = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    encoded_string = base64.b64encode(data_to_encode.encode())
    return encoded_string.decode('utf-8')


def process_mpesa_payment(amount, order):
    """Integrate with M-Pesa Daraja API for STK Push."""
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    token = get_mpesa_access_token()
    if not token:
        return {'status': 'error', 'message': 'Could not get M-Pesa token'}

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = get_mpesa_password(timestamp)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount), # Daraja STK push expects integer for amount usually or float
        "PartyA": order.customer_phone or settings.MPESA_PHONE_NUMBER,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": order.customer_phone or settings.MPESA_PHONE_NUMBER,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": f"DT-{order.id}",
        "TransactionDesc": f"Payment for Order {order.id}"
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        res_data = response.json()
        if res_data.get('ResponseCode') == '0':
            return {'status': 'success', 'transaction_id': res_data.get('CheckoutRequestID')}
        return {'status': 'error', 'message': res_data.get('ResponseDescription', 'STK Push failed')}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# PayPal Functions
def get_paypal_access_token():
    """Retrieve PayPal access token."""
    api_url = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    try:
        response = requests.post(
            api_url, 
            headers={"Accept": "application/json", "Accept-Language": "en_US"}, 
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET), 
            data={"grant_type": "client_credentials"}
        )
        return response.json().get('access_token')
    except Exception as e:
        print(f"PayPal Token Error: {e}")
        return None


def process_paypal_payment(amount, order):
    """Integrate with PayPal API to create a payment."""
    api_url = "https://api-m.sandbox.paypal.com/v1/payments/payment"
    token = get_paypal_access_token()
    if not token:
        return {'status': 'error', 'message': 'Could not get PayPal token'}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # Convert KES to USD (Example conversion rate)
    amount_usd = round(float(amount) / 130, 2)

    payload = {
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "transactions": [{
            "amount": {"total": str(amount_usd), "currency": "USD"},
            "description": f"Dovetec Order #{order.id}"
        }],
        "redirect_urls": {
            "return_url": settings.PAYPAL_SUCCESS_URL,
            "cancel_url": settings.PAYPAL_CANCEL_URL
        }
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        res_data = response.json()
        if response.status_code in [200, 201]:
            # Find the approval URL
            approval_url = next(link['href'] for link in res_data['links'] if link['rel'] == 'approval_url')
            return {'status': 'success', 'redirect_url': approval_url, 'transaction_id': res_data['id']}
        return {'status': 'error', 'message': res_data.get('message', 'PayPal payment creation failed')}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# Callbacks
@csrf_exempt
def mpesa_callback(request):
    """Handle M-Pesa callback for payment updates from Safaricom Daraja API."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            stk_callback = data.get('Body', {}).get('stkCallback', {})
            
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')

            # Find the payment record created during initiation
            try:
                payment = Payment.objects.get(transaction_id=checkout_request_id)
                order = payment.order
                
                if result_code == 0:
                    # Success
                    payment.is_successful = True
                    # Extract MpesaReceiptNumber if available
                    metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                    for item in metadata:
                        if item.get('Name') == 'MpesaReceiptNumber':
                            payment.transaction_id = f"{checkout_request_id}|{item.get('Value')}"
                            break
                    
                    payment.save()
                    order.status = 'paid'
                    order.save()
                    print(f"M-Pesa payment SUCCESS for Order {order.id}: {result_desc}")
                else:
                    # Failure (User cancelled, timeout, etc.)
                    payment.is_successful = False
                    payment.save()
                    order.status = 'failed'
                    order.save()
                    print(f"M-Pesa payment FAILED for Order {order.id}: {result_desc}")
                
                return JsonResponse({'status': 'success', 'message': 'Callback processed'})
                
            except Payment.DoesNotExist:
                print(f"M-Pesa Callback Error: No payment record found for CheckoutRequestID {checkout_request_id}")
                return JsonResponse({'error': 'Payment record not found'}, status=404)

        except Exception as e:
            print(f"M-Pesa Callback Exception: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)



@csrf_exempt
def paypal_callback(request):
    """Handle PayPal callback for payment updates."""
    if request.method == 'POST':
        data = json.loads(request.body)
        transaction_id = data.get('id')  # PayPal's transaction ID
        status = data.get('status')  # e.g., "COMPLETED" or "FAILED"
        order_id = data.get('order_id')  # Include this in your callback payload

        return update_payment_status(transaction_id, order_id, status)

    return JsonResponse({'error': 'Invalid request'}, status=400)


def update_payment_status(transaction_id, order_id, status):
    """Update payment status in the database based on the callback."""
    try:
        order = Order.objects.get(id=order_id)
        payment = Payment.objects.get(order=order)

        payment.is_successful = (status == 'Success' or status == 'COMPLETED')
        payment.transaction_id = transaction_id
        payment.save()

        # Here you can handle post-payment logic, e.g., sending confirmation emails.

        return JsonResponse({'status': 'success'})

    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    except Payment.DoesNotExist:
        return JsonResponse({'error': 'Payment not found'}, status=404)
