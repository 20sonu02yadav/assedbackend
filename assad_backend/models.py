from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Roles(models.TextChoices):
        INDIVIDUAL_CUSTOMER = "Individual Customer", "Individual Customer"
        B2B = "B2B", "B2B"

    email = models.EmailField(_("email address"), unique=True)
    role = models.CharField(max_length=40, choices=Roles.choices, default=Roles.INDIVIDUAL_CUSTOMER)

    def __str__(self):
        return f"{self.username} ({self.email}) - {self.role}"
    


from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator

# -----------------------------
# STORE MODELS
# -----------------------------

class Category(models.Model):
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children", on_delete=models.CASCADE
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    icon = models.ImageField(upload_to="category_icons/", blank=True, null=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            i = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, related_name="products", on_delete=models.PROTECT)

    title = models.CharField(max_length=260)
    slug = models.SlugField(max_length=300, unique=True, blank=True)

    sku = models.CharField(max_length=120, blank=True, default="")
    brand = models.CharField(max_length=120, blank=True, default="")

    # Pricing
    mrp = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    gst_percent = models.PositiveIntegerField(default=18, validators=[MinValueValidator(0), MaxValueValidator(28)])
    discount_percent = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(90)])

    # Content
    short_category_label = models.CharField(max_length=80, blank=True, default="")  # e.g. "AIR COMPRESSOR"
    description = models.TextField(blank=True, default="")
    specs = models.JSONField(blank=True, null=True)  # specs list store (Voltage, Tank, Noise...)

    # Flags
    is_active = models.BooleanField(default=True)
    is_sale = models.BooleanField(default=True)  # show "SALE" pill
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            i = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def gst_amount(self):
        # GST on sale_price (change if you want GST on MRP)
        return (self.sale_price * self.gst_percent) / 100

    def __str__(self):
        return self.title


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.product.title} image"


class ProductReview(models.Model):
    product = models.ForeignKey(Product, related_name="reviews", on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    name = models.CharField(max_length=120)
    email = models.EmailField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.title} - {self.rating}"







from django.db import models


class FranchiseApplication(models.Model):
    TYPE_OF_BUSINESS_CHOICES = [
        ("Proprietorship", "Proprietorship"),
        ("Partnership", "Partnership"),
        ("Pvt Ltd", "Pvt Ltd"),
        ("Ltd Co", "Ltd Co"),
        ("Other", "Other"),
    ]

    NATURE_OF_BUSINESS_CHOICES = [
        ("Retail", "Retail"),
        ("Wholesale", "Wholesale"),
        ("Distribution", "Distribution"),
        ("Online", "Online"),
        ("Other", "Other"),
    ]

    YES_NO_CHOICES = [("Yes", "Yes"), ("No", "No")]

    # Form fields
    registered_business_name = models.CharField(max_length=255)
    trading_name = models.CharField(max_length=255, blank=True)

    type_of_business = models.CharField(max_length=50, choices=TYPE_OF_BUSINESS_CHOICES)
    gstin = models.CharField(max_length=30, blank=True)

    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)

    primary_contact_person = models.CharField(max_length=150)
    designation = models.CharField(max_length=150)
    email = models.EmailField()

    alternate_contact_person = models.CharField(max_length=150, blank=True)

    years_in_operation = models.CharField(max_length=50)  # "Less than 1", "1-2", ...
    nature_of_business = models.CharField(max_length=50, choices=NATURE_OF_BUSINESS_CHOICES)

    main_product_categories = models.TextField()
    geographical_coverage = models.CharField(max_length=255)

    number_of_employees = models.CharField(max_length=50, blank=True)
    annual_turnover = models.CharField(max_length=80, blank=True)

    warehouse_facility = models.CharField(max_length=10, choices=YES_NO_CHOICES, default="No")
    warehouse_details = models.TextField(blank=True)

    existing_dealerships = models.TextField(blank=True)

    # system
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    def __str__(self):
        return f"{self.registered_business_name} - {self.city} ({self.created_at.date()})"