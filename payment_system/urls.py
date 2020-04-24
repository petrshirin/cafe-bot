
from django.urls import path
from .views import *
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [

    path('Tinkoff/', csrf_exempt(get_payment_tinkoff), name='tinkoff'),
]
