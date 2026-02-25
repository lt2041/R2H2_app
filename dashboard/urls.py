# URLs app file for prisma_cloud app
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='r2h2-home'),
]
