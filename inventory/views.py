from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import login
from django.db import transaction
from django.db.models import Sum, Q, F
from django.utils import timezone
from rest_framework import viewsets

from .models import Product, Supplier, Customer, Purchase, Sale, SaleItem, StockTransaction, Category, Unit
from .forms import (
    ProductForm, SupplierForm, CustomerForm, PurchaseItemFormSet, SaleItemFormSet, 
    CustomerSignupForm, CategoryForm, UnitForm
)
from .serializers import ProductSerializer, SupplierSerializer, CustomerSerializer

# ==========================================
# AUTH & REDIRECTS
# ==========================================

def login_success_view(request):
    """
    Redirects users based on their role.
    Admins -> Dashboard
    Customers -> Store Home
    """
    if request.user.is_staff:
        return redirect('inventory:dashboard')
    return redirect('inventory:store_home')

class CustomerSignupView(CreateView):
    template_name = "registration/signup.html"
    form_class = CustomerSignupForm
    success_url = reverse_lazy('inventory:store_home')

    def form_valid(self, form):
        user = form.save()
        # Create linked Customer Profile
        Customer.objects.create(
            user=user,
            name=user.username,
            email=user.email
        )
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
        
        # 1. Search Logic
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(
                Q(name__icontains=query) | 
                Q(description__icontains=query) |
                Q(sku__icontains=query)
            )
            
        # 2. Category Filter
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
    if not cart:
        return redirect('inventory:store_home')
        
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.info(request, "Please login to complete your order.")
            return redirect('login')

        with transaction.atomic():
            # 1. Get or create customer profile
            try:
                customer = request.user.customer_profile
            except (AttributeError, Customer.DoesNotExist):
                customer = Customer.objects.create(
                    user=request.user, 
                    name=request.user.username,
                    email=request.user.email
                )

            # 2. Validate Stock Levels BEFORE creating order
            for pk, qty in cart.items():
                product = get_object_or_404(Product, pk=pk)
                if product.stock_quantity < qty:
                    messages.error(request, f"Insufficient stock for {product.name}. Available: {product.stock_quantity}")
                    return redirect('inventory:cart')

            # 3. Create Sale (Pending)
            sale = Sale.objects.create(
                customer=customer,
                total=0,
                status='PENDING',
                channel='WEB'
            )
            
            total = 0
            for pk, qty in cart.items():
                product = get_object_or_404(Product, pk=pk)
                
                # Create Sale Item
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=qty,
                    unit_price=product.selling_price
                )
                total += product.selling_price * qty
                
                # 4. DEDUCT STOCK IMMEDIATELY (Reserve it)
                StockTransaction.objects.create(
                    product=product,
                    quantity=qty,
                    transaction_type=StockTransaction.OUT,
                    reference=f"Online Order #{sale.id}"
                )
            
            sale.total = total
            sale.save()
            
            request.session['cart'] = {}
            messages.success(request, f"Order #{sale.id} placed! Stock has been reserved.")
            return redirect('inventory:my_orders')
            
    return render(request, "store/checkout.html", {'cart': cart})

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
        
        # Counts
        context['products_count'] = Product.objects.count()
        context['suppliers_count'] = Supplier.objects.count()
        context['categories_count'] = Category.objects.count()
        
        # Stock Logic
        all_products = Product.objects.all()
        context['low_stock_products'] = [p for p in all_products if p.stock_quantity <= p.reorder_level]
        
        # Sales Logic
        today = timezone.now().date()
        daily_sales = Sale.objects.filter(date__date=today, status='COMPLETED').aggregate(total=Sum('total'))
        context['todays_sales'] = daily_sales.get('total') or 0.00
        
        context['pending_orders'] = Sale.objects.filter(status='PENDING', channel='WEB').count()
        return context

# --- REPORT GENERATION (New) ---
class AdminReportView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        context['total_products'] = Product.objects.count()
        context['total_suppliers'] = Supplier.objects.count()
        context['total_customers'] = Customer.objects.count()
        
        # Revenue
        total_revenue = Sale.objects.filter(status='COMPLETED').aggregate(Sum('total'))['total__sum'] or 0
        today_revenue = Sale.objects.filter(status='COMPLETED', date__date=today).aggregate(Sum('total'))['total__sum'] or 0
        context['total_revenue'] = total_revenue
        context['today_revenue'] = today_revenue

        # Stock Lists
        all_products = Product.objects.all()
        context['critical_stock'] = [p for p in all_products if p.stock_quantity <= 0]
        context['reorder_stock'] = [p for p in all_products if p.stock_quantity > 0 and p.stock_quantity <= p.reorder_level]

        # Recent Activity
        context['recent_sales'] = Sale.objects.filter(status='COMPLETED').order_by('-date')[:10]
        context['report_date'] = timezone.now()
        
        return context

# --- ORDER MANAGEMENT ---
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
        # Stock was already deducted at checkout.
        # We just confirm the status here.
        with transaction.atomic():
            order.status = 'COMPLETED'
            order.save()
            messages.success(request, f"Order #{order.id} marked as Completed.")
            
    return redirect('inventory:order_list')

# --- STOCK HISTORY ---
class StockTransactionListView(StaffRequiredMixin, ListView):
    model = StockTransaction
    template_name = "dashboard/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 30

# --- CATEGORIES (New) ---
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

# --- UNITS (New) ---
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

# --- PRODUCTS ---
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

# --- SUPPLIERS & CUSTOMERS ---
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
                
                sale = Sale.objects.create(
                    customer=customer, 
                    status='COMPLETED', 
                    channel='POS'
                )
                
                total = 0
                for item in formset:
                    if item.cleaned_data and not item.cleaned_data.get("DELETE", False):
                        prod = item.cleaned_data['product']
                        qty = item.cleaned_data['quantity']
                        
                        # Validate Stock
                        if prod.stock_quantity < qty:
                             messages.error(request, f"Not enough stock for {prod.name}")
                             transaction.set_rollback(True)
                             return redirect("inventory:sale_add")
                        
                        si = item.save(commit=False)
                        si.sale = sale
                        si.save()
                        total += si.quantity * si.unit_price
                        
                        # Deduct Stock
                        StockTransaction.objects.create(
                            product=prod, 
                            quantity=qty,
                            transaction_type=StockTransaction.OUT, 
                            reference=f"POS Sale {sale.id}"
                        )
                sale.total = total
                sale.save()
                messages.success(request, "POS Sale recorded.")
                return redirect("inventory:dashboard")
    else:
        formset = SaleItemFormSet(prefix="items")
    customers = Customer.objects.all()
    return render(request, "sales/sale_form.html", {"formset": formset, "customers": customers})

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
                        
                        # Add Stock (IN)
                        StockTransaction.objects.create(
                            product=pi.product, 
                            quantity=pi.quantity,
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
class PurchaseViewSet(viewsets.ModelViewSet):
    queryset = Purchase.objects.all()
    serializer_class = ProductSerializer # Note: Should ideally use dedicated serializer
class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = ProductSerializer # Note: Should ideally use dedicated serializer