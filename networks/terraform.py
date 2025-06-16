import subprocess, os, shutil
import json
from django.shortcuts import render
from django.conf import settings

# Sistema de seguridad para que en caso de error al crear una red, se pueda volver a intentarlo conservando la configuración ya creada

# Sistema de seguridad para que en caso de error al eliminar una red, se active el backup para volver al estado anterior, para que el usuario pueda volver a intentarlo
# Si no se consigue, no se elimina la red/fragmento de red de un error de creación, para poder volver a intentarlo

def backup_creation_terraform(username):
    origen = f"terraform/{username}"
    destino = f"terraform/{username}_backup"

    # Verificar si el directorio de destino existe y eliminarlo
    if os.path.exists(destino):
        shutil.rmtree(destino)

    # Copiar el directorio completo
    shutil.copytree(origen, destino)

def backup_restore_terraform(username):
    origen = f"terraform/{username}_backup"
    destino = f"terraform/{username}"

    # Verificar si el directorio de destino existe y eliminarlo
    if os.path.exists(destino):
        shutil.rmtree(destino)

    # Copiar el directorio completo
    shutil.copytree(origen, destino)


def terraform_apply(username):
    try:
        subprocess.run(f"cd terraform/{username} && terraform init -upgrade && terraform apply -auto-approve -parallelism=3", shell=True, check=True)
        backup_creation_terraform(username)
        return False
   
    except Exception as e:
        print(f"Error al aplicar terraform: {e}")
        backup_restore_terraform(username)
        return True
    
    
def terraform_apply_output(username):
    try:
      subprocess.run(f"cd terraform/{username} && terraform init -upgrade && terraform apply -auto-approve -parallelism=3 && terraform output -json > terraform_outputs.json", shell=True, check=True)
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
      subprocess.run(f"cd terraform/{username} && terraform init -upgrade && terraform destroy -auto-approve -parallelism=3", check=True, shell=True)
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


provider "openstack" {{
  user_name   = "{settings.OS_USERNAME}"
  tenant_name = "{settings.OS_PROJECT_NAME}"
  password    = "{settings.OS_PASSWORD}"
  auth_url    = "{settings.OS_AUTH_URL}"
  region      = "{settings.OS_REGION_NAME}"
  max_retries = 5
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
    create = "1m"
    delete = "1m"
  }}
}}


# Creacion de la subred de mgmt
resource "openstack_networking_subnet_v2" "{username}_{type}5G_mgmt_subnetwork" {{
  name       = "{username}_{type}5G_mgmt_subnetwork"
  network_id = openstack_networking_network_v2.{username}_{type}5G_mgmt_network.id
  cidr       = "{subred_mgmt}"
  gateway_ip = "{gateway}"
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Configuracion del router para conectarse a las redes de gestion
resource "openstack_networking_router_v2" "{username}_{type}5G_mgmt_router" {{
  name                = "{username}_{type}5G_mgmt_router"
  external_network_id = "30157725-23a0-4b3e-bd6a-ebfc46c39cac" # ID de la red externa
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Conexion del router a la subred de mgmt 
resource "openstack_networking_router_interface_v2" "{username}_{type}5G_mgmt_router_interface" {{
  router_id = openstack_networking_router_v2.{username}_{type}5G_mgmt_router.id
  subnet_id = openstack_networking_subnet_v2.{username}_{type}5G_mgmt_subnetwork.id
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Crear IP flotante para el broker 
resource "openstack_networking_floatingip_v2" "{username}_{type}5G_mgmt_floating_ip" {{
  pool = "extnet" # Asigna una IP en el rango de direcciones que tenemos en la red externa
  timeouts {{
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
  }}

}}


# Configuracion de red 5G
# Creacion de la red interna
resource "openstack_networking_network_v2" "{username}_{type}5G_network" {{
  name = "{username}_{type}5G_network"
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}


# Creacion de la subred 5G UE_AGF
resource "openstack_networking_subnet_v2" "{username}_UE_AGF_{type}5G_subnetwork" {{
  name       = "{username}_UE_AGF_{type}5G_subnetwork"
  network_id = openstack_networking_network_v2.{username}_{type}5G_network.id
  cidr       = "{subred_open_UE_AGF}"
  timeouts {{
    create = "1m"
    delete = "1m"
  }}

}}

# Creacion de la subred 5G AGF_core5G
resource "openstack_networking_subnet_v2" "{username}_AGF_core5G_{type}5G_subnetwork" {{
  name       = "{username}_AGF_core5G_{type}5G_subnetwork"
  network_id = openstack_networking_network_v2.{username}_{type}5G_network.id
  cidr       = "{subred_open_AGF_core5G}"
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Creacion de la subred 5G core5G_server
resource "openstack_networking_subnet_v2" "{username}_core5G_server_{type}5G_subnetwork" {{
  name       = "{username}_core5G_server_{type}5G_subnetwork"
  network_id = openstack_networking_network_v2.{username}_{type}5G_network.id
  cidr       = "{subred_open_core5G_server}"
  timeouts {{
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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
    create = "1m"
    delete = "1m"
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



def append_section_gen(username, gen_mgmt_subnetwork, gen_subnetwork, gateway, password):
   return f"""

# Configuracion del router para conectarse a las redes de gestion
resource "openstack_networking_router_v2" "{username}_gen_mgmt_router" {{
  name                = "{username}_gen_mgmt_router"
  external_network_id = "30157725-23a0-4b3e-bd6a-ebfc46c39cac" # ID de la red externa
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Conexion del router a la subred de mgmt 
resource "openstack_networking_router_interface_v2" "{username}_gen_mgmt_router_interface" {{
  router_id = openstack_networking_router_v2.{username}_gen_mgmt_router.id
  subnet_id = openstack_networking_subnet_v2.{username}_gen_mgmt_subnetwork.id
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Crear IP flotante para el broker 
resource "openstack_networking_floatingip_v2" "{username}_gen_floating_ip" {{
  pool = "extnet" # Asigna una IP en el rango de direcciones que tenemos en la red externa
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Asociar la IP flotante a la instancia
resource "openstack_networking_floatingip_associate_v2" "{username}_gen_floating_ip_assoc" {{
  floating_ip = openstack_networking_floatingip_v2.{username}_gen_floating_ip.address
  port_id = openstack_compute_instance_v2.{username}_gen_broker.network[0].port
}}

# Creacion de la red Ampliada de Pruebas
resource "openstack_networking_network_v2" "{username}_gen_network" {{
  name = "{username}_gen_network"
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Creacion de la subred Ampliada de Pruebas
resource "openstack_networking_subnet_v2" "{username}_gen_subnetwork" {{
  name       = "{username}_gen_subnetwork"
  network_id = openstack_networking_network_v2.{username}_gen_network.id
  cidr       = "{gen_subnetwork}"
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

#Creación de la red de gestion para la red Ampliada de Pruebas
resource "openstack_networking_network_v2" "{username}_gen_mgmt_network" {{
  name = "{username}_gen_mgmt_network"
  timeouts {{ 
    create = "1m"
    delete = "1m"  
  }}
}}

# Creacion de la subred de gestion para la red Ampliada de Pruebas
resource "openstack_networking_subnet_v2" "{username}_gen_mgmt_subnetwork" {{
  name       = "{username}_gen_mgmt_subnetwork" 
  network_id = openstack_networking_network_v2.{username}_gen_mgmt_network.id
  cidr       = "{gen_mgmt_subnetwork}"
  gateway_ip = "{gateway}"
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}


# Puerto para el broker en la subred Ampliada de Pruebas
resource "openstack_networking_port_v2" "{username}_gen_broker_port" {{
  name       = "{username}_gen_broker_port"
  network_id = openstack_networking_network_v2.{username}_gen_mgmt_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_gen_mgmt_subnetwork.id
  }}
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Crear el broker de la red Ampliada de Pruebas
resource "openstack_compute_instance_v2" "{username}_gen_broker" {{
  name      = "{username}_gen_broker"
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
    port = openstack_networking_port_v2.{username}_gen_broker_port.id
  }}
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Puerto para el controller en la subred Ampliada de Pruebas
resource "openstack_networking_port_v2" "{username}_gen_controller_port" {{
  name       = "{username}_gen_controller_port"
  network_id = openstack_networking_network_v2.{username}_gen_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_gen_subnetwork.id
  }}
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Puerto para el controller en la subred de gestion de la red Ampliada de Pruebas
resource "openstack_networking_port_v2" "{username}_gen_broker_controller_port" {{
  name       = "{username}_gen_broker_controller_port"
  network_id = openstack_networking_network_v2.{username}_gen_mgmt_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_gen_mgmt_subnetwork.id
  }}
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Crear el controller de la red Ampliada de Pruebas
resource "openstack_compute_instance_v2" "{username}_gen_controller" {{
  name      = "{username}_gen_controller"
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
    port = openstack_networking_port_v2.{username}_gen_broker_controller_port.id
  }}
  network {{
    port = openstack_networking_port_v2.{username}_gen_controller_port.id
  }}
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Puerto para el worker en la subred Ampliada de Pruebas
resource "openstack_networking_port_v2" "{username}_gen_worker_port" {{
  name       = "{username}_gen_worker_port"
  network_id = openstack_networking_network_v2.{username}_gen_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_gen_subnetwork.id
  }}
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Puerto para el worker en la subred de gestion de la red Ampliada de Pruebas
resource "openstack_networking_port_v2" "{username}_gen_broker_worker_port" {{
  name       = "{username}_gen_broker_worker_port"
  network_id = openstack_networking_network_v2.{username}_gen_mgmt_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_gen_mgmt_subnetwork.id
  }}
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

# Crear el worker de la red Ampliada de Pruebas
resource "openstack_compute_instance_v2" "{username}_gen_worker" {{
  name      = "{username}_gen_worker"
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
    port = openstack_networking_port_v2.{username}_gen_broker_worker_port.id
  }}
  network {{
    port = openstack_networking_port_v2.{username}_gen_worker_port.id
  }}
  timeouts {{
    create = "1m"
    delete = "1m"
  }}
}}

output "gen_broker_ip" {{
  value = openstack_networking_floatingip_v2.{username}_gen_floating_ip.address 
}}

output "gen_controller_ip" {{
  value = openstack_networking_port_v2.{username}_gen_broker_controller_port.all_fixed_ips
}}

output "gen_worker_ip" {{
  value = openstack_networking_port_v2.{username}_gen_broker_worker_port.all_fixed_ips
}}
"""


def terraform_check_existing_resources(request):
    types = ["free", "open"]
    username = request.user.username
    messages = []

    from .views import obtener_direccion_ip
    ip_gen = obtener_direccion_ip(request.user, "gen_broker_ip")
    ip_open = obtener_direccion_ip(request.user, "broker_open5G_mgmt_ip")
    ip_free = obtener_direccion_ip(request.user, "broker_free5G_mgmt_ip")

    resources = [
        {"type": "openstack_networking_router_v2", "name": f"{username}_gen_mgmt_router", "id": get_resource_id("router", f"{username}_gen_mgmt_router")},
        {"type": "openstack_networking_floatingip_v2", "name": f"{username}_gen_floating_ip", "id": get_resource_id("floatingip", ip_gen)},
        {"type": "openstack_networking_network_v2", "name": f"{username}_gen_network", "id": get_resource_id("network", f"{username}_gen_network")},
        {"type": "openstack_networking_subnet_v2", "name": f"{username}_gen_subnetwork", "id": get_resource_id("subnet", f"{username}_gen_subnetwork")},
        {"type": "openstack_networking_network_v2", "name": f"{username}_gen_mgmt_network", "id": get_resource_id("network", f"{username}_gen_mgmt_network")},
        {"type": "openstack_networking_subnet_v2", "name": f"{username}_gen_mgmt_subnetwork", "id": get_resource_id("subnet", f"{username}_gen_mgmt_subnetwork")},
        {"type": "openstack_networking_port_v2", "name": f"{username}_gen_broker_port", "id": get_resource_id("port", f"{username}_gen_broker_port")},
        {"type": "openstack_compute_instance_v2", "name": f"{username}_gen_broker", "id": get_resource_id("instance", f"{username}_gen_broker")},
        {"type": "openstack_networking_port_v2", "name": f"{username}_gen_broker_controller_port", "id": get_resource_id("port", f"{username}_gen_broker_controller_port")},
        {"type": "openstack_networking_port_v2", "name": f"{username}_gen_controller_port", "id": get_resource_id("port", f"{username}_gen_controller_port")},
        {"type": "openstack_compute_instance_v2", "name": f"{username}_gen_controller", "id": get_resource_id("instance", f"{username}_gen_controller")},
        {"type": "openstack_networking_port_v2", "name": f"{username}_gen_broker_worker_port", "id": get_resource_id("port", f"{username}_gen_broker_worker_port")},
        {"type": "openstack_networking_port_v2", "name": f"{username}_gen_worker_port", "id": get_resource_id("port", f"{username}_gen_worker_port")},
        {"type": "openstack_compute_instance_v2", "name": f"{username}_gen_worker", "id": get_resource_id("instance", f"{username}_gen_worker")},
    ]

    for type in types:
        ip = ip_open if type == "open" else ip_free
        resources_5G = [
            {"type": "openstack_networking_network_v2", "name": f"{username}_{type}5G_mgmt_network", "id": get_resource_id("network", f"{username}_{type}5G_mgmt_network")},
            {"type": "openstack_networking_subnet_v2", "name": f"{username}_{type}5G_mgmt_subnetwork", "id": get_resource_id("subnet", f"{username}_{type}5G_mgmt_subnetwork")},
            {"type": "openstack_networking_router_v2", "name": f"{username}_{type}5G_mgmt_router", "id": get_resource_id("router", f"{username}_{type}5G_mgmt_router")},
            {"type": "openstack_networking_floatingip_v2", "name": f"{username}_{type}5G_mgmt_floating_ip", "id": get_resource_id("floatingip", ip)},
            {"type": "openstack_compute_instance_v2", "name": f"{username}_{type}5G_broker", "id": get_resource_id("instance", f"{username}_{type}5G_broker")},
            {"type": "openstack_networking_network_v2", "name": f"{username}_{type}5G_network", "id": get_resource_id("network", f"{username}_{type}5G_network")},
            {"type": "openstack_networking_subnet_v2", "name": f"{username}_UE_AGF_{type}5G_subnetwork", "id": get_resource_id("subnet", f"{username}_UE_AGF_{type}5G_subnetwork")},
            {"type": "openstack_networking_subnet_v2", "name": f"{username}_AGF_core5G_{type}5G_subnetwork", "id": get_resource_id("subnet", f"{username}_AGF_core5G_{type}5G_subnetwork")},
            {"type": "openstack_networking_subnet_v2", "name": f"{username}_core5G_server_{type}5G_subnetwork", "id": get_resource_id("subnet", f"{username}_core5G_server_{type}5G_subnetwork")},
            {"type": "openstack_networking_port_v2", "name": f"{username}_UE_AGF_{type}5G_port", "id": get_resource_id("port", f"{username}_UE_AGF_{type}5G_port")},
            {"type": "openstack_networking_port_v2", "name": f"{username}_UE_mgmt_{type}5G_port", "id": get_resource_id("port", f"{username}_UE_mgmt_{type}5G_port")},
            {"type": "openstack_compute_instance_v2", "name": f"{username}_{type}5G_UE", "id": get_resource_id("instance", f"{username}_{type}5G_UE")},
            {"type": "openstack_networking_port_v2", "name": f"{username}_AGF_UE_{type}5G_port", "id": get_resource_id("port", f"{username}_AGF_UE_{type}5G_port")},
            {"type": "openstack_networking_port_v2", "name": f"{username}_AGF_core5G_{type}5G_port", "id": get_resource_id("port", f"{username}_AGF_core5G_{type}5G_port")},
            {"type": "openstack_networking_port_v2", "name": f"{username}_AGF_mgmt_{type}5G_port", "id": get_resource_id("port", f"{username}_AGF_mgmt_{type}5G_port")},
            {"type": "openstack_compute_instance_v2", "name": f"{username}_{type}5G_AGF", "id": get_resource_id("instance", f"{username}_{type}5G_AGF")},
            {"type": "openstack_networking_port_v2", "name": f"{username}_core5G_AGF_{type}5G_port", "id": get_resource_id("port", f"{username}_core5G_AGF_{type}5G_port")},
            {"type": "openstack_networking_port_v2", "name": f"{username}_core5G_mgmt_{type}5G_port", "id": get_resource_id("port", f"{username}_core5G_mgmt_{type}5G_port")},
            {"type": "openstack_networking_port_v2", "name": f"{username}_core5G_server_{type}5G_port", "id": get_resource_id("port", f"{username}_core5G_server_{type}5G_port")},
            {"type": "openstack_compute_instance_v2", "name": f"{username}_{type}5G_core5G", "id": get_resource_id("instance", f"{username}_{type}5G_core5G")},
            {"type": "openstack_networking_port_v2", "name": f"{username}_server_mgmt_{type}5G_port", "id": get_resource_id("port", f"{username}_server_mgmt_{type}5G_port")},
            {"type": "openstack_networking_port_v2", "name": f"{username}_server_core5G_{type}5G_port", "id": get_resource_id("port", f"{username}_server_core5G_{type}5G_port")},
            {"type": "openstack_compute_instance_v2", "name": f"{username}_{type}5G_server", "id": get_resource_id("instance", f"{username}_{type}5G_server")},
        ]
        resources.extend(resources_5G)

    # Agregar mensajes
    for resource in resources:
        if resource["id"]:
            messages.append(f"✅ Encontrado en OpenStack: {resource['name']} ({resource['type']}) → ID: {resource['id']}")
        elif resource["type"] == "openstack_networking_floatingip_v2":
            messages.append(f"❌ No se encontró la IP flotante: {resource['name']}")
        else:
            messages.append(f"❌ No encontrado: {resource['name']} ({resource['type']})")

    return render(request, "check_result.html", {"messages": messages})


def get_resource_id(resource_type, resource_name):
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
            return None

        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
        data = json.loads(result.stdout)
        return data.get("id")

    except subprocess.CalledProcessError:
        return None
