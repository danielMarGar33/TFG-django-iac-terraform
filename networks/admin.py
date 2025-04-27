from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin

from .models import (
    UserNetwork, UserSubnet, SSH_password, UserIP, UserDeployedNetworks
)

# Quitar el modelo User original
admin.site.unregister(User)
admin.site.unregister(Group)


# Inlines para mostrar relaciones en el admin de User
class UserNetworkInline(admin.TabularInline):
    model = UserNetwork
    extra = 0

class UserSubnetInline(admin.TabularInline):
    model = UserSubnet
    extra = 0

class SSHPasswordInline(admin.TabularInline):
    model = SSH_password
    extra = 0

class UserIPInline(admin.TabularInline):
    model = UserIP
    extra = 0

class UserDeployedNetworksInline(admin.TabularInline):
    model = UserDeployedNetworks
    extra = 0

# Nuevo Modelo User con búsqueda y relaciones in-line
@admin.register(User)
class CustomUserAdmin(DefaultUserAdmin):
    search_fields = ["username", "email"]
    inlines = [
        UserNetworkInline,
        UserSubnetInline,
        SSHPasswordInline,
        UserIPInline,
        UserDeployedNetworksInline,
    ]

# Admin personalizados para cada modelo
@admin.register(UserNetwork)
class UserNetworkAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "network_cidr")
    search_fields = ("name", "network_cidr", "user__username")
    list_filter = ("user",)
    autocomplete_fields = ["user"]
    ordering = ("user", "name")

@admin.register(UserSubnet)
class UserSubnetAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "subnet_cidr")
    search_fields = ("name", "subnet_cidr", "user__username")
    list_filter = ("user",)
    autocomplete_fields = ["user"]
    ordering = ("user", "name")

@admin.register(SSH_password)
class SSHPasswordAdmin(admin.ModelAdmin):
    list_display = ("user", "ssh_password")
    search_fields = ("user__username",)
    list_filter = ("user",)
    autocomplete_fields = ["user"]

@admin.register(UserIP)
class UserIPAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "ip_address")
    search_fields = ("name", "ip_address", "user__username")
    list_filter = ("user",)
    autocomplete_fields = ["user"]
    ordering = ("user", "name")

@admin.register(UserDeployedNetworks)
class UserDeployedNetworksAdmin(admin.ModelAdmin):
    list_display = ("user", "free5G_deployed", "open5G_deployed", "gen_deployed")
    list_filter = ("user", "free5G_deployed", "open5G_deployed", "gen_deployed")
    search_fields = ("user__username",)
    autocomplete_fields = ["user"]
