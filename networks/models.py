from django.db import models
from django.contrib.auth.models import User

class UserNetwork(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="networks")
    name = models.CharField(max_length=50)  # Nombre de la red (ej: "red_mgmt")
    network_cidr = models.CharField(max_length=18, unique=True)  # Ej: "10.0.0.0/27"

    def __str__(self):
        return f"{self.user.username} - {self.network_cidr}"

class UserSubnet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subnets")
    name = models.CharField(max_length=50)  # Nombre de la subred (ej: "subred_mgmt")
    subnet_cidr = models.CharField(max_length=18)  # Ej: "10.0.1.0/29"

    def __str__(self):
        return f"{self.user.username} - {self.name}: {self.subnet_cidr}"
    
class SSH_password(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ssh_passwords")  # <- Cambiado aquí
    ssh_password = models.CharField(max_length=50, blank=True)  # Contraseña para SSH

    def __str__(self):
        return f"{self.user.username} - SSH Password"

class UserIP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")  # Corregido "adress" -> "addresses"
    name = models.CharField(max_length=50)  # Nombre de la IP (ej: "ip_mgmt")
    ip_address = models.GenericIPAddressField(protocol="both", unpack_ipv4=True)  # Permite IPv4 e IPv6

    def __str__(self):
        return f"{self.user.username} - {self.name}: {self.ip_address}"
    

class UserDeployedNetworks(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deployed_networks")
    free5G_deployed = models.BooleanField(default=False)  # Indica si la red Free5G ha sido desplegada
    open5G_deployed = models.BooleanField(default=False)  # Indica si la red Core5G ha sido desplegada 
    gen_deployed = models.BooleanField(default=False)  # Indica si la red genérica ha sido desplegada 

    def __str__(self):
        return f"{self.user.username} - Deployed Networks"