from django.urls import path
from .views import (
    RegisterView, LoginView, MeView,
    CategoryTreeView, ProductListView, ProductDetailView, ProductReviewListCreateView,FranchiseApplicationCreateView
)

urlpatterns = [
    # auth
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),

    # store
    path("store/categories/", CategoryTreeView.as_view(), name="store-categories"),
    path("store/products/", ProductListView.as_view(), name="store-products"),
    path("store/products/<slug:slug>/", ProductDetailView.as_view(), name="store-product-detail"),
    path("store/products/<slug:slug>/reviews/", ProductReviewListCreateView.as_view(), name="store-product-reviews"),
    path("franchise-applications/", FranchiseApplicationCreateView.as_view(), name="franchise_application_create"),
]