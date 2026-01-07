from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Unit(models.Model):
    name = models.CharField(max_length=50)
    abbreviation = models.CharField(max_length=10, blank=True)
    def __str__(self): return self.name

class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey("self", null=True, blank=True, related_name="children", on_delete=models.SET_NULL)
    def __str__(self): return self.name

class Product(models.Model):
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.SET_NULL)
    buying_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.PositiveIntegerField(default=5)
    active = models.BooleanField(default=True)

    def __str__(self): return f"{self.name} ({self.sku})"

    @property
    def stock_quantity(self):
        from django.db.models import Sum
        qs = StockTransaction.objects.filter(product=self).aggregate(qty=Sum("quantity"))
        return qs.get("qty") or 0

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    def __str__(self): return self.name

class Customer(models.Model):
    # NEW: Link to Django User for online auth
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_profile')
    
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    def __str__(self): return self.name

class Purchase(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    invoice_number = models.CharField(max_length=128, blank=True)
    date = models.DateTimeField(default=timezone.now)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    def __str__(self): return f"PO {self.id} - {self.supplier.name}"

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

class Sale(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending (Online)'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    CHANNEL_CHOICES = [
        ('POS', 'In-Store'),
        ('WEB', 'Online Store'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='COMPLETED')
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='POS')

    def __str__(self): return f"Sale {self.id} - {self.date.date()} ({self.status})"

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

class StockTransaction(models.Model):
    IN = "IN"
    OUT = "OUT"
    TRANSACTION_TYPES = [(IN, "In"), (OUT, "Out")]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="transactions")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPES)
    reference = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    class Meta: ordering = ("-timestamp",)

class MpesaTransaction(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments')
    merchant_request_id = models.CharField(max_length=100)
    checkout_request_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone = models.CharField(max_length=15)
    status = models.CharField(max_length=20, default='PENDING') # PENDING, COMPLETED, FAILED
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.checkout_request_id} - {self.status}"