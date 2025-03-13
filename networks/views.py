# views.py (Vista para manejar la creación de redes)
from django.shortcuts import render, redirect
from django.conf import settings
from .forms import NetworkForm
from .terraform import append_section_5G, terraform_template
import subprocess, os, re, ipaddress

# Red base y tamaño de subred
BASE_CIDR = "10.0.1.0/24"
NET_MASK = 27  # Cada usuario recibe una subred de 16 IPs
SUBNET_MASK = 29  # Para subdivisión adicional si es necesario

# Diccionarios globales para almacenar asignaciones
user_net_map = {}      # Usuario → Red /27
user_subnet_map = {}  # Usuario → Todas las subredes de usuario /29

# Subredes 5G y genéricas del usuario
subnet_5G = {}
subnet_gen = {}


#Elimina todas las redes del usuario
def delete_user_networks(username):
    # Elimina la red del usuario solo si existe en el diccionario
    if username in user_net_map:
        del user_net_map[username]

    # Elimina las subredes del usuario solo si existen en el diccionario
    if username in user_subnet_map:
        del user_subnet_map[username]

    # Elimina las subredes 5G del usuario solo si existe en el diccionario
    if username in subnet_5G:
        del subnet_5G[username]

    # Elimina las subredes genéricas del usuario solo si existe en el diccionario
    if username in subnet_gen:
        del subnet_gen[username]


#Genera una subred única que no haya sido asignada a partir de la red base, y las subredes que ya han sido asignadas.
def get_unique_subnet(base_cidr, assigned_subnets, subnet_mask):
    network = ipaddress.IPv4Network(base_cidr, strict=False)
    subnets = list(network.subnets(new_prefix=subnet_mask))
    
    for subnet in subnets:
        if str(subnet) not in assigned_subnets:
            assigned_subnets.add(str(subnet))
            return str(subnet)
    
    raise ValueError("No quedan subredes disponibles.")

def get_gateway(subnet_cidr):

    """ Devuelve la dirección IP del gateway de una subred """
    network = ipaddress.ip_network(subnet_cidr, strict=False)
    return str(network.network_address + 1)  # Primera IP válida como gateway

def create_initial_config(request):

    """Asigna una subred única a un usuario y la almacena en el mapeo."""
    global user_net_map, user_subnet_map

    assigned_nets = set(user_net_map.values())
    red_unica = get_unique_subnet(BASE_CIDR, assigned_nets, NET_MASK)
    user_net_map[request.user.username] = red_unica
    print (f"Esta es la red unica del usuario {red_unica}")

    # Verifica si el usuario tiene una lista de subredes en el diccionario
    if request.user.username not in user_subnet_map:
       user_subnet_map[request.user.username] = []  # Inicializa la lista si no existe

    assigned_subnets = set(user_subnet_map[request.user.username])
    subred_unica = get_unique_subnet(user_net_map[request.user.username], assigned_subnets, SUBNET_MASK)
    user_subnet_map[request.user.username].append(subred_unica)  # Agregar subred al usuario

    terraform_config = terraform_template(request.user.username, subred_unica, get_gateway(subred_unica))

    # Crear directorio específico para el usuario
    user_dir = os.path.join(settings.BASE_DIR, "terraform", request.user.username)
    os.makedirs(user_dir, exist_ok=True)
    
    main_tf_path = os.path.join(user_dir, "main.tf")
    with open(main_tf_path, "w") as f:
        f.write(terraform_config)



def network_list(request):
    if not request.user.is_authenticated:
        return redirect('login')

    isNew = request.session.pop('isNew', False)  
    if isNew:
        create_initial_config(request)

    # Obtener los valores desde la sesión y eliminarlos
    creada_red_5G = request.session.get('creada_red_5G', False)
    creada_red_gen = request.session.get('creada_red_gen', False)

    context = {
        'creada_red_5G': creada_red_5G,
        'creada_red_gen': creada_red_gen
    }

    return render(request, 'network_list.html', context)



def create_network(request):

    """Asigna una subred única para la red 5G del usuario y la almacena en el mapeo."""
    global user_subnetGEN_map, user_subnet5G_map

    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        form = NetworkForm(request.POST)

        if form.is_valid():
            is5G = form.cleaned_data['opciones'] == 'opcion5G'

            if is5G:
 
                assigned_subnets = set(user_subnet_map[request.user.username])
                subred_unica = get_unique_subnet(user_net_map[request.user.username], assigned_subnets, SUBNET_MASK)
                user_subnet_map[request.user.username].append(subred_unica)  # Agregar subred al usuario
                subnet_5G[request.user.username] = subred_unica
    

                apply_terraform_5G(request.user.username, subred_unica)
                request.session['creada_red_5G'] = True  # Guardar el estado en la sesión
                return redirect('/network-list')
            else:

                assigned_subnets = set(user_subnet_map[request.user.username])
                subred_unica = get_unique_subnet(user_net_map[request.user.username], assigned_subnets, SUBNET_MASK)
                user_subnet_map[request.user.username].append(subred_unica)  # Agregar subred al usuario
                subnet_gen[request.user.username] = subred_unica


                apply_terraform_gen(request.user.username, subred_unica)
                request.session['creada_red_gen'] = True  # Guardar el estado en la sesión
                return redirect('/network-list')
        else:
            return render(request, 'create_network.html', {'form': form})

    else:
        form = NetworkForm()
        return render(request, 'create_network.html', {'form': form})
    



# Función para crear la red 5G
def apply_terraform_5G(username, subred_unica):
    
    user_dir = os.path.join("terraform", username)
    os.makedirs(user_dir, exist_ok=True)
    
    main_tf_path = os.path.join(user_dir, "main.tf")

    append_section = append_section_5G(username, subred_unica)

    # Abrir el archivo en modo "append" para agregar contenido sin borrar lo anterior
    with open(main_tf_path, "a") as f:
        f.write("\n" + append_section)  # Se añade un salto de línea para separar bloques

    # Ejecutar Terraform Apply (simulado)
    subprocess.run("echo 'Ejecutando Apply de Terraform'", shell=True)



# Función para crear la red genérica
def apply_terraform_gen(username, subred_unica):

 return 0


# Función para eliminar la red 5G
def delete_net_5G(request):

    global user_subnet5G_map

    username = request.user.username
    user_dir = os.path.join("terraform", username)
    main_tf_path = os.path.join(user_dir, "main.tf")

    # Verifica si el archivo existe antes de intentar modificarlo
    if not os.path.exists(main_tf_path):
        print(f"El archivo {main_tf_path} no existe.")
        return

    # Lee el contenido actual del archivo
    with open(main_tf_path, "r") as f:
        content = f.read()

    # Usa la misma función que se usó para generar el contenido para eliminarlo
    append_section = append_section_5G(username, subnet_5G[request.user.username])
    user_subnet_map[request.user.username].remove(subnet_5G[request.user.username])
    del subnet_5G[request.user.username]

    # Elimina el contenido generado por `append_section_5G` utilizando re.sub
    new_content = re.sub(re.escape(append_section), "", content)

    # Sobrescribe el archivo con el contenido limpio
    with open(main_tf_path, "w") as f:
        f.write(new_content.strip())  # Limpiar líneas vacías extras

    print(f"Se eliminaron los recursos de {main_tf_path}")

    # Ejecutar Terraform Apply (simulado)
    subprocess.run("echo 'Ejecutando Apply de Terraform'", shell=True)
 
    request.session['creada_red_5G'] = False
    return redirect('/network-list')


# Función para eliminar la red genérica
def delete_net_gen(request):
 
 print(request)
 request.session['creada_red_gen'] = False
 return redirect('/network-list')
