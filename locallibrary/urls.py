from django.urls import path
from networks.views import create_network, network_list, delete_net_5G, delete_net_gen
from accounts.views import register, custom_login, custom_logout, delete_user

urlpatterns = [
    path('create-network/', create_network, name='create_network'),
    path('network-list/', network_list, name='network_list'),
    path('delete_net_5G/', delete_net_5G, name='delete_net_5G'),
    path('delete_net_gen/', delete_net_gen, name='delete_net_gen'),
    path('register/', register, name='register'),
    path('login/', custom_login, name='login'),
    path('', custom_login, name='home'),
    path('logout/', custom_logout, name='logout'),
    path('delete_user/', delete_user, name='delete_user'),  

]
