from django.urls import path
from .views import get_web_hook
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('webhook/<str:token>', csrf_exempt(get_web_hook), name='get_web_hook')
]
