from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    User,
    Category,
    Product,
    ProductImage,
    ProductReview,
    FranchiseApplication,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Address
)

# =========================================================
# USER ADMIN
# =========================================================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Extra", {"fields": ("role",)}),
    )

    list_display = ("username", "email", "role", "is_staff", "is_active")
    search_fields = ("username", "email")


# =========================================================
# CATEGORY ADMIN
# =========================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


# =========================================================
# PRODUCT ADMIN
# =========================================================

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "sku",
        "sale_price",
        "mrp",
        "gst_percent",
        "is_active",
    )

    list_filter = ("is_active", "category")

    search_fields = ("title", "sku", "slug")

    inlines = [ProductImageInline]


# =========================================================
# PRODUCT REVIEW ADMIN
# =========================================================

@admin.register(ProductReview)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "rating", "name", "email", "created_at")
    list_filter = ("rating",)
    search_fields = ("product__title", "name", "email")


# =========================================================
# FRANCHISE APPLICATION ADMIN
# =========================================================

@admin.register(FranchiseApplication)
class FranchiseApplicationAdmin(admin.ModelAdmin):

    list_display = (
        "registered_business_name",
        "city",
        "state",
        "primary_contact_person",
        "email",
        "type_of_business",
        "nature_of_business",
        "years_in_operation",
        "warehouse_facility",
        "created_at",
    )

    list_filter = (
        "state",
        "type_of_business",
        "nature_of_business",
        "warehouse_facility",
        "created_at",
    )

    search_fields = (
        "registered_business_name",
        "city",
        "primary_contact_person",
        "email",
        "gstin",
    )

    readonly_fields = ("created_at", "ip_address", "user_agent")


# =========================================================
# CART ADMIN
# =========================================================

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):

    list_display = ("id", "user", "created_at")

    search_fields = ("user__username", "user__email")

    inlines = [CartItemInline]


# =========================================================
# ORDER ADMIN
# =========================================================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "razorpay_order_id",
        "razorpay_payment_id",
        "total_amount",
        "status",
        "created_at",
    )

    list_filter = ("status", "created_at")

    search_fields = (
        "user__username",
        "razorpay_order_id",
        "shipping_full_name",
        "shipping_phone",
    )

    inlines = [OrderItemInline]

    fieldsets = (
        ("Order Info", {
            "fields": (
                "user",
                "status",
                "total_amount",
                "razorpay_order_id",
                "razorpay_payment_id",
            )
        }),

        ("Shipping Address", {
            "fields": (
                "shipping_full_name",
                "shipping_phone",
                "shipping_line1",
                "shipping_line2",
                "shipping_city",
                "shipping_state",
                "shipping_postal_code",
                "shipping_country",
            )
        }),

        ("Timestamp", {
            "fields": ("created_at",)
        }),
    )


# =========================================================
# ADDRESS ADMIN
# =========================================================

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "full_name",
        "phone",
        "city",
        "postal_code",
        "is_default",
        "created_at",
    )

    list_filter = (
        "city",
        "state",
        "is_default",
    )

    search_fields = (
        "full_name",
        "phone",
        "city",
        "postal_code",
    )