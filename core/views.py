from rest_framework import response, status, views


class HealthView(views.APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        return response.Response({'status': 'ok'}, status=status.HTTP_200_OK)
