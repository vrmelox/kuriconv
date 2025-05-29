from django.urls import path
from . import views

app_name = 'currencies'

urlpatterns = [
    path('', views.convert_currency, name='convert_currency'),
]
