from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product, Supplier, Customer, Purchase, PurchaseItem, Sale, SaleItem, Category, Unit

class CustomerSignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email"]

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "parent"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
        }

class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ["name", "abbreviation"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Kilogram"}),
            "abbreviation": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. kg"}),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["sku", "name", "description", "image", "category", "unit", "buying_price", "selling_price", "reorder_level", "active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "sku": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "unit": forms.Select(attrs={"class": "form-select"}),
            "buying_price": forms.NumberInput(attrs={"class": "form-control"}),
            "selling_price": forms.NumberInput(attrs={"class": "form-control"}),
            "reorder_level": forms.NumberInput(attrs={"class": "form-control"}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "phone", "email", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "email", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }

PurchaseItemFormSet = inlineformset_factory(
    Purchase, PurchaseItem, fields=("product", "quantity", "unit_price"), extra=1, can_delete=True
)

SaleItemFormSet = inlineformset_factory(
    Sale, SaleItem, fields=("product", "quantity", "unit_price"), extra=1, can_delete=True
)