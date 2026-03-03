from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User


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