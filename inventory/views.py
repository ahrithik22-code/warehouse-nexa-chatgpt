from rest_framework import permissions, response, status, viewsets
from rest_framework.decorators import action

from .models import Batch, Movement, MovementService, Product
from .serializers import BatchSerializer, MovementSerializer, ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]


class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.select_related('sku', 'warehouse')
    serializer_class = BatchSerializer
    permission_classes = [permissions.IsAuthenticated]


class MovementViewSet(viewsets.ModelViewSet):
    queryset = Movement.objects.prefetch_related('lines')
    serializer_class = MovementSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def commit(self, request, pk=None):
        movement = self.get_object()
        try:
            MovementService.commit(movement)
        except Exception as exc:  # broad for API surface
            return response.Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(movement)
        return response.Response(serializer.data, status=status.HTTP_200_OK)
