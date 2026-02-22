"""
Core URLs configuration for OptiMystic (Django).
"""
from django.urls import path

from core import views

urlpatterns = [
    path('health/', views.health_view, name='health'),
    path('optimize/', views.optimize_view, name='optimize'),
]
