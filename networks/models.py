from django.db import models
from django.contrib.auth.models import User

class UserNetwork(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="networks")
    name = models.CharField(max_length=50)
    network_cidr = models.CharField(max_length=18, unique=True)

    def __str__(self):
        return f"{self.user.username} - {self.network_cidr}"

    class Meta:
        verbose_name = "User network"
        verbose_name_plural = "User networks"

class UserSubnet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subnets")
    name = models.CharField(max_length=50)
    subnet_cidr = models.CharField(max_length=18)

    def __str__(self):
        return f"{self.user.username} - {self.name}: {self.subnet_cidr}"

    class Meta:
        verbose_name = "User subnet"
        verbose_name_plural = "User subnets"

class SSH_password(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ssh_passwords")
    ssh_password = models.CharField(max_length=50, blank=False)
    type = models.CharField(max_length=50, default="password")

    def __str__(self):
        return f"{self.user.username} - SSH Password"

    class Meta:
        verbose_name = "SSH password"
        verbose_name_plural = "SSH passwords"

class UserIP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    name = models.CharField(max_length=50)
    ip_address = models.GenericIPAddressField(protocol="both", unpack_ipv4=True)

    def __str__(self):
        return f"{self.user.username} - {self.name}: {self.ip_address}"

    class Meta:
        verbose_name = "User IP"
        verbose_name_plural = "User IPs"

class UserDeployedNetworks(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deployed_networks")
    free5G_deployed = models.BooleanField(default=False)
    open5G_deployed = models.BooleanField(default=False)
    gen_deployed = models.BooleanField(default=False)
    free5G_error = models.BooleanField(default=False)
    open5G_error = models.BooleanField(default=False)
    gen_error = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - Deployed Networks"

    class Meta:
        verbose_name = "User deployed network"
        verbose_name_plural = "User deployed networks"
