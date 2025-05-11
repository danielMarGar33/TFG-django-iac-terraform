import subprocess, os, shutil
import json
from django.shortcuts import render

#Ctrl K + C to comment the selected lines
#Ctrl K + U to uncomment the selected lines


# Sistema de seguridad para que en caso de error al crear una red, se pueda volver a intentarlo conservando la configuración ya creada

# Sistema de seguridad para que en caso de error al eliminar una red, se active el backup para volver al estado anterior, para que el usuario pueda volver a intentarlo
# Si no se consigue, no se elimina la red/fragmento de red de un error de creación, para poder volver a intentarlo

def backup_creation_terraform(username):
    destino = f"terraform/{username}_backup"

    # Verificar si el directorio de destino existe y eliminarlo
    if os.path.exists(destino):
        shutil.rmtree(destino)  # Elimina todo el directorio y su contenido

    # Realizar la copia del directorio completo usando xcopy
    subprocess.run(f'xcopy "terraform\\{username}" "{destino}" /E /I /Y', shell=True, check=True) 

def backup_restore_terraform(username):
    destino = f"terraform/{username}"

    # Verificar si el directorio de destino existe y eliminarlo
    if os.path.exists(destino):
        shutil.rmtree(destino)

    # Realizar la copia del directorio completo usando xcopy
    subprocess.run(f'xcopy "terraform\\{username}_backup" "{destino}" /E /I /Y', shell=True, check=True)


def terraform_apply(username):
    try:
        subprocess.run(f"cd terraform/{username} && terraform apply -auto-approve", shell=True, check=True)
        backup_creation_terraform(username)
        return False
   
    except Exception as e:
        print(f"Error al aplicar terraform: {e}")
        backup_restore_terraform(username)
        return True
    
    
def terraform_apply_output(username):
    try:
      subprocess.run(f"cd terraform/{username} && terraform apply -auto-approve && terraform output -json > terraform_outputs.json", shell=True, check=True)
      backup_creation_terraform(username)
      return False
    
    except Exception as e:
        print(f"Error applying terraform: {e}")
        return True


def terraform_init_apply(username):
    try:
      subprocess.run(f"cd terraform/{username} && terraform init -upgrade && terraform apply -auto-approve", shell=True, check=True)
      backup_creation_terraform(username) 
      return False

    except Exception as e:
      print(f"Error al aplicar terraform: {e}")
      return True


def terraform_destroy(username):
    try:
      subprocess.run(f"cd terraform/{username} && terraform destroy -auto-approve", check=True, shell=True)
      return False

    except Exception as e:
      print(f"Error al destruir terraform: {e}")
      return True


def terraform_template():
 return f"""
terraform {{
  required_version = ">= 1.3.0"

  required_providers {{
    openstack = {{
      source  = "terraform-provider-openstack/openstack"
      version = ">= 1.53.0"
    }}
  }}
}}


# Configurar el provider de openstack
provider "openstack" {{
  user_name   = "terraform"
  tenant_name = "terraform"
  password    = "!Terraform_rsti_2025"
  auth_url    = "http://138.4.21.62:5000/v3/"
  region      = "RegionOne"
}}
"""


def append_section_5G(username, subred_open_UE_AGF, subred_open_AGF_core5G, subred_open_core5G_server, subred_mgmt, gateway, core_image, type, password): 
 return f"""


# Configuracion de red de mgmt
# Creacion de la red interna
resource "openstack_networking_network_v2" "{username}_{type}5G_mgmt_network" {{
  name  = "{username}_{type}5G_mgmt_network"
  mtu   = 1400  
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}


# Creacion de la subred de mgmt
resource "openstack_networking_subnet_v2" "{username}_{type}5G_mgmt_subnetwork" {{
  name       = "{username}_{type}5G_mgmt_subnetwork"
  network_id = openstack_networking_network_v2.{username}_{type}5G_mgmt_network.id
  cidr       = "{subred_mgmt}"
  gateway_ip = "{gateway}"
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Configuracion del router para conectarse a las redes de gestion
resource "openstack_networking_router_v2" "{username}_{type}5G_mgmt_router" {{
  name                = "{username}_{type}5G_mgmt_router"
  external_network_id = "30157725-23a0-4b3e-bd6a-ebfc46c39cac" # ID de la red externa
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Conexion del router a la subred de mgmt 
resource "openstack_networking_router_interface_v2" "{username}_{type}5G_mgmt_router_interface" {{
  router_id = openstack_networking_router_v2.{username}_{type}5G_mgmt_router.id
  subnet_id = openstack_networking_subnet_v2.{username}_{type}5G_mgmt_subnetwork.id
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Crear IP flotante para el broker 
resource "openstack_networking_floatingip_v2" "{username}_{type}5G_mgmt_floating_ip" {{
  pool = "extnet" # Asigna una IP en el rango de direcciones que tenemos en la red externa
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Asociar la IP flotante a la instancia
resource "openstack_networking_floatingip_associate_v2" "{username}_{type}5G_mgmt_floating_ip_assoc" {{
  floating_ip = openstack_networking_floatingip_v2.{username}_{type}5G_mgmt_floating_ip.address
  port_id = openstack_compute_instance_v2.{username}_{type}5G_broker.network[0].port
}}


# Puerto para broker en la subred de mgmt
resource "openstack_networking_port_v2" "{username}_{type}5G_broker_port" {{
  name       = "{username}_{type}5G_broker_port"
  network_id = openstack_networking_network_v2.{username}_{type}5G_mgmt_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_{type}5G_mgmt_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Crear instancia del broker con dos interfaces de red
resource "openstack_compute_instance_v2" "{username}_{type}5G_broker" {{
  name      = "{username}_{type}5G_broker"
  image_id  = "db02fc5c-cacc-42be-8e5f-90f2db65cf7c"
  flavor_id = "101"
  user_data = <<-EOF
              #!/bin/bash             
              # Establecer la contrasena para el nuevo usuario (puedes cambiarla)
              echo "root:{password}" | chpasswd

              # Asegurarse de que el usuario pueda acceder a traves de SSH
              echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

              # Reiniciar el servicio SSH para que los cambios tomen efecto
              systemctl restart sshd
              EOF

network {{
    port = openstack_networking_port_v2.{username}_{type}5G_broker_port.id
  }}
timeouts {{
    create = "10m"
    delete = "10m"
  }}

}}


# Configuracion de red 5G
# Creacion de la red interna
resource "openstack_networking_network_v2" "{username}_{type}5G_network" {{
  name = "{username}_{type}5G_network"
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}


# Creacion de la subred 5G UE_AGF
resource "openstack_networking_subnet_v2" "{username}_UE_AGF_{type}5G_subnetwork" {{
  name       = "{username}_UE_AGF_{type}5G_subnetwork"
  network_id = openstack_networking_network_v2.{username}_{type}5G_network.id
  cidr       = "{subred_open_UE_AGF}"
  timeouts {{
    create = "10m"
    delete = "10m"
  }}

}}

# Creacion de la subred 5G AGF_core5G
resource "openstack_networking_subnet_v2" "{username}_AGF_core5G_{type}5G_subnetwork" {{
  name       = "{username}_AGF_core5G_{type}5G_subnetwork"
  network_id = openstack_networking_network_v2.{username}_{type}5G_network.id
  cidr       = "{subred_open_AGF_core5G}"
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Creacion de la subred 5G core5G_server
resource "openstack_networking_subnet_v2" "{username}_core5G_server_{type}5G_subnetwork" {{
  name       = "{username}_core5G_server_{type}5G_subnetwork"
  network_id = openstack_networking_network_v2.{username}_{type}5G_network.id
  cidr       = "{subred_open_core5G_server}"
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}


# Puerto para UE en la subred UE_AGF
resource "openstack_networking_port_v2" "{username}_UE_AGF_{type}5G_port" {{
  name       = "{username}_UE_AGF_{type}5G_port"
  network_id = openstack_networking_network_v2.{username}_{type}5G_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_UE_AGF_{type}5G_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Puerto para UE en la subred de mgmt
resource "openstack_networking_port_v2" "{username}_UE_mgmt_{type}5G_port" {{
  name       = "{username}_UE_mgmt_{type}5G_port"
  network_id = openstack_networking_network_v2.{username}_{type}5G_mgmt_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_{type}5G_mgmt_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Crear instancia del UE
resource "openstack_compute_instance_v2" "{username}_{type}5G_UE" {{
  name      = "{username}_{type}5G_UE"
  image_id  = "db02fc5c-cacc-42be-8e5f-90f2db65cf7c"
  flavor_id = "101"
  user_data = <<-EOF
            #!/bin/bash             
            # Establecer la contrasena para el nuevo usuario (puedes cambiarla)
            echo "root:{password}" | chpasswd

            # Asegurarse de que el usuario pueda acceder a traves de SSH
            echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

            # Reiniciar el servicio SSH para que los cambios tomen efecto
            systemctl restart sshd
            EOF
  network {{
    port = openstack_networking_port_v2.{username}_UE_AGF_{type}5G_port.id
  }}
  network {{
    port = openstack_networking_port_v2.{username}_UE_mgmt_{type}5G_port.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

#------------

# Puerto para AGF en la subred UE_AGF
resource "openstack_networking_port_v2" "{username}_AGF_UE_{type}5G_port" {{
  name       = "{username}_AGF_UE_{type}5G_port"
  network_id = openstack_networking_network_v2.{username}_{type}5G_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_UE_AGF_{type}5G_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Puerto para AGF en la subred AGF_core5G
resource "openstack_networking_port_v2" "{username}_AGF_core5G_{type}5G_port" {{
  name       = "{username}_AGF_core5G_{type}5G_port"
  network_id = openstack_networking_network_v2.{username}_{type}5G_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_AGF_core5G_{type}5G_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Puerto para AGF en la subred de mgmt
resource "openstack_networking_port_v2" "{username}_AGF_mgmt_{type}5G_port" {{
  name       = "{username}_AGF_mgmt_{type}5G_port"
  network_id = openstack_networking_network_v2.{username}_{type}5G_mgmt_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_{type}5G_mgmt_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Crear instancia del AGF
resource "openstack_compute_instance_v2" "{username}_{type}5G_AGF" {{
  name      = "{username}_{type}5G_AGF"
  image_id  = "db02fc5c-cacc-42be-8e5f-90f2db65cf7c"
  flavor_id = "101"
  user_data = <<-EOF
            #!/bin/bash             
            # Establecer la contrasena para el nuevo usuario (puedes cambiarla)
            echo "root:{password}" | chpasswd

            # Asegurarse de que el usuario pueda acceder a traves de SSH
            echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

            # Reiniciar el servicio SSH para que los cambios tomen efecto
            systemctl restart sshd
            EOF
  network {{
    port = openstack_networking_port_v2.{username}_AGF_UE_{type}5G_port.id
  }}
  network {{
    port = openstack_networking_port_v2.{username}_AGF_core5G_{type}5G_port.id
  }}
  network {{
    port = openstack_networking_port_v2.{username}_AGF_mgmt_{type}5G_port.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Puerto para core5G en la subred AGF_core5G
resource "openstack_networking_port_v2" "{username}_core5G_AGF_{type}5G_port" {{
  name       = "{username}_core5G_AGF_{type}5G_port"
  network_id = openstack_networking_network_v2.{username}_{type}5G_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_AGF_core5G_{type}5G_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Puerto para core5G en la subred de mgmt
resource "openstack_networking_port_v2" "{username}_core5G_mgmt_{type}5G_port" {{
  name       = "{username}_core5G_mgmt_{type}5G_port"
  network_id = openstack_networking_network_v2.{username}_{type}5G_mgmt_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_{type}5G_mgmt_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Puerto para core5G en la subred de internet
resource "openstack_networking_port_v2" "{username}_core5G_server_{type}5G_port" {{
  name       = "{username}_core5G_server_{type}5G_port"
  network_id = openstack_networking_network_v2.{username}_{type}5G_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_core5G_server_{type}5G_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Crear instancia del core5G
resource "openstack_compute_instance_v2" "{username}_{type}5G_core5G" {{
  name      = "{username}_{type}5G_core5G"
  image_id  = "{core_image}"
  flavor_id = "101"
  user_data = <<-EOF
            #!/bin/bash             
            # Establecer la contrasena para el nuevo usuario (puedes cambiarla)
            echo "root:{password}" | chpasswd

            # Asegurarse de que el usuario pueda acceder a traves de SSH
            echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

            # Reiniciar el servicio SSH para que los cambios tomen efecto
            systemctl restart sshd
            EOF
  network {{
    port = openstack_networking_port_v2.{username}_core5G_server_{type}5G_port.id
  }}
  network {{
    port = openstack_networking_port_v2.{username}_core5G_AGF_{type}5G_port.id
  }}
  network {{
    port = openstack_networking_port_v2.{username}_core5G_mgmt_{type}5G_port.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Puerto para el server en la subred de mgmt
resource "openstack_networking_port_v2" "{username}_server_mgmt_{type}5G_port" {{
  name       = "{username}_server_mgmt_{type}5G_port"
  network_id = openstack_networking_network_v2.{username}_{type}5G_mgmt_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_{type}5G_mgmt_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Puerto para el server en la subred de core5g
resource "openstack_networking_port_v2" "{username}_server_core5G_{type}5G_port" {{
  name       = "{username}_server_core5G_{type}5G_port"
  network_id = openstack_networking_network_v2.{username}_{type}5G_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_core5G_server_{type}5G_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Crear instancia del server 5G
resource "openstack_compute_instance_v2" "{username}_{type}5G_server" {{
  name      = "{username}_{type}5G_server"
  image_id  = "db02fc5c-cacc-42be-8e5f-90f2db65cf7c"
  flavor_id = "101"
  user_data = <<-EOF
            #!/bin/bash             
            # Establecer la contrasena para el nuevo usuario (puedes cambiarla)
            echo "root:{password}" | chpasswd

            # Asegurarse de que el usuario pueda acceder a traves de SSH
            echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

            # Reiniciar el servicio SSH para que los cambios tomen efecto
            systemctl restart sshd
            EOF
  network {{
    port = openstack_networking_port_v2.{username}_server_core5G_{type}5G_port.id
  }}
  network {{
    port = openstack_networking_port_v2.{username}_server_mgmt_{type}5G_port.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

output "UE_{type}5G_mgmt_ip" {{
  value = openstack_networking_port_v2.{username}_UE_mgmt_{type}5G_port.all_fixed_ips
}}
output "AGF_{type}5G_mgmt_ip" {{
  value = openstack_networking_port_v2.{username}_AGF_mgmt_{type}5G_port.all_fixed_ips
}}
output "core5G_{type}5G_mgmt_ip" {{
  value = openstack_networking_port_v2.{username}_core5G_mgmt_{type}5G_port.all_fixed_ips
}}
output "server_{type}5G_mgmt_ip" {{
  value = openstack_networking_port_v2.{username}_server_mgmt_{type}5G_port.all_fixed_ips
}}
output "broker_{type}5G_mgmt_ip" {{
  value = openstack_networking_floatingip_v2.{username}_{type}5G_mgmt_floating_ip.address
}}
output "UE_{type}5G_UE_ip" {{
  value = openstack_networking_port_v2.{username}_UE_AGF_{type}5G_port.all_fixed_ips
}}
output "AGF_{type}5G_UE_ip" {{
  value = openstack_networking_port_v2.{username}_AGF_UE_{type}5G_port.all_fixed_ips
}}
output "AGF_{type}5G_core5G_ip" {{
  value = openstack_networking_port_v2.{username}_AGF_core5G_{type}5G_port.all_fixed_ips
}}
output "core5G_{type}5G_AGF_ip" {{
  value = openstack_networking_port_v2.{username}_core5G_AGF_{type}5G_port.all_fixed_ips
}}
output "core5G_{type}5G_server_ip" {{
  value = openstack_networking_port_v2.{username}_core5G_server_{type}5G_port.all_fixed_ips
}}
output "server_{type}5G_core5G_ip" {{
  value = openstack_networking_port_v2.{username}_server_core5G_{type}5G_port.all_fixed_ips
}}


"""



def append_section_gen(username, subred_gen, gateway, password):
   return f"""

# Configuracion del router para conectarse a las redes de gestion
resource "openstack_networking_router_v2" "{username}_gen_router" {{
  name                = "{username}_gen_mgmt_router"
  external_network_id = "30157725-23a0-4b3e-bd6a-ebfc46c39cac" # ID de la red externa
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Conexion del router a la subred de mgmt 
resource "openstack_networking_router_interface_v2" "{username}_gen_router_interface" {{
  router_id = openstack_networking_router_v2.{username}_gen_router.id
  subnet_id = openstack_networking_subnet_v2.{username}_gen_subnetwork.id
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Crear IP flotante para el broker 
resource "openstack_networking_floatingip_v2" "{username}_gen_floating_ip" {{
  pool = "extnet" # Asigna una IP en el rango de direcciones que tenemos en la red externa
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Asociar la IP flotante a la instancia
resource "openstack_networking_floatingip_associate_v2" "{username}_gen_floating_ip_assoc" {{
  floating_ip = openstack_networking_floatingip_v2.{username}_gen_floating_ip.address
  port_id = openstack_compute_instance_v2.{username}_gen_instance.network[0].port
}}

# Creacion de la red Ampliada de Pruebas
resource "openstack_networking_network_v2" "{username}_gen_network" {{
  name = "{username}_gen_network"
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Creacion de la subred Ampliada de Pruebas
resource "openstack_networking_subnet_v2" "{username}_gen_subnetwork" {{
  name       = "{username}_gen_subnetwork"
  network_id = openstack_networking_network_v2.{username}_gen_network.id
  cidr       = "{subred_gen}"
  gateway_ip = "{gateway}"
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}


# Puerto para la instancia en la subred Ampliada de Pruebas
resource "openstack_networking_port_v2" "{username}_instance_gen_port" {{
  name       = "{username}_instance_gen_port"
  network_id = openstack_networking_network_v2.{username}_gen_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_gen_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Crear instancia Ampliada de Pruebas
resource "openstack_compute_instance_v2" "{username}_gen_instance" {{
  name      = "{username}_gen_instance"
  image_id  = "db02fc5c-cacc-42be-8e5f-90f2db65cf7c"
  flavor_id = "101"
  user_data = <<-EOF
            #!/bin/bash             
            # Establecer la contrasena para el nuevo usuario (puedes cambiarla)
            echo "root:{password}" | chpasswd

            # Asegurarse de que el usuario pueda acceder a traves de SSH
            echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

            # Reiniciar el servicio SSH para que los cambios tomen efecto
            systemctl restart sshd
            EOF
  network {{
    port = openstack_networking_port_v2.{username}_instance_gen_port.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}


output "instance_gen_ip" {{
  value = openstack_networking_port_v2.{username}_instance_gen_port.all_fixed_ips
}}
"""

## IMPORTANTE AÑADIR LAS VARIABLES DE ENTORNO ##
def terraform_import_all(request):
    types = ["free", "open"]  # Tipos para las barridas 5G
    username = request.user.username
    messages = []

    from .views import obtener_direccion_ip
    ip_gen = obtener_direccion_ip(request.user, "broker_gen_mgmt_ip")
    ip_open = obtener_direccion_ip(request.user, "broker_open5G_mgmt_ip")
    ip_free = obtener_direccion_ip(request.user, "broker_free5G_mgmt_ip")

    resources = [
        # Recursos genéricos
        {"type": "openstack_networking_router_v2", "name": f"{username}_gen_router", "id": get_resource_id("router", f"{username}_gen_mgmt_router", messages)},
        {"type": "openstack_networking_floatingip_v2", "name": f"{username}_gen_floating_ip", "id": get_resource_id("floatingip", ip_gen, messages, "gen")},
        {"type": "openstack_networking_network_v2", "name": f"{username}_gen_network", "id": get_resource_id("network", f"{username}_gen_network", messages)},
        {"type": "openstack_networking_subnet_v2", "name": f"{username}_gen_subnetwork", "id": get_resource_id("subnet", f"{username}_gen_subnetwork", messages)},
        {"type": "openstack_networking_port_v2", "name": f"{username}_instance_gen_port", "id": get_resource_id("port", f"{username}_instance_gen_port", messages)},
        {"type": "openstack_compute_instance_v2", "name": f"{username}_gen_instance", "id": get_resource_id("instance", f"{username}_gen_instance", messages)},
    ]

    # Recursos 5G con barridas para "free" y "open"
    for type in types:
        resources_5G = [
            {"type": "openstack_networking_network_v2", "name": f"{username}_{type}5G_mgmt_network", "id": get_resource_id("network", f"{username}_{type}5G_mgmt_network", messages)},
            {"type": "openstack_networking_subnet_v2", "name": f"{username}_{type}5G_mgmt_subnetwork", "id": get_resource_id("subnet", f"{username}_{type}5G_mgmt_subnetwork", messages)},
            {"type": "openstack_networking_router_v2", "name": f"{username}_{type}5G_mgmt_router", "id": get_resource_id("router", f"{username}_{type}5G_mgmt_router", messages)},
            {"type": "openstack_networking_floatingip_v2", "name": f"{username}_{type}5G_mgmt_floating_ip", "id": get_resource_id("floatingip", ip_open if type == "open" else ip_free, messages, f"{type}5G")},
            {"type": "openstack_compute_instance_v2", "name": f"{username}_{type}5G_broker", "id": get_resource_id("instance", f"{username}_{type}5G_broker", messages)},
            {"type": "openstack_networking_network_v2", "name": f"{username}_{type}5G_network", "id": get_resource_id("network", f"{username}_{type}5G_network", messages)},
            {"type": "openstack_networking_subnet_v2", "name": f"{username}_UE_AGF_{type}5G_subnetwork", "id": get_resource_id("subnet", f"{username}_UE_AGF_{type}5G_subnetwork", messages)},
            {"type": "openstack_networking_subnet_v2", "name": f"{username}_AGF_core5G_{type}5G_subnetwork", "id": get_resource_id("subnet", f"{username}_AGF_core5G_{type}5G_subnetwork", messages)},
            {"type": "openstack_networking_subnet_v2", "name": f"{username}_core5G_server_{type}5G_subnetwork", "id": get_resource_id("subnet", f"{username}_core5G_server_{type}5G_subnetwork", messages)},
            {"type": "openstack_networking_port_v2", "name": f"{username}_UE_AGF_{type}5G_port", "id": get_resource_id("port", f"{username}_UE_AGF_{type}5G_port", messages)},
            {"type": "openstack_networking_port_v2", "name": f"{username}_UE_mgmt_{type}5G_port", "id": get_resource_id("port", f"{username}_UE_mgmt_{type}5G_port", messages)},
            {"type": "openstack_compute_instance_v2", "name": f"{username}_{type}5G_UE", "id": get_resource_id("instance", f"{username}_{type}5G_UE", messages)},
            {"type": "openstack_networking_port_v2", "name": f"{username}_AGF_UE_{type}5G_port", "id": get_resource_id("port", f"{username}_AGF_UE_{type}5G_port", messages)},
            {"type": "openstack_networking_port_v2", "name": f"{username}_AGF_core5G_{type}5G_port", "id": get_resource_id("port", f"{username}_AGF_core5G_{type}5G_port", messages)},
            {"type": "openstack_networking_port_v2", "name": f"{username}_AGF_mgmt_{type}5G_port", "id": get_resource_id("port", f"{username}_AGF_mgmt_{type}5G_port", messages)},
            {"type": "openstack_compute_instance_v2", "name": f"{username}_{type}5G_AGF", "id": get_resource_id("instance", f"{username}_{type}5G_AGF", messages)},
            {"type": "openstack_networking_port_v2", "name": f"{username}_core5G_AGF_{type}5G_port", "id": get_resource_id("port", f"{username}_core5G_AGF_{type}5G_port", messages)},
            {"type": "openstack_networking_port_v2", "name": f"{username}_core5G_mgmt_{type}5G_port", "id": get_resource_id("port", f"{username}_core5G_mgmt_{type}5G_port", messages)},
            {"type": "openstack_networking_port_v2", "name": f"{username}_core5G_server_{type}5G_port", "id": get_resource_id("port", f"{username}_core5G_server_{type}5G_port", messages)},
            {"type": "openstack_compute_instance_v2", "name": f"{username}_{type}5G_core5G", "id": get_resource_id("instance", f"{username}_{type}5G_core5G", messages)},
            {"type": "openstack_networking_port_v2", "name": f"{username}_server_mgmt_{type}5G_port", "id": get_resource_id("port", f"{username}_server_mgmt_{type}5G_port", messages)},
            {"type": "openstack_networking_port_v2", "name": f"{username}_server_core5G_{type}5G_port", "id": get_resource_id("port", f"{username}_server_core5G_{type}5G_port", messages)},
            {"type": "openstack_compute_instance_v2", "name": f"{username}_{type}5G_server", "id": get_resource_id("instance", f"{username}_{type}5G_server", messages)},
        ]

        # Añadir los recursos 5G al listado general
        resources.extend(resources_5G)

    # Importar todos los recursos
    for resource in resources:
        if resource["id"] is not None:
            try:
                subprocess.run(f"cd terraform/{username} && terraform import {resource['type']}.{resource['name']} {resource['id']}", shell=True, check=True, stderr=subprocess.DEVNULL)
                messages.append(f"✅ Importado: {resource['name']} del tipo {resource['type']}  con éxito")
                print(f"✅ Importado: {resource['name']} del tipo {resource['type']}  con éxito")
            except subprocess.CalledProcessError as e:
                messages.append(f"⚠️ Recurso encontrado, pero ya está en el estado: {resource['name']} del tipo {resource['type']}") 
                print(f"⚠️ Recurso encontrado, pero ya está en el estado: {resource['name']} del tipo {resource['type']}")
    return render(request, "import_result.html", {"messages": messages})



def get_resource_id(resource_type, resource_name, messages, type=None):
    try:
        if resource_type == "network":
            cmd = f"openstack network show -f json {resource_name}"
        elif resource_type == "subnet":
            cmd = f"openstack subnet show -f json {resource_name}"
        elif resource_type == "router":
            cmd = f"openstack router show -f json {resource_name}"
        elif resource_type == "floatingip":
            cmd = f"openstack floating ip show -f json {resource_name}"
        elif resource_type == "instance":
            cmd = f"openstack server show -f json {resource_name}"
        elif resource_type == "port":
            cmd = f"openstack port show -f json {resource_name}"
        else:
            print(f"Tipo de recurso desconocido: {resource_type}")
            return None

        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
        data = json.loads(result.stdout)
        return data.get("id")

    except subprocess.CalledProcessError:
        if resource_type == "floatingip":
            messages.append(f"❌ No se encontró la IP flotante de la red {type}")
            print(f"❌ No se encontró la IP flotante de la red {type}")
        else:
            messages.append(f"❌ No se encontró el recurso {resource_name} del tipo {resource_type}")
            print(f"❌ No se encontró el recurso {resource_name} del tipo {resource_type}")
        return None
