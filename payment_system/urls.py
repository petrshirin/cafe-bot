
from django.urls import path
from .views import *

urlpatterns = [

    path('Tinkoff/', get_payment_tinkoff, name='tinkoff'),
]
