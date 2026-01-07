from rest_framework import serializers
from .models import (
    Product, Supplier, Customer,
    Purchase, PurchaseItem,
    Sale, SaleItem, StockTransaction
)

class ProductSerializer(serializers.ModelSerializer):
    stock_quantity = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = "__all__"

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"

class PurchaseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = ("product", "quantity", "unit_price")

class PurchaseSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True)

    class Meta:
        model = Purchase
        fields = ("id", "supplier", "invoice_number", "date", "total", "items")

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        purchase = Purchase.objects.create(**validated_data)
        total = 0
        for item in items_data:
            pi = PurchaseItem.objects.create(purchase=purchase, **item)
            total += pi.quantity * pi.unit_price
            StockTransaction.objects.create(
                product=pi.product,
                quantity=pi.quantity,
                transaction_type=StockTransaction.IN,
                reference=f"Purchase {purchase.id}"
            )
        purchase.total = total
        purchase.save()
        return purchase

class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = ("product", "quantity", "unit_price")

class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)

    class Meta:
        model = Sale
        fields = ("id", "customer", "date", "total", "items")

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        sale = Sale.objects.create(**validated_data)
        total = 0
        for item in items_data:
            si = SaleItem.objects.create(sale=sale, **item)
            total += si.quantity * si.unit_price
            StockTransaction.objects.create(
                product=si.product,
                quantity=si.quantity,
                transaction_type=StockTransaction.OUT,
                reference=f"Sale {sale.id}"
            )
        sale.total = total
        sale.save()
        return sale