from django.urls import path
from networks.views import create_network, network_list, delete_net_5G, delete_net_gen, view_net_5G, view_net_gen
from accounts.views import register, custom_login, custom_logout, delete_user
from accounts.views import error_page  # Importa la vista error_page

# Asignar la vista error_page para manejar los errores 404 y 500
handler404 = error_page
handler500 = error_page

urlpatterns = [
    path('create-network/', create_network, name='create_network'),
    path('network-list/', network_list, name='network_list'),
    path('delete_net_5G/<str:type>/<str:flag>/', delete_net_5G, name='delete_net_5G'),
    path('view_net_5G/<str:type>/', view_net_5G, name='view_net_5G'),
    path('view_net_gen/', view_net_gen, name='view_net_gen'),
    path('delete_net_gen/<str:flag>/', delete_net_gen, name='delete_net_gen'),
    path('register/', register, name='register'),
    path('login/', custom_login, name='login'),
    path('', custom_login, name='home'),
    path('logout/', custom_logout, name='logout'),
    path('delete_user/', delete_user, name='delete_user'),  

]
