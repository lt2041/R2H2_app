# URLs app file for r2h2_app app
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='dashboard-home'),
    path('simulations/', views.simulations, name='dashboard-simulations'),
    path('simulations/<int:sim_id>/', views.simulation_detail, name='dashboard-simulation-detail'),
    path('simulations/<int:sim_id>/link/', views.link_components, name='dashboard-link-components'),
    path('browse/<str:table_name>', views.browse, name='dashboard-browse'),
    path('browse/<str:table_name>/add', views.add_component, name='dashboard-add-component'),
]
