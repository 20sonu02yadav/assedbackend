from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Extra", {"fields": ("role",)}),
    )
    list_display = ("username", "email", "role", "is_staff", "is_active")
    search_fields = ("username", "email")



from django.contrib import admin
from .models import User, Category, Product, ProductImage, ProductReview

# User admin tumhara already hai (rehne do)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "sku", "sale_price", "mrp", "gst_percent", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("title", "sku", "slug")
    inlines = [ProductImageInline]

class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "rating", "name", "email", "created_at")
    list_filter = ("rating",)
    search_fields = ("product__title", "name", "email")

admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductReview, ReviewAdmin)