from rest_framework import permissions, response, status, views

from .services import (
    ManualOrdersImportService,
    ReceivingImportService,
    SellerboardImportService,
)


class ReceivingImportView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        content = request.data.get('file') or request.body.decode()
        service = ReceivingImportService()
        records = service.parse(content)
        service.apply(records)
        return response.Response({'imported': len(records)}, status=status.HTTP_201_CREATED)


class SellerboardImportView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        content = request.data.get('file') or request.body.decode()
        service = SellerboardImportService()
        metrics = service.parse(content)
        return response.Response({'updated': len(metrics)}, status=status.HTTP_200_OK)


class ManualOrdersImportView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        content = request.data.get('file') or request.body.decode()
        service = ManualOrdersImportService()
        service.parse(content)
        return response.Response({'status': 'ok'}, status=status.HTTP_200_OK)
