from django.urls import path
from . import views

urlpatterns = [
    path('bookings/', views.bookingsviewset.as_view({'post': 'create'}), name='bookings'),
    path('lsas/search/', views.get_lsa, name='lsa-search'),
    path('payments/', views.paymentgateway, name='payment-gateway'),
]