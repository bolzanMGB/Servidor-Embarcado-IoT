from django.contrib import admin
from django.urls import path, include
import audioApp.urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(audioApp.urls)),
]
