from django.urls import path

from . import views

app_name = 'planner'

urlpatterns = [
    path('reorder/', views.ReorderView.as_view(), name='reorder'),
    path('fba/', views.FBAView.as_view(), name='fba'),
    path('excess/', views.ExcessView.as_view(), name='excess'),
    path('flags/', views.FlagsView.as_view(), name='flags'),
]
