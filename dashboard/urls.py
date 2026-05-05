# URLs app file for r2h2_app app
from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='dashboard-landing'),
    path('components', views.home, name='dashboard-home'),
    path('simulations/', views.simulations, name='dashboard-simulations'),
    path('simulations/<int:sim_id>/', views.simulation_detail, name='dashboard-simulation-detail'),
    path('simulations/<int:sim_id>/link/', views.link_components, name='dashboard-link-components'),
    path('simulations/<int:sim_id>/duration/', views.update_sim_duration, name='dashboard-update-sim-duration'),
    path('simulations/<int:sim_id>/run/',                views.run_simulation,    name='dashboard-run-simulation'),
    path('simulations/<int:sim_id>/run/<int:run_id>/',          views.poll_simulation_run,   name='dashboard-poll-simulation-run'),
    path('simulations/<int:sim_id>/run/<int:run_id>/cancel/',   views.cancel_simulation_run,  name='dashboard-cancel-simulation-run'),
    path('simulations/<int:sim_id>/run/<int:run_id>/delete/',   views.delete_simulation_run,  name='dashboard-delete-simulation-run'),
    path('simulations/<int:sim_id>/run/<int:run_id>/description/', views.update_run_description, name='dashboard-update-run-description'),
    path('browse/<str:table_name>', views.browse, name='dashboard-browse'),
    path('browse/<str:table_name>/add', views.add_component, name='dashboard-add-component'),
    path('wind-data/', views.wind_data, name='dashboard-wind-data'),
    path('wind-data/upload/', views.wind_data_upload, name='dashboard-wind-data-upload'),
    path('wind-data/set-dir/', views.wind_data_set_dir, name='dashboard-wind-data-set-dir'),
]
