from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # This line connects our new routes to the master project
    path('api/', include('ingestion.urls')), 
]