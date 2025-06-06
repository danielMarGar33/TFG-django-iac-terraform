from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseNotAllowed
from django.contrib.auth import get_user
from django.urls import reverse
from django.conf import settings
from .models import UserNetwork, UserSubnet, SSH_password, UserIP, UserDeployedNetworks
from .forms import NetworkForm
from .terraform import append_section_5G, append_section_gen, terraform_template, terraform_apply, terraform_apply_output, terraform_init_apply
from Crypto.Cipher import AES
import base64
import os, re, ipaddress, json


#################################################################################
# TODO:
# 4. Creación de un usuario administrador para todas las redes
#################################################################################


# Red base y tamano de subred
BASE_CIDR = "10.0.0.0/8"
NET_MASK = 16  # Cada usuario recibe una subred de 16 IPs
SUBNET_MASK = 24  # Para subdivisión adicional si es necesario


##################################################
# TODO: Cambiar las imagenes por las que correspondan
CORE_FREE_IMAGE = "db02fc5c-cacc-42be-8e5f-90f2db65cf7c"
CORE_OPEN_IMAGE = "db02fc5c-cacc-42be-8e5f-90f2db65cf7c"
##################################################

### FUNCIONES DE ENCRIPTACION Y DESENCRIPTACION ###
def encriptar_contraseña(contraseña):
    """ Encripta la contraseña """
    key = settings.ENCRYPTION_KEY.encode('utf-8')
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(contraseña.encode('utf-8'))
    return base64.b64encode(cipher.nonce + tag + ciphertext).decode('utf-8')

def desencriptar_contraseña(contraseña):
    """ Desencripta la contraseña """
    contraseña = base64.b64decode(contraseña.encode('utf-8'))
    key = settings.ENCRYPTION_KEY.encode('utf-8')
    nonce, tag, ciphertext = contraseña[:16], contraseña[16:32], contraseña[32:]
    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')

### FUNCIONES PARA EXTRAER, GUARDAR Y ELIMINAR DATOS EN BBDD ###

def asignar_flag_red(usuario, tipo_red):
    if tipo_red == "free":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"free5G_deployed": True})
    elif tipo_red == "open":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"open5G_deployed": True})
    elif tipo_red == "gen":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"gen_deployed": True})
    elif tipo_red == "free_error":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"free5G_error": True})
    elif tipo_red == "open_error":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"open5G_error": True})
    elif tipo_red == "gen_error":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"gen_error": True})

def eliminar_flag_red(usuario, tipo_red):
    if tipo_red == "free":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"free5G_deployed": False})
    elif tipo_red == "open":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"open5G_deployed": False})
    elif tipo_red == "gen":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"gen_deployed": False})
    elif tipo_red == "free_error":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"free5G_error": False})
    elif tipo_red == "open_error":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"open5G_error": False})
    elif tipo_red == "gen_error":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"gen_error": False})
    

def obtener_flag_red(usuario, tipo_red):
    """ Devuelve el valor de la bandera de la red """
    try:
        if tipo_red == "free":
            return UserDeployedNetworks.objects.get(user=usuario).free5G_deployed
        elif tipo_red == "open":
            return UserDeployedNetworks.objects.get(user=usuario).open5G_deployed
        elif tipo_red == "gen":
            return UserDeployedNetworks.objects.get(user=usuario).gen_deployed
        elif tipo_red == "free_error":
            return UserDeployedNetworks.objects.get(user=usuario).free5G_error
        elif tipo_red == "open_error":
            return UserDeployedNetworks.objects.get(user=usuario).open5G_error
        elif tipo_red == "gen_error":
            return UserDeployedNetworks.objects.get(user=usuario).gen_error
    except UserDeployedNetworks.DoesNotExist:
        return False

def asignar_red_usuario(usuario, red_cidr, nombre):
    """ Asigna una red principal a un usuario en la BD """
    UserNetwork.objects.update_or_create(user=usuario, name=nombre, defaults={"network_cidr": red_cidr})

def obtener_red(usuario, nombre):
    """ Obtiene la red principal de un usuario """
    try:
        return UserNetwork.objects.get(user=usuario, name=nombre).network_cidr
    except UserNetwork.DoesNotExist:
        return None
    
def asignar_contraseña_ssh(usuario, contraseña, type):
    """ Asigna una contraseña de SSH a un usuario en la BD """
    SSH_password.objects.update_or_create(user=usuario, defaults={"ssh_password": encriptar_contraseña(contraseña)}, type=type)

def eliminar_contraseña_ssh(usuario, type):
    """ Elimina la contraseña de SSH de un usuario en la BD """
    try:
        SSH_password.objects.filter(user=usuario, type=type).delete()
    except SSH_password.DoesNotExist:
        return None

def asignar_direccion_ip(usuario, direccion_ip, nombre):
    """ Asigna una contraseña de SSH a un usuario en la BD """
    UserIP.objects.update_or_create(user=usuario, name=nombre, defaults={"ip_address": direccion_ip}) 

def eliminar_direccion_ip(usuario, nombre):
    """ Elimina una dirección IP específica de la BD """
    try:
       UserIP.objects.filter(user=usuario, name=nombre).delete()
    except UserIP.DoesNotExist:
        return None

def obtener_direccion_ip(usuario, nombre):
    """ Obtiene la dirección IP de un usuario """
    try:
        return UserIP.objects.get(user=usuario, name=nombre).ip_address
    except UserIP.DoesNotExist:
        return None

def eliminar_red_usuario(usuario, nombre):
    """ Elimina la red principal del usuario """
    try:
     UserNetwork.objects.filter(user=usuario, name=nombre).delete()
    except UserNetwork.DoesNotExist:
        return None

def asignar_subred(usuario, nombre_subred, subred_cidr):
    """ Asigna una subred específica a un usuario en la BD """
    UserSubnet.objects.create(user=usuario, name=nombre_subred, subnet_cidr=subred_cidr)

def obtener_subredes(usuario):
    """ Devuelve todas las subredes de un usuario """
    return list(UserSubnet.objects.filter(user=usuario).values_list("name", "subnet_cidr"))

def obtener_subred_por_nombre(usuario, nombre_subred):
    """Obtiene el valor de subnet_cidr de una subred específica de un usuario por nombre"""
    subred = UserSubnet.objects.filter(user=usuario, name=nombre_subred).first()
    
    if subred:
        return subred.subnet_cidr  
    return "Subred no encontrada" 

def eliminar_subred(usuario, nombre_subred):
    """ Elimina una subred específica de la BD """
    try:
      UserSubnet.objects.filter(user=usuario, name=nombre_subred).delete()
    except UserSubnet.DoesNotExist:
        return None

def obtener_subred_unica(base_cidr, assigned_subnets, subnet_mask):
    network = ipaddress.IPv4Network(base_cidr, strict=False)
    subnets = list(network.subnets(new_prefix=subnet_mask))

    # Verificar si los elementos de assigned_subnets son las tuplas (subredes) o solo las subredes de usuario (creación de usuario)
    if all(isinstance(item, tuple) and len(item) == 2 for item in assigned_subnets):
        assigned_subnets_only = {subnet for _, subnet in assigned_subnets}
    else:
        assigned_subnets_only = set(assigned_subnets)

    for subnet in subnets:
        if str(subnet) not in assigned_subnets_only:
            return str(subnet)

    raise ValueError("No quedan subredes disponibles.")

def get_gateway(subnet_cidr):
    """ Devuelve la dirección IP del gateway de una subred """
    network = ipaddress.ip_network(subnet_cidr, strict=False)
    return str(network.network_address + 1)  # Primera IP válida como gateway


### VISTAS ###

@login_required
def create_initial_config(request):
    usuario = get_user(request)

    if not UserNetwork.objects.filter(user=usuario).exists():

        terraform_config = terraform_template()
    
        user_dir = os.path.join(settings.BASE_DIR, "terraform", usuario.username)
        os.makedirs(user_dir, exist_ok=True)

        main_tf_path = os.path.join(user_dir, "main.tf")
        with open(main_tf_path, "w") as f:
            f.write(terraform_config)

        flag = terraform_init_apply(usuario.username)
        if flag:
            redirect('delete_user')


@login_required
def network_list(request):
    isNew = request.session.pop('isNew', False)  
    if isNew:
        create_initial_config(request)

    # Obtener mensaje de la URL si existe
    url_mensaje = request.GET.get('mensaje', None)
    if url_mensaje:
        messages.info(request, url_mensaje)

    creada_red_5G_open = obtener_flag_red(request.user, "open")
    creada_red_5G_free = obtener_flag_red(request.user, "free")
    creada_red_gen = obtener_flag_red(request.user, "gen")  
    error_red_5G_open = obtener_flag_red(request.user, "open_error")
    error_red_5G_free = obtener_flag_red(request.user, "free_error")
    error_red_gen = obtener_flag_red(request.user, "gen_error")

    context = {
        'creada_red_5G_open': creada_red_5G_open,
        'creada_red_5G_free': creada_red_5G_free,
        'creada_red_gen': creada_red_gen,
        'error_red_5G_open': error_red_5G_open,
        'error_red_5G_free': error_red_5G_free,
        'error_red_gen': error_red_gen,
    }

    return render(request, 'network_list.html', context)

@login_required
@require_http_methods(["POST", "PUT"])
def create_network(request):
    usuario = get_user(request)

    if request.method == 'POST':
        form = NetworkForm(request.POST)

        if form.is_valid():

            Is5G_open = form.cleaned_data['opciones'] == 'opcion5G_open'
            Is5G_free = form.cleaned_data['opciones'] == 'opcion5G_free'
            IsGen = form.cleaned_data['opciones'] == 'opcionGen'


            if Is5G_open or Is5G_free:

                    asignar_contraseña_ssh(usuario, request.POST.get('ssh_password'), "open") if Is5G_open else asignar_contraseña_ssh(usuario, request.POST.get('ssh_password'), "free")
                    type = "open" if Is5G_open else "free"
                    core = CORE_OPEN_IMAGE if Is5G_open else CORE_FREE_IMAGE

                    assigned_nets = list(UserNetwork.objects.values_list('network_cidr', flat=True))
                    red_unica = obtener_subred_unica(BASE_CIDR, assigned_nets, NET_MASK)
                    asignar_red_usuario(usuario, red_unica, f"{type}5G_mgmt_network")

                    assigned_nets = list(UserNetwork.objects.values_list('network_cidr', flat=True))
                    red_unica = obtener_subred_unica(BASE_CIDR, assigned_nets, NET_MASK)
                    asignar_red_usuario(usuario, red_unica, f"{type}5G_network")

                    asignar_subred(usuario, f"{type}5G_mgmt_subnetwork", obtener_subred_unica(obtener_red(usuario, f"{type}5G_mgmt_network"), obtener_subredes(usuario), SUBNET_MASK))
                    asignar_subred(usuario, f"{type}5G_UE_AGF_subnetwork", obtener_subred_unica(obtener_red(usuario, f"{type}5G_network"), obtener_subredes(usuario), SUBNET_MASK))
                    asignar_subred(usuario, f"{type}5G_AGF_core5G_subnetwork", obtener_subred_unica(obtener_red(usuario, f"{type}5G_network"), obtener_subredes(usuario), SUBNET_MASK))
                    asignar_subred(usuario, f"{type}5G_core5G_server_subnetwork", obtener_subred_unica(obtener_red(usuario, f"{type}5G_network"), obtener_subredes(usuario), SUBNET_MASK))

                    resultado = apply_terraform_5G(usuario, usuario.username, core, type)
                    asignar_flag_red(usuario, type)

                    if resultado:
                        mensaje = f"Error al crear la red {type}5G"
                        asignar_flag_red(usuario, f"{type}_error")
                        messages.error(request, mensaje)
                        return redirect(reverse('network_list'))
                    else:
                        eliminar_flag_red(usuario, f"{type}_error")
                        messages.success(request, f"Red {type}5G creada correctamente")
                        
                        # Cargar la salida de Terraform
                        with open(f"terraform/{usuario.username}/terraform_outputs.json") as f:
                                data = json.load(f)

                        # Obtener la IPs de los servidores
                        UE_mgmt_ip = data[f"UE_{type}5G_mgmt_ip"]["value"][0]
                        asignar_direccion_ip(usuario, UE_mgmt_ip, f"UE_{type}5G_mgmt_ip")

                        AGF_mgmt_ip = data[f"AGF_{type}5G_mgmt_ip"]["value"][0]
                        asignar_direccion_ip(usuario, AGF_mgmt_ip, f"AGF_{type}5G_mgmt_ip")

                        core5G_mgmt_ip = data[f"core5G_{type}5G_mgmt_ip"]["value"][0]
                        asignar_direccion_ip(usuario, core5G_mgmt_ip, f"core5G_{type}5G_mgmt_ip")

                        server_mgmt_ip = data[f"server_{type}5G_mgmt_ip"]["value"][0]
                        asignar_direccion_ip(usuario, server_mgmt_ip, f"server_{type}5G_mgmt_ip")

                        broker_mgmt_ip = data[f"broker_{type}5G_mgmt_ip"]["value"]
                        asignar_direccion_ip(usuario, broker_mgmt_ip, f"broker_{type}5G_mgmt_ip")

                        UE_UE_ip = data[f"UE_{type}5G_UE_ip"]["value"][0]
                        asignar_direccion_ip(usuario, UE_UE_ip, f"UE_{type}5G_UE_ip")

                        AGF_UE_ip = data[f"AGF_{type}5G_UE_ip"]["value"][0]
                        asignar_direccion_ip(usuario, AGF_UE_ip, f"AGF_{type}5G_UE_ip")

                        AGF_core5G_ip = data[f"AGF_{type}5G_core5G_ip"]["value"][0]
                        asignar_direccion_ip(usuario, AGF_core5G_ip, f"AGF_{type}5G_core5G_ip")

                        core5G_AGF_ip = data[f"core5G_{type}5G_AGF_ip"]["value"][0]
                        asignar_direccion_ip(usuario, core5G_AGF_ip, f"core5G_{type}5G_AGF_ip")

                        core5G_server_ip = data[f"core5G_{type}5G_server_ip"]["value"][0]
                        asignar_direccion_ip(usuario, core5G_server_ip, f"core5G_{type}5G_server_ip")

                        server_core5G_ip = data[f"server_{type}5G_core5G_ip"]["value"][0]
                        asignar_direccion_ip(usuario, server_core5G_ip, f"server_{type}5G_core5G_ip")

                        return redirect(reverse('network_list'))
        

            elif IsGen:
                    asignar_contraseña_ssh(usuario, request.POST.get('ssh_password'), "gen")

                    assigned_nets = list(UserNetwork.objects.values_list('network_cidr', flat=True))
                    red_unica = obtener_subred_unica(BASE_CIDR, assigned_nets, NET_MASK)
                    asignar_red_usuario(usuario, red_unica, "gen_network")

                    assigned_nets = list(UserNetwork.objects.values_list('network_cidr', flat=True))
                    red_unica = obtener_subred_unica(BASE_CIDR, assigned_nets, NET_MASK)
                    asignar_red_usuario(usuario, red_unica, "gen_mgmt_network")

                    asignar_subred(usuario, "gen_mgmt_subnetwork", obtener_subred_unica(obtener_red(usuario, "gen_mgmt_network"), obtener_subredes(usuario), SUBNET_MASK))
                    asignar_subred(usuario, "gen_subnetwork", obtener_subred_unica(obtener_red(usuario, "gen_network"), obtener_subredes(usuario), SUBNET_MASK))

                    resultado = apply_terraform_gen(usuario, usuario.username) 
                    asignar_flag_red(usuario, "gen")

                    if resultado:
                        mensaje = "Error al crear la red Ampliada de Pruebas"
                        asignar_flag_red(usuario, "gen_error")
                        messages.error(request, mensaje)
                        return redirect(reverse('network_list'))
                    
                    else: 
                        eliminar_flag_red(usuario, "gen_error")
                        messages.success(request, "Red Ampliada de Pruebas creada correctamente")

                        # Cargar la salida de Terraform
                        with open(f"terraform/{usuario.username}/terraform_outputs.json") as f:
                                data = json.load(f)

                        gen_broker_ip = data["gen_broker_ip"]["value"]
                        asignar_direccion_ip(usuario, gen_broker_ip, "gen_broker_ip")

                        gen_controler_ip = data["gen_controller_ip"]["value"][0]
                        asignar_direccion_ip(usuario, gen_controler_ip, "gen_controller_ip")

                        gen_worker_ip = data["gen_worker_ip"]["value"][0]
                        asignar_direccion_ip(usuario, gen_worker_ip, "gen_worker_ip")
                        return redirect(reverse('network_list'))

        else:
            creada_red_5G_open = obtener_flag_red(request.user, "open")
            creada_red_5G_free = obtener_flag_red(request.user, "free")
            creada_red_gen = obtener_flag_red(request.user, "gen")

            context = {
               'creada_red_5G_open': creada_red_5G_open,
               'creada_red_5G_free': creada_red_5G_free,
               'creada_red_gen': creada_red_gen,
               'form': form
        }
        return render(request, 'create_network.html', context)

    else:
        return redirect(reverse('network_list'))


def apply_terraform_5G(usuario, username, core_image, type):
    user_dir = os.path.join("terraform", username)
    os.makedirs(user_dir, exist_ok=True)

    main_tf_path = os.path.join(user_dir, "main.tf")

    append_section = append_section_5G(username, 
                                       obtener_subred_por_nombre(usuario, f"{type}5G_UE_AGF_subnetwork"), 
                                       obtener_subred_por_nombre(usuario, f"{type}5G_AGF_core5G_subnetwork"), 
                                       obtener_subred_por_nombre(usuario, f"{type}5G_core5G_server_subnetwork"),
                                       obtener_subred_por_nombre(usuario, f"{type}5G_mgmt_subnetwork"),
                                       get_gateway(obtener_subred_por_nombre(usuario, f"{type}5G_mgmt_subnetwork")),
                                       core_image,
                                       type,
                                       desencriptar_contraseña(SSH_password.objects.get(user=usuario, type=type).ssh_password)
                                       )
    with open(main_tf_path, "a") as f:
        f.write(append_section)
    
    return terraform_apply_output(username)
    


def apply_terraform_gen(usuario, username):

    user_dir = os.path.join("terraform", username)
    os.makedirs(user_dir, exist_ok=True)

    main_tf_path = os.path.join(user_dir, "main.tf")

    append_section = append_section_gen(username, 
                                       obtener_subred_por_nombre(usuario, f"gen_mgmt_subnetwork"), 
                                       obtener_subred_por_nombre(usuario, f"gen_subnetwork"),
                                       get_gateway(obtener_subred_por_nombre(usuario, f"gen_mgmt_subnetwork")),
                                       desencriptar_contraseña(SSH_password.objects.get(user=usuario, type="gen").ssh_password)
                                       )
    with open(main_tf_path, "a") as f:
        f.write(append_section)
    
    return terraform_apply_output(username)


@login_required
@require_http_methods(["POST", "PUT"])
def delete_net_5G(request, type, flag):

    usuario = get_user(request)
    username = usuario.username
    user_dir = os.path.join("terraform", username)
    main_tf_path = os.path.join(user_dir, "main.tf")

    if type == "free":
        core_image = CORE_FREE_IMAGE
    else:
        core_image = CORE_OPEN_IMAGE
        
    if not os.path.exists(main_tf_path):
        return redirect(reverse('network_list'))

    with open(main_tf_path, "r") as f:
        content = f.read()

    append_section = append_section_5G(username, 
                                       obtener_subred_por_nombre(usuario, f"{type}5G_UE_AGF_subnetwork"), 
                                       obtener_subred_por_nombre(usuario, f"{type}5G_AGF_core5G_subnetwork"), 
                                       obtener_subred_por_nombre(usuario, f"{type}5G_core5G_server_subnetwork"),
                                       obtener_subred_por_nombre(usuario, f"{type}5G_mgmt_subnetwork"),
                                       get_gateway(obtener_subred_por_nombre(usuario, f"{type}5G_mgmt_subnetwork")),
                                       core_image,
                                       type,
                                       desencriptar_contraseña(SSH_password.objects.get(user=usuario, type=type).ssh_password) 
                                       )

    old_content = re.sub(re.escape(append_section), "", content)

    with open(main_tf_path, "w") as f:
        f.write(old_content)

    result = terraform_apply(usuario.username)
    print("result", result)

    if result == False:
        eliminar_flag_red(usuario, type)

        #Eliminar la contraseña SSH
        eliminar_contraseña_ssh(usuario, type)

        #Eliminar las redes
        eliminar_red_usuario(usuario, f"{type}5G_mgmt_network")
        eliminar_red_usuario(usuario, f"{type}5G_network")

        #Eliminar las subredes
        eliminar_subred(usuario, f"{type}5G_UE_AGF_subnetwork")
        eliminar_subred(usuario, f"{type}5G_AGF_core5G_subnetwork")
        eliminar_subred(usuario, f"{type}5G_core5G_server_subnetwork")
        eliminar_subred(usuario, f"{type}5G_mgmt_subnetwork")

        # Eliminar las IPs
        eliminar_direccion_ip(usuario, f"UE_{type}5G_mgmt_ip")
        eliminar_direccion_ip(usuario, f"AGF_{type}5G_mgmt_ip")
        eliminar_direccion_ip(usuario, f"core5G_{type}5G_mgmt_ip")
        eliminar_direccion_ip(usuario, f"server_{type}5G_mgmt_ip")
        eliminar_direccion_ip(usuario, f"broker_{type}5G_mgmt_ip")
        eliminar_direccion_ip(usuario, f"UE_{type}5G_UE_ip")
        eliminar_direccion_ip(usuario, f"AGF_{type}5G_UE_ip")
        eliminar_direccion_ip(usuario, f"AGF_{type}5G_core5G_ip")
        eliminar_direccion_ip(usuario, f"core5G_{type}5G_AGF_ip")
        eliminar_direccion_ip(usuario, f"core5G_{type}5G_server_ip")
        eliminar_direccion_ip(usuario, f"server_{type}5G_core5G_ip")


        mensaje = f"Red {type}5G eliminada correctamente"
        messages.success(request, mensaje)
        eliminar_flag_red(usuario, f"{type}_error")
        return redirect('network_list')  
    
    else :
       mensaje = f"Error al eliminar la red {type}5G, se ha restaurado la configuración anterior."
       asignar_flag_red(usuario, f"{type}_error")
       messages.error(request, mensaje)
       return redirect('network_list') 


@login_required
@require_http_methods(["POST", "PUT"])
def delete_net_gen(request, flag):

    usuario = get_user(request)
    username = usuario.username
    user_dir = os.path.join("terraform", username)
    main_tf_path = os.path.join(user_dir, "main.tf")

    if not os.path.exists(main_tf_path):
        return redirect(reverse('network_list'))
    
    with open(main_tf_path, "r") as f:
        content = f.read()

    append_section = append_section_gen(username, 
                                       obtener_subred_por_nombre(usuario, f"gen_mgmt_subnetwork"), 
                                       obtener_subred_por_nombre(usuario, f"gen_subnetwork"),
                                       get_gateway(obtener_subred_por_nombre(usuario, f"gen_mgmt_subnetwork")),
                                       desencriptar_contraseña(SSH_password.objects.get(user=usuario, type="gen").ssh_password)
                                       )
    
    old_content = re.sub(re.escape(append_section), "", content)

    with open(main_tf_path, "w") as f:
        f.write(old_content)

    result = terraform_apply(usuario.username)

    if result == False:
       eliminar_flag_red(usuario, "gen")

       #Eliminar la contraseña SSH
       eliminar_contraseña_ssh(usuario, "gen")

       #Eliminar las redes
       eliminar_red_usuario(usuario, "gen_network")
       eliminar_red_usuario(usuario, "gen_mgmt_network")

       #Eliminar las subredes
       eliminar_subred(usuario, "gen_mgmt_subnetwork")
       eliminar_subred(usuario, "gen_subnetwork")

       # Eliminar las IPs
       eliminar_direccion_ip(usuario, "gen_broker_ip")
       eliminar_direccion_ip(usuario, "gen_controller_ip")
       eliminar_direccion_ip(usuario, "gen_worker_ip")
    
       mensaje = "Red Ampliada de Pruebas eliminada correctamente"
       messages.success(request, mensaje)
       eliminar_flag_red(usuario, "gen_error")
       return redirect('network_list') 
    
    else :
       mensaje = f"Error al eliminar la red Ampliada de Pruebas, se ha restaurado la configuración anterior."
       messages.error(request, mensaje)
       asignar_flag_red(usuario, "gen_error")
       return redirect('network_list') 


@login_required
def view_net_5G(request, type):

    UE_mgmt_ip = obtener_direccion_ip(request.user, f"UE_{type}5G_mgmt_ip")
    AGF_mgmt_ip = obtener_direccion_ip(request.user, f"AGF_{type}5G_mgmt_ip")
    core5G_mgmt_ip = obtener_direccion_ip(request.user, f"core5G_{type}5G_mgmt_ip")
    server_mgmt_ip = obtener_direccion_ip(request.user, f"server_{type}5G_mgmt_ip")
    broker_mgmt_ip = obtener_direccion_ip(request.user, f"broker_{type}5G_mgmt_ip")
    UE_UE_ip = obtener_direccion_ip(request.user, f"UE_{type}5G_UE_ip")
    AGF_UE_ip = obtener_direccion_ip(request.user, f"AGF_{type}5G_UE_ip")
    AGF_core5G_ip = obtener_direccion_ip(request.user, f"AGF_{type}5G_core5G_ip")
    core5G_AGF_ip = obtener_direccion_ip(request.user, f"core5G_{type}5G_AGF_ip")
    core5G_server_ip = obtener_direccion_ip(request.user, f"core5G_{type}5G_server_ip")
    server_core5G_ip = obtener_direccion_ip(request.user, f"server_{type}5G_core5G_ip")

    
    
    string_type = type + "5G"
    context = {
        'UE_5G_mgmt_ip': UE_mgmt_ip,
        'AGF_5G_mgmt_ip': AGF_mgmt_ip,
        'core5G_5G_mgmt_ip': core5G_mgmt_ip,
        'server_5G_mgmt_ip': server_mgmt_ip,
        'broker_5G_mgmt_ip': broker_mgmt_ip,
        'UE_5G_UE_ip': UE_UE_ip,
        'AGF_5G_UE_ip': AGF_UE_ip,
        'AGF_5G_core5G_ip': AGF_core5G_ip,
        'core5G_5G_AGF_ip': core5G_AGF_ip,
        'core5G_5G_server_ip': core5G_server_ip,
        'server_5G_core5G_ip': server_core5G_ip,
        'type': string_type
    }

    return render(request, 'network5G.html', context)

@login_required
def view_net_gen(request):

    gen_broker_ip = obtener_direccion_ip(request.user, "gen_broker_ip")
    print("gen_broker_ip", gen_broker_ip)
    context = {
        'gen_broker_ip': gen_broker_ip,
        'gen_controller_ip': obtener_direccion_ip(request.user, "gen_controller_ip"),
        'gen_worker_ip': obtener_direccion_ip(request.user, "gen_worker_ip"),
    }
    return render(request, 'network_gen.html', context)

