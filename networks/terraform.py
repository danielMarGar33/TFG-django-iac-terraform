import subprocess, os, shutil

#Ctrl K + C to comment the selected lines
#Ctrl K + U to uncomment the selected lines


# Sistema de seguridad para que en caso de error al crear una red, se vuelva al estado anterior, mediante el backup, eliminando lo que se ha creado

# Sistema de seguridad para que en caso de error al eliminar una red, hayan 3 intentos 
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
    
    except subprocess.CalledProcessError as e:
        print(f"Error al aplicar terraform: {e}")
        backup_restore_terraform(username)
        return True

       
    
def terraform_apply_output(username):
    try:
      subprocess.run(f"cd terraform/{username} && terraform apply -auto-approve && terraform output -json > terraform_outputs.json", shell=True, check=True)
      backup_creation_terraform(username)
      return False
    
    except subprocess.CalledProcessError as e:
        print(f"Error applying terraform: {e}")
        backup_restore_terraform(username)
        return True


def terraform_init_apply_output(username):
  try:
    subprocess.run(f"cd terraform/{username} && terraform init -upgrade && terraform apply -auto-approve && terraform output -json > terraform_outputs.json", shell=True, check=True)
    backup_creation_terraform(username) 
  except subprocess.CalledProcessError as e:
    print(f"Error al aplicar terraform: {e}")
    terraform_init_apply_output(username)

def terraform_destroy(username):
  try:
    subprocess.run(f"cd terraform/{username} && terraform destroy -auto-approve", check=True, shell=True)
  except subprocess.CalledProcessError as e:
    print(f"Error al destruir terraform: {e}")
    terraform_destroy(username)


# def terraform_apply(username):
#      return 0

# def terraform_apply_output(username):
#      return 0

# def terraform_init_apply_output(username):
#      subprocess.run(f"cp terraform/terraform_outputs.json terraform/{username}", shell=True, check=True)
#      return 0

# def terraform_destroy(username):
#      return 0
    

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



def append_section_gen(username, subred_gen, subred_mgmt, gateway, password):
   return f"""

# Configuracion de red de mgmt
# Creacion de la red interna
resource "openstack_networking_network_v2" "{username}_gen_mgmt_network" {{
  name  = "{username}_gen_mgmt_network"
  mtu   = 1400  
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}


# Creacion de la subred de mgmt
resource "openstack_networking_subnet_v2" "{username}_gen_mgmt_subnetwork" {{
  name       = "{username}_gen_mgmt_subnetwork"
  network_id = openstack_networking_network_v2.{username}_gen_mgmt_network.id
  cidr       = "{subred_mgmt}"
  gateway_ip = "{gateway}"
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Configuracion del router para conectarse a las redes de gestion
resource "openstack_networking_router_v2" "{username}_gen_mgmt_router" {{
  name                = "{username}_gen_mgmt_router"
  external_network_id = "30157725-23a0-4b3e-bd6a-ebfc46c39cac" # ID de la red externa
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Conexion del router a la subred de mgmt 
resource "openstack_networking_router_interface_v2" "{username}_gen_mgmt_router_interface" {{
  router_id = openstack_networking_router_v2.{username}_gen_mgmt_router.id
  subnet_id = openstack_networking_subnet_v2.{username}_gen_mgmt_subnetwork.id
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Crear IP flotante para el broker 
resource "openstack_networking_floatingip_v2" "{username}_gen_mgmt_floating_ip" {{
  pool = "extnet" # Asigna una IP en el rango de direcciones que tenemos en la red externa
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Asociar la IP flotante a la instancia
resource "openstack_networking_floatingip_associate_v2" "{username}_gen_mgmt_floating_ip_assoc" {{
  floating_ip = openstack_networking_floatingip_v2.{username}_gen_mgmt_floating_ip.address
  port_id = openstack_compute_instance_v2.{username}_gen_broker.network[0].port
}}


# Puerto para broker en la subred de mgmt
resource "openstack_networking_port_v2" "{username}_gen_broker_port" {{
  name       = "{username}_gen_broker_port"
  network_id = openstack_networking_network_v2.{username}_gen_mgmt_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_gen_mgmt_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Crear instancia del broker con dos interfaces de red
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
    create = "10m"
    delete = "10m"
  }}

}}

# Creacion de la red generica
resource "openstack_networking_network_v2" "{username}_gen_network" {{
  name = "{username}_gen_network"
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Creacion de la subred generica
resource "openstack_networking_subnet_v2" "{username}_gen_subnetwork" {{
  name       = "{username}_gen_subnetwork"
  network_id = openstack_networking_network_v2.{username}_gen_network.id
  cidr       = "{subred_gen}"
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}


# Puerto para la instancia en la subred de mgmt
resource "openstack_networking_port_v2" "{username}_instance_mgmt_gen_port" {{
  name       = "{username}_instance_mgmt_gen_port"
  network_id = openstack_networking_network_v2.{username}_gen_mgmt_network.id
  fixed_ip {{
    subnet_id = openstack_networking_subnet_v2.{username}_gen_mgmt_subnetwork.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

# Puerto para la instancia en la subred generica
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

# Crear instancia generica
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
  network {{
    port = openstack_networking_port_v2.{username}_instance_mgmt_gen_port.id
  }}
  timeouts {{
    create = "10m"
    delete = "10m"
  }}
}}

output "instance_mgmt_ip" {{
  value = openstack_networking_port_v2.{username}_instance_mgmt_gen_port.all_fixed_ips
}}
output "broker_gen_mgmt_ip" {{
  value = openstack_networking_floatingip_v2.{username}_gen_mgmt_floating_ip.address
}}
output "instance_gen_ip" {{
  value = openstack_networking_port_v2.{username}_instance_gen_port.all_fixed_ips
}}
"""