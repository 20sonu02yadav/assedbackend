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



    

    

import razorpay
from django.conf import settings

    
import razorpay
from django.conf import settings
from .models import Address




# views.py (add)
from rest_framework import generics, permissions
from .models import Address
from .serializers import AddressSerializer, AddressCreateSerializer



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



# views.py (add)

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Order
from .serializers import OrderTrackingSerializer

class MyOrdersView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderTrackingSerializer

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related("items", "history", "items__product")
            .order_by("-created_at")
        )

class OrderDetailTrackingView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderTrackingSerializer
    lookup_field = "id"

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related("items", "history", "items__product")
        )
    



# views.py
from django.conf import settings
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

import razorpay

from .models import Cart, CartItem, Product, Order, OrderItem, Address, OrderStatusHistory
from .serializers import (
    CartSerializer,
    AddressSerializer,
    OrderSerializer,
    OrderDetailSerializer,
)

# ----------------------------
# CART
# ----------------------------
from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
import razorpay
from django.conf import settings

from .models import (
    Category,
    Product,
    ProductReview,
    FranchiseApplication,
    Cart,
    CartItem,
    Address,
    Order,
    OrderItem,
    OrderStatusHistory,
)
from .serializers import (
    CategoryTreeSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ReviewSerializer,
    FranchiseApplicationCreateSerializer,
    CartSerializer,
    AddressSerializer,
    AddressCreateSerializer,
    OrderSerializer,
    OrderDetailSerializer,
)

# ------------------------------------------------
# CART
# ------------------------------------------------

class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart, context={"request": request})
        return Response(serializer.data)


class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        if quantity < 1:
            return Response({"detail": "Quantity must be at least 1."}, status=400)

        cart, _ = Cart.objects.get_or_create(user=request.user)

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=404)

        item, created = CartItem.objects.get_or_create(cart=cart, product=product)

        # ✅ Important fix
        if created:
            item.quantity = quantity
        else:
            item.quantity = quantity  # exact qty set
            # If you want add-on behavior then use: item.quantity += quantity

        item.save()

        return Response({"message": "Added to cart successfully."}, status=200)


class UpdateCartItemQtyView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):
        quantity = int(request.data.get("quantity", 1))

        if quantity < 1:
            return Response({"detail": "Quantity must be at least 1."}, status=400)

        cart, _ = Cart.objects.get_or_create(user=request.user)

        try:
            item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response({"detail": "Cart item not found."}, status=404)

        item.quantity = quantity
        item.save()

        return Response({"message": "Quantity updated successfully."}, status=200)


class RemoveCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, item_id):
        cart, _ = Cart.objects.get_or_create(user=request.user)

        try:
            item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response({"detail": "Cart item not found."}, status=404)

        item.delete()
        return Response({"message": "Item removed successfully."}, status=200)


# ------------------------------------------------
# ADDRESS
# ------------------------------------------------

class AddressListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by("-is_default", "-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AddressCreateSerializer
        return AddressSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        obj = serializer.save()

        if obj.is_default:
            Address.objects.filter(user=self.request.user).exclude(id=obj.id).update(is_default=False)


# ------------------------------------------------
# PAYMENT
# ------------------------------------------------

class CreateRazorpayOrder(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)

        if not cart.items.exists():
            return Response({"detail": "Cart is empty."}, status=400)

        total = sum(item.product.sale_price * item.quantity for item in cart.items.all())

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        payment = client.order.create({
            "amount": int(total * 100),
            "currency": "INR",
            "payment_capture": 1,
        })

        return Response(payment)


class VerifyPayment(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        razorpay_order_id = request.data.get("razorpay_order_id")
        razorpay_payment_id = request.data.get("razorpay_payment_id")
        razorpay_signature = request.data.get("razorpay_signature")
        address_id = request.data.get("address_id")

        if not address_id:
            return Response({"detail": "Address is required."}, status=400)

        cart, _ = Cart.objects.get_or_create(user=request.user)

        if not cart.items.exists():
            return Response({"detail": "Cart is empty."}, status=400)

        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({"detail": "Selected address not found."}, status=404)

        total = sum(item.product.sale_price * item.quantity for item in cart.items.all())

        # Optional: Razorpay signature verification
        try:
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })
        except Exception:
            return Response({"detail": "Payment signature verification failed."}, status=400)

        order = Order.objects.create(
            user=request.user,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            total_amount=total,
            status="paid",

            # ✅ shipping snapshot
            shipping_full_name=address.full_name,
            shipping_phone=address.phone,
            shipping_line1=address.line1,
            shipping_line2=address.line2,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_postal_code=address.postal_code,
            shipping_country=address.country,
        )

        for item in cart.items.select_related("product").all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.product.sale_price,
                quantity=item.quantity,
            )

        OrderStatusHistory.objects.create(
            order=order,
            status="paid",
            note="Payment successful and order created",
        )

        # ✅ clear cart
        cart.items.all().delete()

        serializer = OrderDetailSerializer(order, context={"request": request})
        return Response(
            {
                "message": "Order created successfully.",
                "order": serializer.data,
            },
            status=200
        )


# ------------------------------------------------
# ORDERS
# ------------------------------------------------

class UserOrdersView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .prefetch_related("items__product__images", "history")
            .order_by("-created_at")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .prefetch_related("items__product__images", "history")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx
    


from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.permissions import AllowAny
from .serializers import ForgotPasswordSerializer, ResetPasswordSerializer

User = get_user_model()


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()

        # security: always return success message even if email not found
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = PasswordResetTokenGenerator().make_token(user)

            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"

            subject = "Reset your password"
            message = (
                f"Hello {user.username},\n\n"
                f"You requested a password reset.\n\n"
                f"Click the link below to reset your password:\n\n"
                f"{reset_url}\n\n"
                f"If you did not request this, you can ignore this email."
            )

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        return Response(
            {"message": "If this email exists, a password reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        password = serializer.validated_data["password"]

        user.set_password(password)
        user.save()

        return Response(
            {"message": "Password reset successful. Please login again."},
            status=status.HTTP_200_OK,
        )