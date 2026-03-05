from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import *


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
    


from rest_framework import generics, permissions
from .models import FranchiseApplication
from .serializers import FranchiseApplicationCreateSerializer


class FranchiseApplicationCreateView(generics.CreateAPIView):
    queryset = FranchiseApplication.objects.all()
    serializer_class = FranchiseApplicationCreateSerializer
    permission_classes = [permissions.AllowAny]




from rest_framework.permissions import IsAuthenticated
from .models import Cart, CartItem, Product
class CartView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        cart, created = Cart.objects.get_or_create(user=request.user)

        serializer = CartSerializer(cart)

        return Response(serializer.data)
    

class AddToCartView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        product_id = request.data.get("product_id")

        quantity = int(request.data.get("quantity", 1))

        cart, created = Cart.objects.get_or_create(user=request.user)

        product = Product.objects.get(id=product_id)

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product
        )

        item.quantity = quantity
        item.save()

        return Response({"message": "Added to cart"})
    

import razorpay
from django.conf import settings


class CreateRazorpayOrder(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        cart = Cart.objects.get(user=request.user)

        total = sum(item.total_price() for item in cart.items.all())

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        payment = client.order.create({
            "amount": int(total * 100),
            "currency": "INR",
            "payment_capture": 1
        })

        return Response(payment)
    
import razorpay
from django.conf import settings
from .models import Address

class VerifyPayment(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        data = {
            "razorpay_order_id": request.data.get("razorpay_order_id"),
            "razorpay_payment_id": request.data.get("razorpay_payment_id"),
            "razorpay_signature": request.data.get("razorpay_signature"),
            "address_id" : request.data.get("address_id")  # ✅ NEW
        }

        client.utility.verify_payment_signature(data)

        cart = Cart.objects.get(user=request.user)

        total = sum(item.total_price() for item in cart.items.all())

        order = Order.objects.create(
            user=request.user,
            razorpay_order_id=data["razorpay_order_id"],
            razorpay_payment_id=data["razorpay_payment_id"],
            total_amount=total,
            status="paid"
        )   
        shipping_full_name=addr.full_name if addr else "",
        shipping_phone=addr.phone if addr else "",
        shipping_line1=addr.line1 if addr else "",
        shipping_line2=addr.line2 if addr else "",
        shipping_city=addr.city if addr else "",
        shipping_state=addr.state if addr else "",
        shipping_postal_code=addr.postal_code if addr else "",
        shipping_country=addr.country if addr else "India",

        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.product.sale_price,
                quantity=item.quantity
            )

        cart.items.all().delete()

        return Response({"message":"Payment verified"})

class UserOrdersView(generics.ListAPIView):

    permission_classes = [IsAuthenticated]

    serializer_class = OrderSerializer

    def get_queryset(self):

        return Order.objects.filter(user=self.request.user).order_by("-created_at")



# views.py (add)
from rest_framework import generics, permissions
from .models import Address
from .serializers import AddressSerializer, AddressCreateSerializer

class AddressListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AddressCreateSerializer
        return AddressSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class AddressRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        obj = serializer.save()
        # if set default -> unset others
        if obj.is_default:
            Address.objects.filter(user=self.request.user).exclude(id=obj.id).update(is_default=False)