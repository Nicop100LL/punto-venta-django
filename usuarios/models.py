from django.contrib.auth.models import AbstractUser
from django.db import models

class Empresa(models.Model):
    nombre = models.CharField(max_length=100)
    cuit = models.CharField(max_length=13, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    condicion_iva = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.nombre

class Usuario(AbstractUser):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, null=True, blank=True)

    def is_superuser_or_staff(self):
        return self.is_superuser or self.is_staff

class Cliente(models.Model):
    nombre = models.CharField(max_length=255)
    cuit = models.CharField(max_length=20, blank=True, null=True)
    condicion_iva = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.nombre

