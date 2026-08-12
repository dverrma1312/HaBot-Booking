from django.contrib import admin
from django.urls import path, include
from allinone.views import dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard_view, name='dashboard'),
    path('api/', include('allinone.urls')),
]