# Agrovet Management System

A comprehensive web-based management system designed for agricultural veterinary shops (Agrovets). This application features a dual-interface system: a public-facing E-commerce Store for customers and a secure Administration Dashboard for staff to manage inventory, sales, and reports.

## 🚀 Features

### 🛒 Customer Storefront
* **Product Catalog:** Browse products with categories, search functionality, and detailed views.
* **Shopping Cart:** Add items to a session-based cart.
* **User Accounts:** Customer registration and login.
* **Order Tracking:** "My Orders" section for customers to view order history and status.
* **Responsive Design:** optimized for mobile and desktop using a custom "Agrovet Green" theme.

### 💼 Admin Dashboard
* **Inventory Management:** CRUD operations for Products, Categories, Units, and Suppliers.
* **Point of Sale (POS):** Dedicated interface for recording walk-in sales with automatic stock deduction.
* **Stock Control:** Real-time low stock alerts and detailed stock transaction logs (IN/OUT).
* **Order Management:** Process and approve online orders from customers.
* **Reporting:** Generate printable system reports with financial summaries and inventory health checks.
* **Procurement:** Record purchases from suppliers to restock inventory.

## 🛠️ Tech Stack

* **Backend:** Django 4.2 (Python 3.11)
* **Database:** PostgreSQL 15
* **Frontend:** Django Templates, Bootstrap 5, Select2, jQuery
* **Containerization:** Docker & Docker Compose
* **Proxy/Server:** Traefik (Reverse Proxy), Gunicorn

## 📋 Prerequisites

Ensure you have the following installed on your machine:
* [Docker](https://www.docker.com/get-started)
* [Docker Compose](https://docs.docker.com/compose/install/)
* [Git](https://git-scm.com/)

## ⚙️ Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/Muigai-Kiongo/Agrovet.git](https://github.com/Muigai-Kiongo/Agrovet.git)
    cd Agrovet
    ```

2.  **Environment Configuration**
    Copy the example environment file and configure your credentials.
    ```bash
    cp Agrovet/.env.example Agrovet/.env
    ```
    *Open `Agrovet/.env` and ensure `DJANGO_SECRET_KEY` and database credentials are set.*

3.  **Build and Run with Docker**
    ```bash
    cd Agrovet
    docker-compose up -d --build
    ```

4.  **Apply Database Migrations**
    Initialize the database schema.
    ```bash
    docker-compose exec web python manage.py migrate
    ```

5.  **Create an Admin User**
    Create a superuser account to access the dashboard.
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

## 🖥️ Usage

### Accessing the Application
* **Storefront (Public):** [http://agrovet.local:8080/](http://agrovet.local:8080/)
* **Admin Dashboard:** [http://agrovet.local:8080/dashboard/](http://agrovet.local:8080/dashboard/) (Requires Login)
* **Django Admin:** [http://agrovet.local:8080/admin/](http://agrovet.local:8080/admin/)

### Default Accounts
* **Admin:** Use the credentials you created in Step 5.
* **Customer:** You can sign up for a new account via the "Sign Up" button on the storefront.

## 📂 Project Structure

Agrovet/
├── .dockerignore
├── .env
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── entrypoint.sh
├── manage.py
├── requirements.txt
│
├── agrovet_project/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── inventory/
│   ├── admin.py
│   ├── apps.py
│   ├── context_processors.py
│   ├── forms.py
│   ├── models.py
│   ├── serializers.py
│   ├── urls.py
│   ├── views.py
│   │
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_product_image_sale_channel_sale_status_and_more.py
│   │   └── 0003_customer_user.py
│   │
│   ├── static/
│   │   └── inventory/
│   │       └── css/
│   │           └── custom.css
│   │
│   └── templates/
│       ├── base.html
│       ├── home.html
│       ├── customers/
│       │   ├── customer_form.html
│       │   └── customer_list.html
│       ├── dashboard/
│       │   ├── home.html
│       │   └── order_list.html
│       ├── products/
│       │   ├── product_confirm_delete.html
│       │   ├── product_detail.html
│       │   ├── product_form.html
│       │   └── product_list.html
│       ├── purchases/
│       │   └── purchase_form.html
│       ├── registration/
│       │   ├── login.html
│       │   └── signup.html
│       ├── sales/
│       │   └── sale_form.html
│       ├── store/
│       │   ├── cart.html
│       │   ├── checkout.html
│       │   ├── my_orders.html
│       │   ├── product_detail.html
│       │   └── store_home.html
│       └── suppliers/
│           ├── supplier_form.html
│           └── supplier_list.html
│
├── traefik/
│   ├── acme.json
│   └── traefik.yml
│
└── staticfiles/ (Generated/Collected Static Files)
    ├── admin/
    ├── inventory/
    └── rest_framework/


## 🔧 Configuration

### Environment Variables (`.env`)
| Variable | Description | Default (Dev) |
| :--- | :--- | :--- |
| `DJANGO_DEBUG` | Enable debug mode | `True` |
| `DJANGO_SECRET_KEY` | Secret key for crypto signing | `change-me` |
| `POSTGRES_DB` | Database name | `agrovet` |
| `POSTGRES_USER` | Database user | `agrovet` |
| `POSTGRES_PASSWORD` | Database password | `agrovet` |
| `POSTGRES_HOST` | Database host service | `db` |

### Static & Media Files
* **Static Files:** Served via Whitenoise in production (or Django in dev).
* **Media Files:** Mapped to the `./media` directory on your host machine for persistence.

## 🤝 Contributing

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.