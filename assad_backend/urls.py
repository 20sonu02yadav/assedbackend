from django.urls import path
from .views import *
urlpatterns = [
    # auth
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("auth/reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("cart/", CartView.as_view()),
    path("cart/add/", AddToCartView.as_view()),
    path("cart/items/<int:item_id>/", UpdateCartItemQtyView.as_view()),
    path("cart/items/<int:item_id>/remove/", RemoveCartItemView.as_view()),
    path("addresses/", AddressListCreateView.as_view(), name="address_list_create"),
    path("addresses/<int:pk>/", AddressDetailView.as_view()),
    #path("addresses/<int:pk>/", AddressRetrieveUpdateDestroyView.as_view(), name="address_rud"),
    path("payment/create-order/", CreateRazorpayOrder.as_view()),
    path("payment/verify/", VerifyPayment.as_view()),

    path("orders/", UserOrdersView.as_view()),
    path("orders/<int:id>/", OrderDetailView.as_view()),
    #path("orders/", MyOrdersView.as_view(), name="my_orders"),
    #path("orders/<int:id>/", OrderDetailTrackingView.as_view(), name="order_detail_tracking"),
    # store 
    path("store/categories/", CategoryTreeView.as_view(), name="store-categories"),
    path("store/products/", ProductListView.as_view(), name="store-products"),
    path("store/products/<slug:slug>/", ProductDetailView.as_view(), name="store-product-detail"),
    path("store/products/<slug:slug>/reviews/", ProductReviewListCreateView.as_view(), name="store-product-reviews"),
    path("franchise-applications/", FranchiseApplicationCreateView.as_view(), name="franchise_application_create"),
]