from django.urls import path
from . import views

urlpatterns = [
	path('', views.calculator_list, name='calculator_list'),
    path('databaseUpload/', views.database_upload, name='database_upload'),
    path('import-skill-analyzer/', views.import_skill_analyzer, name='import_skill_analyzer'),
    path('chart-database/', views.chart_database, name='chart_database'),
    path('chart-database/download/', views.download_chart_database, name='download_chart_database'),
    path('chart-database/alias-upload/', views.alias_upload, name='alias_upload'),
    path('chart-database/add-alias/', views.add_alias, name='add_alias'),
    path('chart-database/remove-alias/', views.remove_alias, name='remove_alias'),
    path('chart-database/get-aliases/<int:song_id>/', views.get_song_aliases, name='get_song_aliases'),
    path('save-b50/', views.save_b50_data, name='save_b50_data'),
    path('load-b50/', views.load_b50_data, name='load_b50_data'),
    path('load-astro-cache/', views.load_astro_cache_data, name='load_astro_cache_data'),
    path('download-decompressed-cache/', views.download_decompressed_cache, name='download_decompressed_cache'),
    path('convert-cache-to-b50/', views.convert_cache_to_b50, name='convert_cache_to_b50'),
    path('convert-cache-to-all-scores/', views.convert_cache_to_all_scores, name='convert_cache_to_all_scores'),
    path('convert-cache-to-b50-direct/', views.convert_cache_to_b50_direct, name='convert_cache_to_b50_direct'),
    path('download-converted-b50/', views.download_converted_b50, name='download_converted_b50'),
    path('clear-b50/', views.clear_b50_data, name='clear_b50_data'),
]
