from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    # ... (Keep existing Auth & Store URLs) ...
    path("login-redirect/", views.login_success_view, name="login_redirect"),
    path("signup/", views.CustomerSignupView.as_view(), name="signup"),
    path("", views.StoreHomeView.as_view(), name="store_home"),
    path("store/my-orders/", views.CustomerOrderListView.as_view(), name="my_orders"),
    path("store/product/<int:pk>/", views.StoreProductDetailView.as_view(), name="store_product_detail"),
    path("store/cart/", views.cart_view, name="cart"),
    path("store/cart/add/<int:pk>/", views.add_to_cart, name="add_to_cart"),
    path("store/cart/clear/", views.clear_cart, name="clear_cart"),
    path("store/checkout/", views.checkout_view, name="checkout"),

    # --- Admin Interface (Dashboard) ---
    path("dashboard/", views.DashboardHomeView.as_view(), name="dashboard"),
    
    # NEW: Report Generation URL
    path("dashboard/report/", views.AdminReportView.as_view(), name="admin_report"),

    path("dashboard/stock-history/", views.StockTransactionListView.as_view(), name="stock_history"),
    path("dashboard/orders/", views.OrderListView.as_view(), name="order_list"),
    path("dashboard/orders/<int:pk>/approve/", views.approve_order, name="approve_order"),
    path("dashboard/sales/add/", views.pos_sale_create_view, name="sale_add"),
    path("dashboard/purchases/add/", views.purchase_create_view, name="purchase_add"),

    # ... (Keep existing Management URLs for Products, Suppliers, etc.) ...
    path("dashboard/products/", views.ProductListView.as_view(), name="product_list"),
    path("dashboard/products/add/", views.ProductCreateView.as_view(), name="product_add"),
    path("dashboard/products/<int:pk>/edit/", views.ProductUpdateView.as_view(), name="product_edit"),
    path("dashboard/products/<int:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),
    path("dashboard/suppliers/", views.SupplierListView.as_view(), name="supplier_list"),
    path("dashboard/suppliers/add/", views.SupplierCreateView.as_view(), name="supplier_add"),
    path("dashboard/customers/", views.CustomerListView.as_view(), name="customer_list"),
    path("dashboard/customers/add/", views.CustomerCreateView.as_view(), name="customer_add"),
    path("dashboard/categories/", views.CategoryListView.as_view(), name="category_list"),
    path("dashboard/categories/add/", views.CategoryCreateView.as_view(), name="category_add"),
    path("dashboard/categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_edit"),
    path("dashboard/categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),
    path("dashboard/units/", views.UnitListView.as_view(), name="unit_list"),
    path("dashboard/units/add/", views.UnitCreateView.as_view(), name="unit_add"),
    path("dashboard/units/<int:pk>/edit/", views.UnitUpdateView.as_view(), name="unit_edit"),
    path("dashboard/units/<int:pk>/delete/", views.UnitDeleteView.as_view(), name="unit_delete"),
]