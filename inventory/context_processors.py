from .models import Product, Supplier, Customer

def quick_counts(request):
    return {
        "products_count": Product.objects.count(),
        "suppliers_count": Supplier.objects.count(),
        "customers_count": Customer.objects.count(),
    }