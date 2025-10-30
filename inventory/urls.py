from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BatchViewSet, MovementViewSet, ProductViewSet

app_name = 'inventory'

router = DefaultRouter()
router.register('products', ProductViewSet)
router.register('batches', BatchViewSet)
router.register('movements', MovementViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
