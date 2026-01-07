import json
import threading
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import login
from django.db import transaction
from django.db.models import Sum, Q, F
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import send_mail
from datetime import timedelta
from rest_framework import viewsets

from .models import (
    Product, Supplier, Customer, Purchase, Sale, SaleItem, 
    StockTransaction, Category, Unit, MpesaTransaction
)
from .forms import (
    ProductForm, SupplierForm, CustomerForm, PurchaseItemFormSet, SaleItemFormSet, 
    CustomerSignupForm, CategoryForm, UnitForm
)
from .serializers import ProductSerializer, SupplierSerializer, CustomerSerializer
from .utils import MpesaClient

# ==========================================
# AUTH & REDIRECTS
# ==========================================

def login_success_view(request):
    if request.user.is_staff:
        return redirect('inventory:dashboard')
    return redirect('inventory:store_home')

class CustomerSignupView(CreateView):
    template_name = "registration/signup.html"
    form_class = CustomerSignupForm
    success_url = reverse_lazy('inventory:store_home')

    def form_valid(self, form):
        user = form.save()
        Customer.objects.create(user=user, name=user.username, email=user.email)
        login(self.request, user)
        messages.success(self.request, "Account created successfully!")
        return redirect(self.success_url)

# ==========================================
# CUSTOMER / STOREFRONT VIEWS
# ==========================================

class StoreHomeView(ListView):
    model = Product
    template_name = "store/store_home.html"
    context_object_name = "products"
    paginate_by = 9

    def get_queryset(self):
        qs = Product.objects.filter(active=True)
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(sku__icontains=query))
        cat_id = self.request.GET.get('category')
        if cat_id:
            try:
                qs = qs.filter(category_id=int(cat_id))
            except ValueError:
                pass
        return qs.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['current_query'] = self.request.GET.get('q', '')
        context['current_category'] = self.request.GET.get('category', '')
        cart = self.request.session.get('cart', {})
        context['cart_count'] = sum(cart.values())
        return context

class StoreProductDetailView(DetailView):
    model = Product
    template_name = "store/product_detail.html"
    context_object_name = "product"

def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if product.stock_quantity <= 0:
        messages.error(request, "Item is out of stock.")
        return redirect('inventory:store_home')
    cart = request.session.get('cart', {})
    cart[str(pk)] = cart.get(str(pk), 0) + 1
    request.session['cart'] = cart
    messages.success(request, f"{product.name} added to cart.")
    return redirect('inventory:store_home')

def clear_cart(request):
    request.session['cart'] = {}
    return redirect('inventory:store_home')

def cart_view(request):
    cart = request.session.get('cart', {})
    items = []
    total = 0
    if cart:
        products = Product.objects.filter(pk__in=cart.keys())
        for p in products:
            qty = cart[str(p.pk)]
            line_total = p.selling_price * qty
            items.append({'product': p, 'quantity': qty, 'line_total': line_total})
            total += line_total
    return render(request, "store/cart.html", {'items': items, 'total': total})

def checkout_view(request):
    cart = request.session.get('cart', {})
    
    # Calculate totals for the initial GET request (Standard Checkout)
    total = 0
    items_with_details = []
    if cart:
        products = Product.objects.filter(pk__in=cart.keys())
        for p in products:
            qty = cart[str(p.pk)]
            line_total = p.selling_price * qty
            total += line_total
            items_with_details.append({'product': p, 'quantity': qty, 'line_total': line_total})

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.info(request, "Please login to complete your order.")
            return redirect('login')

        order_id = request.POST.get('order_id')  # From "My Orders" Popup
        payment_method = request.POST.get('payment_method')
        phone_number = request.POST.get('mpesa_phone')

        with transaction.atomic():
            # CASE 1: Paying for an existing PENDING order (from My Orders)
            if order_id:
                sale = get_object_or_404(Sale, pk=order_id, customer__user=request.user)
                if sale.status != 'PENDING':
                    messages.error(request, "This order is already processed or cancelled.")
                    return redirect('inventory:my_orders')
                total_to_pay = sale.total
            
            # CASE 2: New Checkout from Cart
            else:
                if not cart:
                    return redirect('inventory:store_home')
                
                customer, _ = Customer.objects.get_or_create(
                    user=request.user, 
                    defaults={'name': request.user.username, 'email': request.user.email}
                )

                # Validate Stock
                for pk, qty in cart.items():
                    product = get_object_or_404(Product, pk=pk)
                    if product.stock_quantity < qty:
                        messages.error(request, f"Insufficient stock for {product.name}.")
                        return redirect('inventory:cart')

                sale = Sale.objects.create(customer=customer, total=total, status='PENDING', channel='WEB')
                
                for pk, qty in cart.items():
                    product = get_object_or_404(Product, pk=pk)
                    SaleItem.objects.create(sale=sale, product=product, quantity=qty, unit_price=product.selling_price)
                    StockTransaction.objects.create(
                        product=product, quantity=-qty,
                        transaction_type=StockTransaction.OUT,
                        reference=f"Online Order #{sale.id}"
                    )
                total_to_pay = total

            # HANDLE M-PESA INTEGRATION
            if payment_method == 'mpesa' and phone_number:
                mpesa = MpesaClient()
                # Format phone to 2547XXXXXXXX
                formatted_phone = "254" + phone_number.lstrip('0').lstrip('+').lstrip('254')
                
                stk_response = mpesa.stk_push(formatted_phone, total_to_pay, sale.id)
                
                if stk_response.get('ResponseCode') == '0':
                    MpesaTransaction.objects.create(
                        sale=sale,
                        merchant_request_id=stk_response.get('MerchantRequestID'),
                        checkout_request_id=stk_response.get('CheckoutRequestID'),
                        amount=total_to_pay,
                        phone=formatted_phone
                    )
                    messages.success(request, f"M-Pesa prompt sent to {formatted_phone}.")
                else:
                    messages.error(request, "M-Pesa request failed. Please try again.")
                    # Only rollback if it's a new order; otherwise, just stay on the page
                    if not order_id:
                        transaction.set_rollback(True)
                    return redirect('inventory:my_orders' if order_id else 'inventory:checkout')

            # Finalize: Clear cart if this was a new checkout
            if not order_id:
                request.session['cart'] = {}
                # Send async email via our Utility
                EmailClient.send_order_confirmation(request.user, sale)
                messages.success(request, f"Order #{sale.id} placed successfully!")
            
            return redirect('inventory:my_orders')

    # GET Request: Only allow if there's a cart
    if not cart:
        return redirect('inventory:store_home')
        
    return render(request, "store/checkout.html", {
        'cart': cart, 
        'total': total,
        'items_with_details': items_with_details
    })

@csrf_exempt
def mpesa_callback(request):
    """Handles Safaricom M-Pesa Callback"""
    data = json.loads(request.body)
    stk_callback = data['Body']['stkCallback']
    checkout_id = stk_callback['CheckoutRequestID']
    result_code = stk_callback['ResultCode']
    
    try:
        transaction_record = MpesaTransaction.objects.get(checkout_request_id=checkout_id)
        if result_code == 0:
            transaction_record.status = 'COMPLETED'
            # Update the sale status
            sale = transaction_record.sale
            sale.status = 'COMPLETED'
            sale.save()
        else:
            transaction_record.status = 'FAILED'
        transaction_record.save()
    except MpesaTransaction.DoesNotExist:
        pass
        
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Success"})

class CustomerOrderListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = "store/my_orders.html"
    context_object_name = "orders"
    ordering = ['-date']

    def get_queryset(self):
        if hasattr(self.request.user, 'customer_profile'):
            return Sale.objects.filter(customer=self.request.user.customer_profile)
        return Sale.objects.none()

# ==========================================
# ADMIN / DASHBOARD VIEWS
# ==========================================

class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

class DashboardHomeView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products_count'] = Product.objects.count()
        context['suppliers_count'] = Supplier.objects.count()
        context['categories_count'] = Category.objects.count()
        all_products = Product.objects.all()
        context['low_stock_products'] = [p for p in all_products if p.stock_quantity <= p.reorder_level]
        today = timezone.now().date()
        daily_sales = Sale.objects.filter(date__date=today, status='COMPLETED').aggregate(total=Sum('total'))
        context['todays_sales'] = daily_sales.get('total') or 0.00
        context['pending_orders'] = Sale.objects.filter(status='PENDING', channel='WEB').count()
        return context


class AdminReportView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        today = now.date()
        
        # 1. Get Filter Parameter
        period = self.request.GET.get('period', 'today')
        start_date = None
        end_date = now

        # 2. Define Date Ranges
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'weekly':
            start_date = now - timedelta(days=7)
        elif period == 'monthly':
            start_date = now - timedelta(days=30)
        elif period == 'yearly':
            start_date = now - timedelta(days=365)
        elif period == 'custom':
            custom_start = self.request.GET.get('start_date')
            custom_end = self.request.GET.get('end_date')
            if custom_start and custom_end:
                start_date = timezone.datetime.strptime(custom_start, '%Y-%m-%d')
                end_date = timezone.datetime.strptime(custom_end, '%Y-%m-%d') + timedelta(days=1)
        
        # 3. Filter Sales Data
        sales_qs = Sale.objects.filter(status='COMPLETED')
        if start_date:
            sales_qs = sales_qs.filter(date__range=(start_date, end_date))

        # 4. Context Calculations
        context['period_revenue'] = sales_qs.aggregate(Sum('total'))['total__sum'] or 0
        context['total_revenue'] = Sale.objects.filter(status='COMPLETED').aggregate(Sum('total'))['total__sum'] or 0
        context['today_revenue'] = Sale.objects.filter(status='COMPLETED', date__date=today).aggregate(Sum('total'))['total__sum'] or 0
        
        context['recent_sales'] = sales_qs.order_by('-date')[:10]
        
        # Counts & Alerts (Static)
        context['total_products'] = Product.objects.count()
        context['total_suppliers'] = Supplier.objects.count()
        context['total_customers'] = Customer.objects.count()
        all_products = Product.objects.all()
        context['critical_stock'] = [p for p in all_products if p.stock_quantity <= 0]
        context['reorder_stock'] = [p for p in all_products if p.stock_quantity > 0 and p.stock_quantity <= p.reorder_level]
        
        # Meta Data
        context['report_date'] = now
        context['current_period'] = period
        return context

class OrderListView(StaffRequiredMixin, ListView):
    model = Sale
    template_name = "dashboard/order_list.html"
    context_object_name = "orders"
    def get_queryset(self):
        return Sale.objects.filter(channel='WEB').order_by('-date')

def approve_order(request, pk):
    if not request.user.is_staff: return redirect('login')
    order = get_object_or_404(Sale, pk=pk)
    if order.status == 'PENDING':
        with transaction.atomic():
            order.status = 'COMPLETED'
            order.save()
            messages.success(request, f"Order #{order.id} marked as Completed.")
    return redirect('inventory:order_list')

# --- STOCK & SETTINGS ---
class StockTransactionListView(StaffRequiredMixin, ListView):
    model = StockTransaction
    template_name = "dashboard/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 30

class CategoryListView(StaffRequiredMixin, ListView):
    model = Category
    template_name = "categories/category_list.html"
    context_object_name = "categories"

class CategoryCreateView(StaffRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "categories/category_form.html"
    success_url = reverse_lazy("inventory:category_list")

class CategoryUpdateView(StaffRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "categories/category_form.html"
    success_url = reverse_lazy("inventory:category_list")

class CategoryDeleteView(StaffRequiredMixin, DeleteView):
    model = Category
    template_name = "categories/category_confirm_delete.html"
    success_url = reverse_lazy("inventory:category_list")

class UnitListView(StaffRequiredMixin, ListView):
    model = Unit
    template_name = "units/unit_list.html"
    context_object_name = "units"

class UnitCreateView(StaffRequiredMixin, CreateView):
    model = Unit
    form_class = UnitForm
    template_name = "units/unit_form.html"
    success_url = reverse_lazy("inventory:unit_list")

class UnitUpdateView(StaffRequiredMixin, UpdateView):
    model = Unit
    form_class = UnitForm
    template_name = "units/unit_form.html"
    success_url = reverse_lazy("inventory:unit_list")

class UnitDeleteView(StaffRequiredMixin, DeleteView):
    model = Unit
    template_name = "units/unit_confirm_delete.html"
    success_url = reverse_lazy("inventory:unit_list")

class ProductListView(StaffRequiredMixin, ListView):
    model = Product
    template_name = "products/product_list.html"
    context_object_name = "products"
    paginate_by = 20

class ProductCreateView(StaffRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "products/product_form.html"
    success_url = reverse_lazy("inventory:product_list")

class ProductUpdateView(StaffRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "products/product_form.html"
    success_url = reverse_lazy("inventory:product_list")

class ProductDeleteView(StaffRequiredMixin, DeleteView):
    model = Product
    template_name = "products/product_confirm_delete.html"
    success_url = reverse_lazy("inventory:product_list")

class SupplierListView(StaffRequiredMixin, ListView):
    model = Supplier
    template_name = "suppliers/supplier_list.html"
    context_object_name = "suppliers"
    paginate_by = 20

class SupplierCreateView(StaffRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "suppliers/supplier_form.html"
    success_url = reverse_lazy("inventory:supplier_list")

class CustomerListView(StaffRequiredMixin, ListView):
    model = Customer
    template_name = "customers/customer_list.html"
    context_object_name = "customers"
    paginate_by = 20

class CustomerCreateView(StaffRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "customers/customer_form.html"
    success_url = reverse_lazy("inventory:customer_list")

# --- POS & PURCHASES ---
def pos_sale_create_view(request):
    if not request.user.is_staff: return redirect("login")
    if request.method == "POST":
        formset = SaleItemFormSet(request.POST, prefix="items")
        customer_id = request.POST.get("customer")
        if formset.is_valid():
            with transaction.atomic():
                customer = None
                if customer_id:
                    customer = get_object_or_404(Customer, pk=customer_id)
                
                sale = Sale.objects.create(customer=customer, status='COMPLETED', channel='POS', total=0)
                
                total = 0
                for item in formset:
                    if item.cleaned_data and not item.cleaned_data.get("DELETE", False):
                        prod = item.cleaned_data['product']
                        qty = item.cleaned_data['quantity']
                        
                        # Use the form's unit price, or fallback to the product's default selling price
                        unit_price = item.cleaned_data.get('unit_price') or prod.selling_price
                        
                        if prod.stock_quantity < qty:
                             messages.error(request, f"Not enough stock for {prod.name}")
                             transaction.set_rollback(True)
                             return redirect("inventory:sale_add")
                        
                        si = item.save(commit=False)
                        si.sale = sale
                        si.unit_price = unit_price  # Force the unit price here
                        si.save()
                        
                        total += qty * unit_price
                        
                        StockTransaction.objects.create(
                            product=prod, 
                            quantity=-qty,
                            transaction_type=StockTransaction.OUT, 
                            reference=f"POS Sale {sale.id}"
                        )
                
                sale.total = total
                sale.save()
                messages.success(request, f"POS Sale #{sale.id} recorded for KES {total}")
                return redirect("inventory:dashboard")
    else:
        formset = SaleItemFormSet(prefix="items")
    
    customers = Customer.objects.all()
    # Pass product prices to JS as a JSON object
    product_data = {p.id: float(p.selling_price) for p in Product.objects.all()}
    
    return render(request, "sales/sale_form.html", {
        "formset": formset, 
        "customers": customers,
        "product_data": json.dumps(product_data) # Send to template
    })

def purchase_create_view(request):
    if not request.user.is_staff: return redirect("login")
    if request.method == "POST":
        formset = PurchaseItemFormSet(request.POST, prefix="items")
        supplier_id = request.POST.get("supplier")
        if formset.is_valid() and supplier_id:
            with transaction.atomic():
                supplier = get_object_or_404(Supplier, pk=supplier_id)
                purchase = Purchase.objects.create(supplier=supplier)
                total = 0
                for item in formset:
                    if item.cleaned_data and not item.cleaned_data.get("DELETE", False):
                        pi = item.save(commit=False)
                        pi.purchase = purchase
                        pi.save()
                        total += pi.quantity * pi.unit_price
                        StockTransaction.objects.create(
                            product=pi.product, quantity=pi.quantity,
                            transaction_type=StockTransaction.IN, 
                            reference=f"Purchase {purchase.id}"
                        )
                purchase.total = total
                purchase.save()
                messages.success(request, "Purchase recorded.")
                return redirect("inventory:dashboard")
    else:
        formset = PurchaseItemFormSet(prefix="items")
    suppliers = Supplier.objects.all()
    return render(request, "purchases/purchase_form.html", {"formset": formset, "suppliers": suppliers})

# --- API ---
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer