from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import (
    Category,
    Product,
    ProductImage,
    ProductReview,
    FranchiseApplication,
    Cart,
    CartItem,
    Address,
    Order,
    OrderItem,
    OrderStatusHistory,
)

User = get_user_model()


# ============================================================
# AUTH SERIALIZERS
# ============================================================

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=User.Roles.choices)
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        email = validated_data["email"].lower().strip()
        role = validated_data["role"]
        password = validated_data["password"]

        base_username = email.split("@")[0]
        username = base_username
        i = 1

        while User.objects.filter(username=username).exists():
            i += 1
            username = f"{base_username}{i}"

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
        )
        return user


class LoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs["username_or_email"].strip()
        password = attrs["password"]

        user_obj = None

        if "@" in identifier:
            user_obj = User.objects.filter(email__iexact=identifier).first()

        if user_obj is None:
            user_obj = User.objects.filter(username__iexact=identifier).first()

        if not user_obj:
            raise serializers.ValidationError({"username_or_email": "User not found."})

        user = authenticate(username=user_obj.username, password=password)

        if not user:
            raise serializers.ValidationError({"password": "Invalid password."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "Account disabled."})

        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "role")


# ============================================================
# CATEGORY SERIALIZERS
# ============================================================

class CategoryTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    icon_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "icon_url", "children")

    def get_children(self, obj):
        qs = obj.children.filter(is_active=True).order_by("sort_order", "name")
        return CategoryTreeSerializer(qs, many=True, context=self.context).data

    def get_icon_url(self, obj):
        request = self.context.get("request")

        if obj.icon and request:
            return request.build_absolute_uri(obj.icon.url)

        if obj.icon:
            return obj.icon.url

        return None


# ============================================================
# PRODUCT SERIALIZERS
# ============================================================

class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "image_url", "sort_order")

    def get_image_url(self, obj):
        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(obj.image.url)

        return obj.image.url


class ProductListSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    gst_amount = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "title",
            "slug",
            "sku",
            "brand",
            "short_category_label",
            "category_name",
            "category_slug",
            "mrp",
            "sale_price",
            "gst_percent",
            "gst_amount",
            "discount_percent",
            "is_sale",
            "image",
        )

    def get_image(self, obj):
        first = obj.images.first()

        if not first:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(first.image.url)

        return first.image.url

    def get_gst_amount(self, obj):
        return str(obj.gst_amount)


class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    gst_amount = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "title",
            "slug",
            "sku",
            "brand",
            "short_category_label",
            "category_name",
            "category_slug",
            "mrp",
            "sale_price",
            "gst_percent",
            "gst_amount",
            "discount_percent",
            "is_sale",
            "description",
            "specs",
            "images",
        )

    def get_gst_amount(self, obj):
        return str(obj.gst_amount)


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReview
        fields = ("id", "rating", "name", "email", "comment", "created_at")
        read_only_fields = ("id", "created_at")


# ============================================================
# FRANCHISE SERIALIZER
# ============================================================

class FranchiseApplicationCreateSerializer(serializers.ModelSerializer):
    confirm = serializers.BooleanField(write_only=True)

    class Meta:
        model = FranchiseApplication
        fields = "__all__"
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):

        if not attrs.get("confirm", False):
            raise serializers.ValidationError(
                {"confirm": "You must confirm the information is accurate."}
            )

        if attrs.get("warehouse_facility") == "Yes":
            details = (attrs.get("warehouse_details") or "").strip()

            if len(details) < 3:
                raise serializers.ValidationError(
                    {"warehouse_details": "Please specify warehouse size/details."}
                )

        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm", None)

        request = self.context.get("request")

        if request:
            validated_data["ip_address"] = self._get_ip(request)
            validated_data["user_agent"] = request.META.get("HTTP_USER_AGENT", "")[:1000]

        return super().create(validated_data)

    def _get_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")

        if xff:
            return xff.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR")


# ============================================================
# CART SERIALIZERS
# ============================================================


# ============================================================
# CART SERIALIZERS
# ============================================================

class CartItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source="product.title", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_image = serializers.SerializerMethodField()
    unit_price = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product",
            "product_title",
            "product_slug",
            "product_image",
            "unit_price",
            "quantity",
            "line_total",
        )

    def get_product_image(self, obj):
        first = obj.product.images.first()
        if not first:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(first.image.url)
        return first.image.url

    def get_unit_price(self, obj):
        return str(obj.product.sale_price)

    def get_line_total(self, obj):
        return str(obj.product.sale_price * obj.quantity)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("id", "items", "total_amount")

    def get_total_amount(self, obj):
        total = sum(item.product.sale_price * item.quantity for item in obj.items.all())
        return str(total)


# ============================================================
# ADDRESS SERIALIZERS
# ============================================================

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            "id",
            "full_name",
            "phone",
            "line1",
            "line2",
            "city",
            "state",
            "postal_code",
            "country",
            "is_default",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class AddressCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            "id",
            "full_name",
            "phone",
            "line1",
            "line2",
            "city",
            "state",
            "postal_code",
            "country",
            "is_default",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        if len((attrs.get("postal_code") or "").strip()) < 4:
            raise serializers.ValidationError(
                {"postal_code": "Enter a valid postal code."}
            )

        if len((attrs.get("phone") or "").strip()) < 8:
            raise serializers.ValidationError(
                {"phone": "Enter a valid phone number."}
            )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        is_default = validated_data.get("is_default", False)
        if is_default:
            Address.objects.filter(user=user, is_default=True).update(is_default=False)

        return Address.objects.create(user=user, **validated_data)


# ============================================================
# ORDER SERIALIZERS
# ============================================================

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ("id", "status", "note", "created_at")


class OrderItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source="product.title", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_image = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_title",
            "product_slug",
            "product_image",
            "price",
            "quantity",
            "line_total",
        )

    def get_product_image(self, obj):
        first = obj.product.images.first()
        if not first:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(first.image.url)
        return first.image.url

    def get_line_total(self, obj):
        return str(obj.price * obj.quantity)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "total_amount",
            "created_at",
            "items",
        )


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    history = OrderStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "total_amount",
            "razorpay_order_id",
            "razorpay_payment_id",
            "created_at",
            "shipping_full_name",
            "shipping_phone",
            "shipping_line1",
            "shipping_line2",
            "shipping_city",
            "shipping_state",
            "shipping_postal_code",
            "shipping_country",
            "items",
            "history",
        )

class OrderTrackingSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    history = OrderStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "total_amount",
            "created_at",
            "shipping_full_name",
            "shipping_phone",
            "shipping_line1",
            "shipping_line2",
            "shipping_city",
            "shipping_state",
            "shipping_postal_code",
            "shipping_country",
            "items",
            "history",
        )



from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework import serializers

User = get_user_model()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        validate_password(attrs["password"])

        try:
            uid = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=uid)
        except Exception:
            raise serializers.ValidationError({"uid": "Invalid reset link."})

        token_ok = PasswordResetTokenGenerator().check_token(user, attrs["token"])
        if not token_ok:
            raise serializers.ValidationError({"token": "Reset link is invalid or expired."})

        attrs["user"] = user
        return attrs