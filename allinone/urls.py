from django.urls import path
from . import views

urlpatterns = [
    # Booking Endpoints
    path('bookings/', views.BookingViewSet.as_view({'post': 'create', 'get': 'list'}), name='bookings'),
    path('v1/bookings/', views.BookingViewSet.as_view({'post': 'create', 'get': 'list'}), name='v1-bookings'),

    # LSA Search Endpoints
    path('lsas/search/', views.get_lsa, name='lsa-search'),
    path('v1/lsas/search/', views.get_lsa, name='v1-lsa-search'),

    # Payment Integration Endpoints
    path('payments/initiate/', views.initiate_payment, name='payment-initiate'),
    path('v1/payments/initiate/', views.initiate_payment, name='v1-payment-initiate'),

    path('payments/webhook/', views.payment_webhook, name='payment-webhook'),
    path('v1/payments/webhook/', views.payment_webhook, name='v1-payment-webhook'),
]