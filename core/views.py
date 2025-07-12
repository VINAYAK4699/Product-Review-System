from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.contrib.auth.forms import AuthenticationForm
from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import RegisterForm, ProductForm, ReviewForm
from .models import UserProfile, Product, Review
from .serializers import ProductSerializer, ReviewSerializer, UserSerializer
from django.db.models import Avg
from django.contrib.auth.models import User

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            # Set user type
            profile = user.userprofile
            profile.user_type = form.cleaned_data['user_type']
            profile.save()

            messages.success(request, "Registration successful. Please login.")
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegisterForm()
    return render(request, 'core/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Determine user type
            user_type = user.userprofile.user_type

            # Redirect based on user type
            if user_type == 'admin':
                return redirect('admin_page')
            else:
                return redirect('user_page')

        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'core/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

# Admin dashboard with all product management
@login_required
def admin_page(request):
    if request.user.userprofile.user_type != 'admin':
        return HttpResponseForbidden("You are not authorized to access this page.")

    products = Product.objects.all()
    form = ProductForm()

    if request.method == 'POST':
        if 'create' in request.POST:
            form = ProductForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Product added successfully.")
                return redirect('admin_page')
            else:
                messages.error(request, "Please correct the errors below.")

        elif 'update' in request.POST:
            product_id = request.POST.get('product_id')
            product = get_object_or_404(Product, id=product_id)
            form = ProductForm(request.POST, instance=product)
            if form.is_valid():
                form.save()
                messages.success(request, "Product updated.")
                return redirect('admin_page')
            else:
                messages.error(request, f"Error updating product {product.name}.")

        elif 'delete' in request.POST:
            product_id = request.POST.get('product_id')
            product = get_object_or_404(Product, id=product_id)
            product.delete()
            messages.success(request, "Product deleted.")
            return redirect('admin_page')

    return render(request, 'accounts/admin_page.html', {'products': products,'form': form})

# User-only view
@login_required
def user_page(request):
    if request.user.userprofile.user_type != 'user':
        return HttpResponseForbidden("You are not authorized to access this page.")

    # Get all products with average ratings
    products = Product.objects.annotate(avg_rating=Avg('reviews__rating'))

    return render(request, 'core/user_page.html', {'products': products})


@login_required
def product_reviews(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.select_related('user').all()
    existing_review = Review.objects.filter(product=product, user=request.user).first()

    if existing_review:
        form = None  # Prevent duplicate review
    else:
        form = ReviewForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.save()
            messages.success(request, "Review submitted successfully.")
            return redirect('product_reviews', product_id=product.id)

    return render(request, 'core/product_reviews.html', {
        'product': product,
        'reviews': reviews,
        'form': form,
        'existing_review': existing_review
    })

# ------------------- REST API Views -------------------

@api_view(['POST'])
def api_register_view(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "User registered."}, status=201)
    return Response(serializer.errors, status=400)

@api_view(['POST'])
def api_login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(username=username, password=password)
    if user:
        login(request, user)
        return Response({"message": "Login successful"})
    return Response({"error": "Invalid credentials"}, status=400)

@api_view(['POST'])
def api_logout_view(request):
    logout(request)
    return Response({"message": "Logged out"})

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().annotate(avg_rating=Avg('reviews__rating'))
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def api_product_reviews(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'GET':
        reviews = product.reviews.select_related('user')
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)
    else:
        if Review.objects.filter(product=product, user=request.user).exists():
            return Response({"error": "You have already reviewed this product."}, status=400)
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, product=product)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

@api_view(['GET'])
def api_product_rating(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    avg = product.reviews.aggregate(avg=Avg('rating'))['avg']
    return Response({"product_id": product.id, "avg_rating": round(avg or 0, 2)})

