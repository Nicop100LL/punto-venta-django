from django.urls import path
from .views import test_ticket

urlpatterns = [
    path("test-ticket/", test_ticket, name="test_ticket"),
]
