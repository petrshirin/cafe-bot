from django.urls import path
from .views import get_web_hook

urlpatterns = [
    path('webhook/<str:token>', get_web_hook, name='get_web_hook')
]
