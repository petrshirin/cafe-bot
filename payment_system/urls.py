
from django.urls import path
from .views import *

urlpatterns = [

    path('payment/Tinkoff/', get_payment_tinkoff, name='tinkoff'),
]
