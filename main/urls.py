from django.urls import path
from . import views

urlpatterns = [
	path('', views.calculator_list, name='calculator_list'),
    path('databaseUpload/', views.database_upload, name='database_upload'),
    path('chart-database/', views.chart_database, name='chart_database'),
]
