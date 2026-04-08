from django.urls import path
from . import views

urlpatterns = [
	path('', views.calculator_list, name='calculator_list'),
    path('databaseUpload/', views.database_upload, name='database_upload'),
    path('chart-database/', views.chart_database, name='chart_database'),
    path('chart-database/download/', views.download_chart_database, name='download_chart_database'),
    path('chart-database/add-alias/', views.add_alias, name='add_alias'),
    path('chart-database/remove-alias/', views.remove_alias, name='remove_alias'),
    path('chart-database/get-aliases/<int:song_id>/', views.get_song_aliases, name='get_song_aliases'),
    path('save-b50/', views.save_b50_data, name='save_b50_data'),
    path('load-b50/', views.load_b50_data, name='load_b50_data'),
    path('clear-b50/', views.clear_b50_data, name='clear_b50_data'),
]
