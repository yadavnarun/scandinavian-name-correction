# api/urls.py
from django.urls import path
from .views import NameCorrectionView

app_name = 'api'

urlpatterns = [
    path('correct/', NameCorrectionView.as_view(), name='correct-name'),
]