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

class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(CartSerializer(cart).data)

class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        if quantity < 1:
            return Response({"detail": "Quantity must be >= 1"}, status=400)

        cart, _ = Cart.objects.get_or_create(user=request.user)

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=404)

        item, created = CartItem.objects.get_or_create(cart=cart, product=product)

        # ✅ FIX: created means default 1, so set exact quantity
        if created:
            item.quantity = quantity
        else:
            item.quantity = item.quantity + quantity

        item.save()
        return Response({"message": "Added to cart"}, status=200)

class UpdateCartItemQtyView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id: int):
        qty = int(request.data.get("quantity", 1))
        if qty < 1:
            return Response({"detail": "Quantity must be >= 1"}, status=400)

        cart, _ = Cart.objects.get_or_create(user=request.user)

        try:
            item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response({"detail": "Cart item not found"}, status=404)

        item.quantity = qty
        item.save()
        return Response({"message": "Quantity updated"}, status=200)

class RemoveCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, item_id: int):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        CartItem.objects.filter(id=item_id, cart=cart).delete()
        return Response({"message": "Removed"}, status=200)

# ----------------------------
# ADDRESS
# ----------------------------

class AddressListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by("-is_default", "-created_at")

    def perform_create(self, serializer):
        # if new address is_default True -> unset others
        is_default = serializer.validated_data.get("is_default", False)
        if is_default:
            Address.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
        serializer.save(user=self.request.user)

class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        is_default = serializer.validated_data.get("is_default", None)
        if is_default is True:
            Address.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
        serializer.save()

# ----------------------------
# PAYMENT (RAZORPAY)
# ----------------------------

class CreateRazorpayOrder(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)

        if cart.items.count() == 0:
            return Response({"detail": "Cart is empty"}, status=400)

        total = sum([item.total_price() for item in cart.items.all()])

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        rp_order = client.order.create({
            "amount": int(total * 100),
            "currency": "INR",
            "payment_capture": 1,
        })

        return Response(rp_order, status=200)

class VerifyPayment(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        razorpay_order_id = request.data.get("razorpay_order_id")
        razorpay_payment_id = request.data.get("razorpay_payment_id")
        razorpay_signature = request.data.get("razorpay_signature")
        address_id = request.data.get("address_id")

        if not address_id:
            return Response({"detail": "address_id is required"}, status=400)

        # ✅ address belongs to user
        try:
            addr = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({"detail": "Invalid address"}, status=400)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        if cart.items.count() == 0:
            return Response({"detail": "Cart is empty"}, status=400)

        total = sum([item.total_price() for item in cart.items.all()])

        # ✅ Optional signature verify (recommended)
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })
        except Exception:
            return Response({"detail": "Signature verification failed"}, status=400)

        # ✅ Create Order + OrderItems
        order = Order.objects.create(
            user=request.user,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            total_amount=total,
            status="paid",

            # snapshot shipping fields
            shipping_full_name=addr.full_name,
            shipping_phone=addr.phone,
            shipping_line1=addr.line1,
            shipping_line2=addr.line2,
            shipping_city=addr.city,
            shipping_state=addr.state,
            shipping_postal_code=addr.postal_code,
            shipping_country=addr.country,
        )

        for item in cart.items.select_related("product").all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.product.sale_price,
                quantity=item.quantity
            )

        # ✅ status history
        OrderStatusHistory.objects.create(order=order, status="paid", note="Payment captured")

        # ✅ Clear cart items
        cart.items.all().delete()

        return Response(
            {"message": "Order created", "order": OrderDetailSerializer(order).data},
            status=200
        )

# ----------------------------
# ORDERS
# ----------------------------

class UserOrdersView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by("-created_at")

class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)