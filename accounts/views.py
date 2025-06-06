import subprocess
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.conf import settings
from networks.terraform import terraform_destroy  # Asegúrate de que esta función esté definida en terraform.py
import os, shutil


# Vista de Registro
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            login(request, user)  # Inicia sesión automáticamente después de registrarse
            
            request.session['isNew'] = True  # Guardar el estado en la sesión
            return redirect('network_list')  # Redirige a la página principal
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

# Vista de Inicio de Sesión
def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
           
            if request.user.is_authenticated:
                # Cierra la sesión actual (sea quien sea el usuario)
                logout(request)

            login(request, user)
            return redirect('network_list')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

# Vista de Cierre de Sesión
def custom_logout(request):
    logout(request)
    return redirect('login')  # Redirige a la página de inicio de sesión

# Vista de Eliminación de Usuarios
def delete_user(request):
    
    user = get_user(request)
    username = user.username  # Obtener el nombre de usuario antes de eliminarlo
    flag = terraform_destroy(username)

    if flag == True:
       mensaje = f"Error al destruir las redes, se ha restaurado la configuración anterior."
       messages.error(request, mensaje)
       return redirect('network_list') 


    # Eliminar usuario de la base de datos y cerrar sesión
    user.delete()
    logout(request)

    # Ruta del directorio del usuario
    user_dir = os.path.join(settings.BASE_DIR, "terraform", username)

    # Ruta del directorio de backup del usuario 
    backup_dir = os.path.join(settings.BASE_DIR, "terraform", f"{username}_backup")

    # Eliminar el directorio de forma segura si existe
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)  # Borra la carpeta con todo su contenido

    # Eliminar el directorio de backup de forma segura si existe
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)  # Borra la carpeta con todo su contenido

    return redirect('login')  # Redirigir al login después de eliminar

def error_page(request, exception=None):
    return render(request, 'error.html')