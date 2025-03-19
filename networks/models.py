from django.db import models
from django.contrib.auth.models import User

class UserNetwork(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="network")
    network_cidr = models.CharField(max_length=18, unique=True)  # Ej: "10.0.0.0/27"
    ssh_password = models.CharField(max_length=50, blank=True)  # Contrasena para SSH

    def __str__(self):
        return f"{self.user.username} - {self.network_cidr}"


class UserSubnet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subnets")
    name = models.CharField(max_length=50)  # Nombre de la subred (ej: "subred_control")
    subnet_cidr = models.CharField(max_length=18)  # Ej: "10.0.1.0/29"

    def __str__(self):
        return f"{self.user.username} - {self.name}: {self.subnet_cidr}"
