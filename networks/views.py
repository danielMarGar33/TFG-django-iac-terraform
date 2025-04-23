from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user
from .models import UserNetwork, UserSubnet, SSH_password, UserIP, UserDeployedNetworks
from .forms import NetworkForm
from .terraform import append_section_5G, append_section_gen, terraform_template, terraform_apply, terraform_apply_output, terraform_init_apply_output, terraform_destroy
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


### FUNCIONES PARA EXTRAER, GUARDAR Y ELIMINAR DATOS EN BBDD ###

def asignar_flag_red(usuario, tipo_red):
    if tipo_red == "free":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"free5G_deployed": True})
    elif tipo_red == "open":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"open5G_deployed": True})
    elif tipo_red == "gen":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"gen_deployed": True})

def eliminar_flag_red(usuario, tipo_red):
    if tipo_red == "free":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"free5G_deployed": False})
    elif tipo_red == "open":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"open5G_deployed": False})
    elif tipo_red == "gen":
        UserDeployedNetworks.objects.update_or_create(user=usuario, defaults={"gen_deployed": False})

def obtener_flag_red(usuario, tipo_red):
    """ Devuelve el valor de la bandera de la red """
    try:
        if tipo_red == "free":
            return UserDeployedNetworks.objects.get(user=usuario).free5G_deployed
        elif tipo_red == "open":
            return UserDeployedNetworks.objects.get(user=usuario).open5G_deployed
        elif tipo_red == "gen":
            return UserDeployedNetworks.objects.get(user=usuario).gen_deployed
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
    
def asignar_contraseña_ssh(usuario, contraseña):
    """ Asigna una contraseña de SSH a un usuario en la BD """
    SSH_password.objects.update_or_create(user=usuario, defaults={"ssh_password": contraseña})

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

        asignar_contraseña_ssh(usuario, request.session.get('ssh_password'))
        terraform_config = terraform_template()
    
        user_dir = os.path.join(settings.BASE_DIR, "terraform", usuario.username)
        os.makedirs(user_dir, exist_ok=True)

        main_tf_path = os.path.join(user_dir, "main.tf")
        with open(main_tf_path, "w") as f:
            f.write(terraform_config)

        terraform_init_apply_output(usuario.username)


@login_required
def network_list(request):

    isNew = request.session.pop('isNew', False)  
    if isNew:
        create_initial_config(request)

    mensaje = request.GET.get('mensaje', None)
    creada_red_5G_open = obtener_flag_red(request.user, "open")
    creada_red_5G_free = obtener_flag_red(request.user, "free")
    creada_red_gen = obtener_flag_red(request.user, "gen")  

    context = {
        'creada_red_5G_open': creada_red_5G_open,
        'creada_red_5G_free': creada_red_5G_free,
        'creada_red_gen': creada_red_gen,
        'mensaje': mensaje,
    }

    return render(request, 'network_list.html', context)

@login_required
def create_network(request):
    usuario = get_user(request)

    if request.method == 'POST':
        form = NetworkForm(request.POST)

        if form.is_valid():

            Is5G_open = form.cleaned_data['opciones'] == 'opcion5G_open'
            Is5G_free = form.cleaned_data['opciones'] == 'opcion5G_free'
            IsGen = form.cleaned_data['opciones'] == 'opcionGen'

            if Is5G_open or Is5G_free:
                
                type = "open" if Is5G_open else "free"
                core = CORE_OPEN_IMAGE if Is5G_open else CORE_FREE_IMAGE

                assigned_nets = list(UserNetwork.objects.values_list('network_cidr', flat=True))
                red_unica = obtener_subred_unica(BASE_CIDR, assigned_nets, NET_MASK)
                asignar_red_usuario(usuario, red_unica, f"user_{type}5G_mgmt_network")

                assigned_nets = list(UserNetwork.objects.values_list('network_cidr', flat=True))
                red_unica = obtener_subred_unica(BASE_CIDR, assigned_nets, NET_MASK)
                asignar_red_usuario(usuario, red_unica, f"user_{type}5G_network")

                asignar_subred(usuario, f"subred_{type}5G_mgmt", obtener_subred_unica(obtener_red(usuario, f"user_{type}5G_mgmt_network"), obtener_subredes(usuario), SUBNET_MASK))
                asignar_subred(usuario, f"subred_{type}5G_UE_AGF", obtener_subred_unica(obtener_red(usuario, f"user_{type}5G_network"), obtener_subredes(usuario), SUBNET_MASK))
                asignar_subred(usuario, f"subred_{type}5G_AGF_core5G", obtener_subred_unica(obtener_red(usuario, f"user_{type}5G_network"), obtener_subredes(usuario), SUBNET_MASK))
                asignar_subred(usuario, f"subred_{type}5G_core5G_server", obtener_subred_unica(obtener_red(usuario, f"user_{type}5G_network"), obtener_subredes(usuario), SUBNET_MASK))

                resultado = apply_terraform_5G(usuario, usuario.username, core, type)

                if resultado:
                    mensaje = f"Error al crear la red {type}5G"
                    return redirect(f'/network-list?mensaje={mensaje}')
                else:
                    asignar_flag_red(usuario, type)
                    mensaje = f"Red {type}5G creada correctamente"
                    
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

                    return redirect(f'/network-list?mensaje={mensaje}')
            

            elif IsGen:

                assigned_nets = list(UserNetwork.objects.values_list('network_cidr', flat=True))
                red_unica = obtener_subred_unica(BASE_CIDR, assigned_nets, NET_MASK)
                asignar_red_usuario(usuario, red_unica, "user_gen_mgmt_network")

                assigned_nets = list(UserNetwork.objects.values_list('network_cidr', flat=True))
                red_unica = obtener_subred_unica(BASE_CIDR, assigned_nets, NET_MASK)
                asignar_red_usuario(usuario, red_unica, "user_gen_network")

                asignar_subred(usuario, "subred_gen", obtener_subred_unica(obtener_red(usuario, "user_gen_network"), obtener_subredes(usuario), SUBNET_MASK))
                asignar_subred(usuario, "subred_gen_mgmt", obtener_subred_unica(obtener_red(usuario, "user_gen_mgmt_network"), obtener_subredes(usuario), SUBNET_MASK))

                resultado = apply_terraform_gen(usuario, usuario.username) 

                if resultado:
                    mensaje = "Error al crear la red genérica"
                    return redirect(f'/network-list?mensaje={mensaje}')
                else: 
                    asignar_flag_red(usuario, "gen")
                    mensaje = "Red genérica creada correctamente"

                    # Cargar la salida de Terraform
                    with open(f"terraform/{usuario.username}/terraform_outputs.json") as f:
                            data = json.load(f)

                    instance_mgmt_ip = data["instance_mgmt_ip"]["value"][0]
                    asignar_direccion_ip(usuario, instance_mgmt_ip, "instance_mgmt_ip")

                    broker_mgmt_ip = data["broker_gen_mgmt_ip"]["value"]
                    asignar_direccion_ip(usuario, broker_mgmt_ip, "broker_gen_mgmt_ip")

                    return redirect(f'/network-list?mensaje={mensaje}')

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
        return redirect('/network-list')

def apply_terraform_gen(usuario, username):
    user_dir = os.path.join("terraform", username)
    os.makedirs(user_dir, exist_ok=True)

    main_tf_path = os.path.join(user_dir, "main.tf")

    append_section = append_section_gen(username, 
                                       obtener_subred_por_nombre(usuario, f"subred_gen"), 
                                       obtener_subred_por_nombre(usuario, f"subred_gen_mgmt"), 
                                       get_gateway(obtener_subred_por_nombre(usuario, f"subred_gen_mgmt")),
                                       SSH_password.objects.get(user=usuario).ssh_password
                                       )
    with open(main_tf_path, "a") as f:
        f.write(append_section)
    
    resultado = terraform_apply_output(username)

    if resultado:

        #Eliminar las redes
        eliminar_red_usuario(usuario, "user_gen_mgmt_network")
        eliminar_red_usuario(usuario, "user_gen_network")

        #Eliminar las subredes
        eliminar_subred(usuario, "subred_gen")
        eliminar_subred(usuario, "subred_gen_mgmt")

        # Eliminar las IPs
        eliminar_direccion_ip(usuario, "instance_mgmt_ip")
        eliminar_direccion_ip(usuario, "broker_gen_mgmt_ip")
        return True
    else:   
        return False



def apply_terraform_5G(usuario, username, core_image, type):
    user_dir = os.path.join("terraform", username)
    os.makedirs(user_dir, exist_ok=True)

    main_tf_path = os.path.join(user_dir, "main.tf")

    append_section = append_section_5G(username, 
                                       obtener_subred_por_nombre(usuario, f"subred_{type}5G_UE_AGF"), 
                                       obtener_subred_por_nombre(usuario, f"subred_{type}5G_AGF_core5G"), 
                                       obtener_subred_por_nombre(usuario, f"subred_{type}5G_core5G_server"),
                                       obtener_subred_por_nombre(usuario, f"subred_{type}5G_mgmt"),
                                       get_gateway(obtener_subred_por_nombre(usuario, f"subred_{type}5G_mgmt")),
                                       core_image,
                                       type,
                                       SSH_password.objects.get(user=usuario).ssh_password
                                       )
    with open(main_tf_path, "a") as f:
        f.write(append_section)
    
    resultado = terraform_apply_output(username)
    
    if resultado:

        #Eliminar las redes
        eliminar_red_usuario(usuario, f"user_{type}5G_mgmt_network")
        eliminar_red_usuario(usuario, f"user_{type}5G_network")
            
        #Eliminar las subredese
        eliminar_subred(usuario, f"subred_{type}5G_UE_AGF")
        eliminar_subred(usuario, f"subred_{type}5G_AGF_core5G")
        eliminar_subred(usuario, f"subred_{type}5G_core5G_server")
        eliminar_subred(usuario, f"subred_{type}5G_mgmt")

        # Eliminar las IPs
        eliminar_direccion_ip(usuario, f"UE_{type}5G_mgmt_ip")
        eliminar_direccion_ip(usuario, f"AGF_{type}5G_mgmt_ip")
        eliminar_direccion_ip(usuario, f"core5G_{type}5G_mgmt_ip")
        eliminar_direccion_ip(usuario, f"server_{type}5G_mgmt_ip")
        eliminar_direccion_ip(usuario, f"broker_{type}5G_mgmt_ip")
        return True
    else:
        return False


@login_required
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
        return redirect('/network-list')

    with open(main_tf_path, "r") as f:
        content = f.read()

    append_section = append_section_5G(username, 
                                       obtener_subred_por_nombre(usuario, f"subred_{type}5G_UE_AGF"), 
                                       obtener_subred_por_nombre(usuario, f"subred_{type}5G_AGF_core5G"), 
                                       obtener_subred_por_nombre(usuario, f"subred_{type}5G_core5G_server"),
                                       obtener_subred_por_nombre(usuario, f"subred_{type}5G_mgmt"),
                                       get_gateway(obtener_subred_por_nombre(usuario, f"subred_{type}5G_mgmt")),
                                       core_image,
                                       type,
                                       SSH_password.objects.get(user=usuario).ssh_password
                                       )

    old_content = re.sub(re.escape(append_section), "", content)

    with open(main_tf_path, "w") as f:
        f.write(old_content)

    result = terraform_apply(usuario.username)
    print("result", result)

    if result == False:
       eliminar_flag_red(usuario, type)

       #Eliminar las redes
       eliminar_red_usuario(usuario, f"user_{type}5G_mgmt_network")
       eliminar_red_usuario(usuario, f"user_{type}5G_network")
        
       #Eliminar las subredes
       eliminar_subred(usuario, f"subred_{type}5G_UE_AGF")
       eliminar_subred(usuario, f"subred_{type}5G_AGF_core5G")
       eliminar_subred(usuario, f"subred_{type}5G_core5G_server")
       eliminar_subred(usuario, f"subred_{type}5G_mgmt")

       # Eliminar las IPs
       eliminar_direccion_ip(usuario, f"UE_{type}5G_mgmt_ip")
       eliminar_direccion_ip(usuario, f"AGF_{type}5G_mgmt_ip")
       eliminar_direccion_ip(usuario, f"core5G_{type}5G_mgmt_ip")
       eliminar_direccion_ip(usuario, f"server_{type}5G_mgmt_ip")
       eliminar_direccion_ip(usuario, f"broker_{type}5G_mgmt_ip")


       mensaje = f"Red {type}5G eliminada correctamente"
       return redirect(f'/network-list?mensaje={mensaje}')
    
    else :
       mensaje = f"Error al eliminar la red {type}5G, se ha restaurado la configuración anterior."
       return redirect(f'/network-list?mensaje={mensaje}')


@login_required
def delete_net_gen(request, flag):

    usuario = get_user(request)
    username = usuario.username
    user_dir = os.path.join("terraform", username)
    main_tf_path = os.path.join(user_dir, "main.tf")

    if not os.path.exists(main_tf_path):
        return redirect('/network-list')
    
    with open(main_tf_path, "r") as f:
        content = f.read()

    append_section = append_section_gen(username, 
                                       obtener_subred_por_nombre(usuario, f"subred_gen"), 
                                       obtener_subred_por_nombre(usuario, f"subred_gen_mgmt"), 
                                       get_gateway(obtener_subred_por_nombre(usuario, f"subred_gen_mgmt")),
                                       SSH_password.objects.get(user=usuario).ssh_password
                                       )
    
    old_content = re.sub(re.escape(append_section), "", content)

    with open(main_tf_path, "w") as f:
        f.write(old_content)

    result = terraform_apply(usuario.username)

    if result == False:
       eliminar_flag_red(usuario, "gen")

       #Eliminar las redes
       eliminar_red_usuario(usuario, "user_gen_mgmt_network")
       eliminar_red_usuario(usuario, "user_gen_network")

       #Eliminar las subredes
       eliminar_subred(usuario, "subred_gen")
       eliminar_subred(usuario, "subred_gen_mgmt")

       # Eliminar las IPs
       eliminar_direccion_ip(usuario, "instance_mgmt_ip")
       eliminar_direccion_ip(usuario, "broker_gen_mgmt_ip")
    
       mensaje = "Red genérica eliminada correctamente"
       return redirect(f'/network-list?mensaje={mensaje}')
    
    else :
       mensaje = f"Error al eliminar la red genérica, se ha restaurado la configuración anterior."
       return redirect(f'/network-list?mensaje={mensaje}')


@login_required
def view_net_5G(request, type):

    UE_mgmt_ip = obtener_direccion_ip(request.user, f"UE_{type}5G_mgmt_ip")
    AGF_mgmt_ip = obtener_direccion_ip(request.user, f"AGF_{type}5G_mgmt_ip")
    core5G_mgmt_ip = obtener_direccion_ip(request.user, f"core5G_{type}5G_mgmt_ip")
    server_mgmt_ip = obtener_direccion_ip(request.user, f"server_{type}5G_mgmt_ip")
    broker_mgmt_ip = obtener_direccion_ip(request.user, f"broker_{type}5G_mgmt_ip")
    
    
    string_type = type + "5G"
    context = {
        f'UE_{type}5G_mgmt_ip': UE_mgmt_ip,
        f'AGF_{type}5G_mgmt_ip': AGF_mgmt_ip,
        f'core5G_{type}5G_mgmt_ip': core5G_mgmt_ip,
        f'server_{type}5G_mgmt_ip': server_mgmt_ip,
        f'broker_{type}5G_mgmt_ip': broker_mgmt_ip,
        'type': string_type
    }

    return render(request, 'network.html', context)

@login_required
def view_net_gen(request):

    instance_mgmt_ip = obtener_direccion_ip(request.user, "instance_mgmt_ip")
    broker_mgmt_ip = obtener_direccion_ip(request.user, "broker_gen_mgmt_ip")
    
    context = {
        'instance_gen_mgmt_ip': instance_mgmt_ip,
        'broker_gen_mgmt_ip': broker_mgmt_ip,
        'type': "genérica"
    }

    return render(request, 'network.html', context)

