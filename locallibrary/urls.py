from django.urls import path
from django.contrib import admin
from networks.views import create_network, network_list, delete_net_5G, delete_net_gen, view_net_5G, view_net_gen
from accounts.views import register, custom_login, custom_logout, delete_user
from networks.terraform import terraform_check_existing_resources
from accounts.views import error_page

handler404 = error_page

urlpatterns = [
    path('admin/', admin.site.urls),
    path('check_networks/', terraform_check_existing_resources, name='check_networks'),
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

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
