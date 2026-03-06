from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import *


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

        # ✅ auto username from email prefix (unique)
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

        # ✅ try email first
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


from rest_framework import serializers
from .models import Category, Product, ProductImage, ProductReview

class CategoryTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    icon_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "icon_url", "children")

    def get_children(self, obj):
        qs = obj.children.filter(is_active=True).order_by("sort_order", "name")
        return CategoryTreeSerializer(qs, many=True).data

    def get_icon_url(self, obj):
        request = self.context.get("request")
        if obj.icon and request:
            return request.build_absolute_uri(obj.icon.url)
        if obj.icon:
            return obj.icon.url
        return None


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
        # decimal safe
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



from rest_framework import serializers
from .models import FranchiseApplication


class FranchiseApplicationCreateSerializer(serializers.ModelSerializer):
    confirm = serializers.BooleanField(write_only=True)

    class Meta:
        model = FranchiseApplication
        fields = [
            "id",
            "registered_business_name",
            "trading_name",
            "type_of_business",
            "gstin",
            "city",
            "state",
            "postal_code",
            "primary_contact_person",
            "designation",
            "email",
            "alternate_contact_person",
            "years_in_operation",
            "nature_of_business",
            "main_product_categories",
            "geographical_coverage",
            "number_of_employees",
            "annual_turnover",
            "warehouse_facility",
            "warehouse_details",
            "existing_dealerships",
            "confirm",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        # checkbox confirm required
        if not attrs.get("confirm", False):
            raise serializers.ValidationError({"confirm": "You must confirm the information is accurate."})

        # if warehouse yes then details should be present (optional rule but helpful)
        if attrs.get("warehouse_facility") == "Yes":
            details = (attrs.get("warehouse_details") or "").strip()
            if len(details) < 3:
                raise serializers.ValidationError({"warehouse_details": "Please specify warehouse size/details."})

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
    


class CartItemSerializer(serializers.ModelSerializer):

    product_title = serializers.CharField(source="product.title", read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "product_title", "quantity"]



from rest_framework import serializers
from .models import Order, OrderItem, OrderStatusHistory

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ("id", "status", "note", "created_at")


class CartSerializer(serializers.ModelSerializer):

    items = CartItemSerializer(many=True)

    class Meta:
        model = Cart
        fields = ["id", "items"]

class OrderItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source="product.title", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "product_title", "product_slug", "price", "quantity")


class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "razorpay_order_id",
            "status",
            "total_amount",
            "items",
            "created_at",
        ]


class OrderTrackingSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    history = OrderStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "total_amount",
            "courier_name",
            "tracking_number",
            "tracking_url",
            "created_at",
            "items",
            "history",
        )

# serializers.py (add)
from .models import Address

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
        # Basic validation
        if len((attrs.get("postal_code") or "").strip()) < 4:
            raise serializers.ValidationError({"postal_code": "Enter a valid postal code."})
        if len((attrs.get("phone") or "").strip()) < 8:
            raise serializers.ValidationError({"phone": "Enter a valid phone number."})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        is_default = validated_data.get("is_default", False)

        # If setting default, unset old defaults
        if is_default:
            Address.objects.filter(user=user, is_default=True).update(is_default=False)

        return Address.objects.create(user=user, **validated_data)