from django.urls import path

from .views import ManualOrdersImportView, ReceivingImportView, SellerboardImportView

app_name = 'imports'

urlpatterns = [
    path('receiving/', ReceivingImportView.as_view(), name='receiving'),
    path('sellerboard/', SellerboardImportView.as_view(), name='sellerboard'),
    path('manual-orders/', ManualOrdersImportView.as_view(), name='manual-orders'),
]
