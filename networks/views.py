from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user
from .models import UserNetwork, UserSubnet
from .forms import NetworkForm
from .terraform import append_section_5G, terraform_template, broker_template_5G, broker_template_no5G
import subprocess, os, re, ipaddress

# Red base y tamano de subred
BASE_CIDR = "10.0.0.0/8"
NET_MASK = 16  # Cada usuario recibe una subred de 16 IPs
SUBNET_MASK = 24  # Para subdivisión adicional si es necesario


### FUNCIONES PARA GUARDAR DATOS EN BD ###

def asignar_red_usuario(usuario, red_cidr, ssh_password):
    """ Asigna una red principal a un usuario en la BD """
    UserNetwork.objects.update_or_create(user=usuario, defaults={"network_cidr": red_cidr}, ssh_password=ssh_password)

def obtener_red_usuario(usuario):
    """ Obtiene la red principal de un usuario """
    try:
        return UserNetwork.objects.get(user=usuario).network_cidr
    except UserNetwork.DoesNotExist:
        return None

def eliminar_red_usuario(usuario):
    """ Elimina la red principal del usuario """
    UserNetwork.objects.filter(user=usuario).delete()

    subprocess.run(f"cd terraform/{usuario.username} && terraform destroy -auto-approve", shell=True)
    subprocess.run("cd ../..", shell=True)

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
    UserSubnet.objects.filter(user=usuario, name=nombre_subred).delete()


### FUNCIONES DE LÓGICA ###

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
    print(f"Usuario en create_initial_config: {usuario} ({type(usuario)})")

    if not UserNetwork.objects.filter(user=usuario).exists():
        assigned_nets = list(UserNetwork.objects.values_list('network_cidr', flat=True))
        print(f"Redes asignadas: {assigned_nets}")
        red_unica = obtener_subred_unica(BASE_CIDR, assigned_nets, NET_MASK)
        print(request)
        asignar_red_usuario(usuario, red_unica, request.session.get('ssh_password'))

        subred_control = obtener_subred_unica(red_unica, [], SUBNET_MASK)
        asignar_subred(usuario, "subred_control", subred_control)

        terraform_config = terraform_template(usuario.username, subred_control, get_gateway(subred_control))

        #Anadir el broker no5G
        broker_no5G= broker_template_no5G(usuario.username, UserNetwork.objects.get(user=usuario).ssh_password) 
    
        user_dir = os.path.join(settings.BASE_DIR, "terraform", usuario.username)
        os.makedirs(user_dir, exist_ok=True)

        main_tf_path = os.path.join(user_dir, "main.tf")
        with open(main_tf_path, "w") as f:
            f.write(terraform_config)
            f.write("\n" + broker_no5G)

        subprocess.run(f"cd terraform/{usuario.username} && terraform init", shell=True, check=True)
        subprocess.run("cd ../..", shell=True)
        subprocess.run("ls -a", shell=True)

@login_required
def network_list(request):
    if not request.user.is_authenticated:
        return redirect('login')

    isNew = request.session.pop('isNew', False)  
    if isNew:
        create_initial_config(request)

    creada_red_5G = request.session.get('creada_red_5G', False)
    creada_red_gen = request.session.get('creada_red_gen', False)

    context = {
        'creada_red_5G': creada_red_5G,
        'creada_red_gen': creada_red_gen
    }

    return render(request, 'network_list.html', context)

@login_required
def create_network(request):
    usuario = get_user(request)

    if request.method == 'POST':
        form = NetworkForm(request.POST)

        if form.is_valid():
            is5G = form.cleaned_data['opciones'] == 'opcion5G'

            if is5G:
                asignar_subred(usuario, "subred_UE_AGF", obtener_subred_unica(obtener_red_usuario(usuario), obtener_subredes(usuario), SUBNET_MASK))
                asignar_subred(usuario, "subred_AGF_core5G", obtener_subred_unica(obtener_red_usuario(usuario), obtener_subredes(usuario), SUBNET_MASK))
                asignar_subred(usuario, "subred_core5G_internet", obtener_subred_unica(obtener_red_usuario(usuario), obtener_subredes(usuario), SUBNET_MASK))

                apply_terraform_5G(usuario, usuario.username)
                request.session['creada_red_5G'] = True
                return redirect('/network-list')
            else:
                return redirect('/network-list')
        else:
            return render(request, 'create_network.html', {'form': form})

    else:
        form = NetworkForm()
        return render(request, 'create_network.html', {'form': form})

def apply_terraform_5G(usuario, username):
    user_dir = os.path.join("terraform", username)
    os.makedirs(user_dir, exist_ok=True)

    main_tf_path = os.path.join(user_dir, "main.tf")

    #Eliminar el broker no5G para anadir el broker 5G
    broker_no5G= broker_template_no5G(usuario.username, UserNetwork.objects.get(user=usuario).ssh_password)
    broker_5G= broker_template_5G(usuario.username, UserNetwork.objects.get(user=usuario).ssh_password)

    append_section = append_section_5G(username, obtener_subred_por_nombre(usuario, "subred_UE_AGF"), obtener_subred_por_nombre(usuario, "subred_AGF_core5G"), obtener_subred_por_nombre(usuario, "subred_core5G_internet"))
    
    with open(main_tf_path, "r") as f:
        content = f.read()

    old_broker = re.sub(re.escape(broker_no5G), "", content)

    with open(main_tf_path, "w") as f:
        f.write(old_broker.strip())
        f.write("\n" + broker_5G)
        f.write("\n" + append_section)
    
    subprocess.run(f"cd terraform/{usuario.username} && terraform apply -auto-approve", shell=True, check=True)
    subprocess.run("cd ../..", shell=True)


@login_required
def delete_net_5G(request):
    usuario = get_user(request)
    username = usuario.username
    user_dir = os.path.join("terraform", username)
    main_tf_path = os.path.join(user_dir, "main.tf")

    if not os.path.exists(main_tf_path):
        return redirect('/network-list')

    with open(main_tf_path, "r") as f:
        content = f.read()

    append_section = append_section_5G(username, obtener_subred_por_nombre(usuario, "subred_UE_AGF"), obtener_subred_por_nombre(usuario, "subred_AGF_core5G"), obtener_subred_por_nombre(usuario, "subred_core5G_internet"))

    #Eliminar el broker 5G para anadir el broker no5G
    broker_no5G = broker_template_no5G(usuario.username, UserNetwork.objects.get(user=usuario).ssh_password)
    broker_5G = broker_template_5G(usuario.username, UserNetwork.objects.get(user=usuario).ssh_password)
    
    #Eliminar las subredes
    eliminar_subred(usuario, "subred_UE_AGF")
    eliminar_subred(usuario, "subred_AGF_core5G")
    eliminar_subred(usuario, "subred_core5G_internet")

    # Eliminar tanto el broker 5G como la sección adicional en una sola operación
    old_content = re.sub(re.escape(append_section), "", content)
    old_content = re.sub(re.escape(broker_5G), "", old_content).strip()

    # Escribir el nuevo contenido en el archivo
    with open(main_tf_path, "w") as f:
        f.write(old_content + "\n" + broker_no5G)
    
    subprocess.run(f"cd terraform/{usuario.username} && terraform apply -auto-approve", shell=True)
    subprocess.run("cd ../..", shell=True)

    request.session['creada_red_5G'] = False
    return redirect('/network-list')

@login_required
def delete_net_gen(request):
    return redirect('/network-list')