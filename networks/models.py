from django.db import models
from django.contrib.auth.models import User

class UserNetwork(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="networks")
    name = models.CharField(max_length=50)  # Nombre de la red (ej: "red_control")
    network_cidr = models.CharField(max_length=18, unique=True)  # Ej: "10.0.0.0/27"

    def __str__(self):
        return f"{self.user.username} - {self.network_cidr}"

class UserSubnet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subnets")
    name = models.CharField(max_length=50)  # Nombre de la subred (ej: "subred_control")
    subnet_cidr = models.CharField(max_length=18)  # Ej: "10.0.1.0/29"

    def __str__(self):
        return f"{self.user.username} - {self.name}: {self.subnet_cidr}"
    
class SSH_password(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ssh_passwords")  # <- Cambiado aquí
    ssh_password = models.CharField(max_length=50, blank=True)  # Contraseña para SSH

    def __str__(self):
        return f"{self.user.username} - SSH Password"
