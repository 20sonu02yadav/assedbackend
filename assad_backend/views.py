from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, LoginSerializer, UserSerializer


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response(
            {
                "message": "Registered successfully",
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)
        return Response(
            {
                "message": "Login successful",
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": UserSerializer(request.user).data})
    


from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.db.models import Q

from .models import Category, Product, ProductReview
from .serializers import (
    CategoryTreeSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ReviewSerializer,
)

class CategoryTreeView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategoryTreeSerializer

    def get_queryset(self):
        return Category.objects.filter(is_active=True, parent__isnull=True).order_by("sort_order", "name")


class ProductListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    search_fields = ["title", "sku", "brand", "short_category_label"]
    ordering_fields = ["sale_price", "mrp", "created_at", "title"]

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related("category").prefetch_related("images")

        category_slug = self.request.query_params.get("category")
        if category_slug:
            qs = qs.filter(category__slug=category_slug)

        # allow subcategory tree filter: include children
        parent_slug = self.request.query_params.get("parent")
        if parent_slug:
            parent = Category.objects.filter(slug=parent_slug).first()
            if parent:
                child_ids = list(parent.children.filter(is_active=True).values_list("id", flat=True))
                qs = qs.filter(category_id__in=child_ids)

        # pricing sort shortcut
        pricing = self.request.query_params.get("pricing")
        if pricing == "low":
            qs = qs.order_by("sale_price")
        elif pricing == "high":
            qs = qs.order_by("-sale_price")

        return qs


class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related("category").prefetch_related("images")


class ProductReviewListCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        slug = self.kwargs["slug"]
        product = Product.objects.filter(slug=slug, is_active=True).first()
        if not product:
            return ProductReview.objects.none()
        return ProductReview.objects.filter(product=product)

    def perform_create(self, serializer):
        slug = self.kwargs["slug"]
        product = Product.objects.get(slug=slug, is_active=True)
        serializer.save(product=product)