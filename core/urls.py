from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core import views

# DRF router for ProductViewSet
router = DefaultRouter()
router.register(r'api/products', views.ProductViewSet, basename='api-products')

urlpatterns = [
    # HTML Views
    path('register/', views.register_view, name='register'),
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-page/', views.admin_page, name='admin_page'),
    path('user-page/', views.user_page, name='user_page'),
    path('products/<int:product_id>/reviews/', views.product_reviews, name='product_reviews'),

    # API Views
    path('api/register/', views.api_register_view, name='api_register'),
    path('api/login/', views.api_login_view, name='api_login'),
    path('api/logout/', views.api_logout_view, name='api_logout'),
    path('api/products/<int:product_id>/reviews/', views.api_product_reviews, name='api_product_reviews'),
    path('api/products/<int:product_id>/rating/', views.api_product_rating, name='api_product_rating'),

    # DRF ViewSets (Product CRUD)
    path('', include(router.urls)),
]
