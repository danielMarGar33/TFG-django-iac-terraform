
terraform {
  required_version = ">= 0.14.0"
  required_providers {
    openstack = {
        source  = "terraform-provider-openstack/openstack"
         version = "~> 1.53.0"
    }
  }
}

# Configurar el provider de openstack
provider "openstack" {
  user_name   = "terraform"
  tenant_name = "terraform"
  password    = "!Terraform_rsti_2025"
  auth_url    = "http://138.4.21.62:5000/v3/"
  region      = "RegionOne"
}

######################
# Configuracion de red del user 
# Creacion de la red interna
resource "openstack_networking_network_v2" "Daniel_network" {
  name           = "Daniel_network"
  admin_state_up = true
}

# Creacion de la subred de control
resource "openstack_networking_subnet_v2" "Daniel_control_subnetwork" {
  name       = "Daniel_control_subnetwork"
  network_id = openstack_networking_network_v2.Daniel_network.id
  cidr       = "10.0.0.0/24"
  gateway_ip = "10.0.0.1"
  enable_dhcp = true
}

# Configuracion del router para conectarse a las redes de gestion
resource "openstack_networking_router_v2" "mgmt_router_Daniel" {
  name                = "mgmt_router_Daniel"
  admin_state_up      = true
  external_network_id = "30157725-23a0-4b3e-bd6a-ebfc46c39cac" # ID de la red externa
}

# Conexion del router a la subred de control del user 
resource "openstack_networking_router_interface_v2" "router_internal_interface" {
  router_id = openstack_networking_router_v2.mgmt_router_Daniel.id
  subnet_id = openstack_networking_subnet_v2.Daniel_control_subnetwork.id
}

# Crear IP flotante para el broker 
resource "openstack_networking_floatingip_v2" "floating_ip" {
  pool = "extnet" # Asigna una IP en el rango de direcciones que tenemos en la red externa
}

# Asociar la IP flotante a la instancia
resource "openstack_compute_floatingip_associate_v2" "server_floating_ip_assoc" {
  floating_ip = openstack_networking_floatingip_v2.floating_ip.address
  instance_id = openstack_compute_instance_v2.broker_Daniel.id
}
######################

# Puerto para broker en la subred de control
resource "openstack_networking_port_v2" "broker_control_port" {
  name       = "broker_control_port"
  network_id = openstack_networking_network_v2.Daniel_network.id
  fixed_ip {
    subnet_id = openstack_networking_subnet_v2.Daniel_control_subnetwork.id
    ip_address = "10.0.0.40"
  }
  timeouts {
    create = "10m"
    delete = "10m"
  }
}

# Crear instancia del broker con dos interfaces de red
resource "openstack_compute_instance_v2" "broker_Daniel" {
  name      = "broker_Daniel"
  image_id  = "db02fc5c-cacc-42be-8e5f-90f2db65cf7c"
  flavor_id = "101"
  user_data = <<-EOF
              #!/bin/bash
              # Deshabilitar el acceso SSH para el usuario root
              echo "PermitRootLogin no" >> /etc/ssh/sshd_config
              
              # Crear un nuevo usuario
              useradd -m Daniel
              
              # Establecer la contrasena para el nuevo usuario (puedes cambiarla)
              echo "Daniel:122334" | chpasswd
              usermod -aG sudo Daniel

              # Asegurarse de que el usuario pueda acceder a traves de SSH
              echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config
              echo "AllowUsers Daniel" >> /etc/ssh/sshd_config

              # Reiniciar el servicio SSH para que los cambios tomen efecto
              systemctl restart sshd
              EOF

network {
    port = openstack_networking_port_v2.broker_control_port.id
  }

}



# subred_UE_AGF = 10.0.1.0/24
# subred_AGF_core5G = 10.0.2.0/24
# subred_core5G_internet = 10.0.3.0/24


# Creacion de la subred 5G UE_AGF
resource "openstack_networking_subnet_v2" "Daniel_UE_AGF_subnetwork" {
  name       = "Daniel_UE_AGF_subnetwork"
  network_id = openstack_networking_network_v2.Daniel_network.id
  cidr       = "10.0.1.0/24"
  enable_dhcp = true

}

# Creacion de la subred 5G AGF_core5G
resource "openstack_networking_subnet_v2" "Daniel_AGF_core5G_subnetwork" {
  name       = "Daniel_AGF_core5G_subnetwork"
  network_id = openstack_networking_network_v2.Daniel_network.id
  cidr       = "10.0.2.0/24"
  enable_dhcp = true
}

# Creacion de la subred 5G core5G_internet
resource "openstack_networking_subnet_v2" "Daniel_core5G_internet_subnetwork" {
  name       = "Daniel_core5G_internet_subnetwork"
  network_id = openstack_networking_network_v2.Daniel_network.id
  cidr       = "10.0.3.0/24"
  gateway_ip = "10.0.3.1"
  enable_dhcp = true
}


# Puerto para UE en la subred UE_AGF
resource "openstack_networking_port_v2" "Daniel_UE_AGF_port" {
  name       = "Daniel_UE_AGF_port"
  network_id = openstack_networking_network_v2.Daniel_network.id
  fixed_ip {
    subnet_id = openstack_networking_subnet_v2.Daniel_UE_AGF_subnetwork.id
    ip_address = "10.0.1.30"
  }
  timeouts {
    create = "10m"
    delete = "10m"
  }
}

# Puerto para UE en la subred de control
resource "openstack_networking_port_v2" "Daniel_UE_control_port" {
  name       = "Daniel_UE_control_port"
  network_id = openstack_networking_network_v2.Daniel_network.id
  fixed_ip {
    subnet_id = openstack_networking_subnet_v2.Daniel_control_subnetwork.id
    ip_address = "10.0.0.30"
  }
  timeouts {
    create = "10m"
    delete = "10m"
  }
}

# Crear instancia del UE
resource "openstack_compute_instance_v2" "Daniel_UE" {
  name      = "Daniel_UE"
  image_id  = "db02fc5c-cacc-42be-8e5f-90f2db65cf7c"
  flavor_id = "101"
  user_data = <<-EOF
              #!/bin/bash

              # Obtener las IP fijas de los puertos de Terraform
              AGF_IP=${openstack_networking_port_v2.Daniel_UE_AGF_port.fixed_ip[0].ip_address}
              CONTROL_IP=${openstack_networking_port_v2.Daniel_UE_control_port.fixed_ip[0].ip_address}

              # Anadir las rutas con mayor prioridad
              ip route add 10.0.1.0/24 via $AGF_IP dev ens3 metric 50 #subred UE_AGF
              ip route add 10.0.0.0/24 via $CONTROL_IP dev ens4 metric 50 #subred control
              EOF
  network {
    port = openstack_networking_port_v2.Daniel_UE_AGF_port.id
  }

  network {
    port = openstack_networking_port_v2.Daniel_UE_control_port.id
  }

  depends_on = [
    openstack_networking_port_v2.Daniel_UE_AGF_port,
    openstack_networking_port_v2.Daniel_UE_control_port
  ]
}

#------------

# Puerto para AGF en la subred UE_AGF
resource "openstack_networking_port_v2" "Daniel_AGF_UE_port" {
  name       = "Daniel_AGF_UE_port"
  network_id = openstack_networking_network_v2.Daniel_network.id
  fixed_ip {
    subnet_id = openstack_networking_subnet_v2.Daniel_UE_AGF_subnetwork.id
    ip_address = "10.0.1.31"
  }
  timeouts {
    create = "10m"
    delete = "10m"
  }
}

# Puerto para AGF en la subred AGF_core5G
resource "openstack_networking_port_v2" "Daniel_AGF_core5G_port" {
  name       = "Daniel_AGF_core5G_port"
  network_id = openstack_networking_network_v2.Daniel_network.id
  fixed_ip {
    subnet_id = openstack_networking_subnet_v2.Daniel_AGF_core5G_subnetwork.id
    ip_address = "10.0.2.30"
  }
  timeouts {
    create = "10m"
    delete = "10m"
  }
}

# Puerto para AGF en la subred de control
resource "openstack_networking_port_v2" "Daniel_AGF_control_port" {
  name       = "Daniel_AGF_control_port"
  network_id = openstack_networking_network_v2.Daniel_network.id
  fixed_ip {
    subnet_id = openstack_networking_subnet_v2.Daniel_control_subnetwork.id
    ip_address = "10.0.0.50"
  }
  timeouts {
    create = "10m"
    delete = "10m"
  }
}

# Crear instancia del AGF
resource "openstack_compute_instance_v2" "Daniel_AGF" {
  name      = "Daniel_AGF"
  image_id  = "db02fc5c-cacc-42be-8e5f-90f2db65cf7c"
  flavor_id = "101"
  user_data = <<-EOF
              #!/bin/bash
              # Deshabilitar el acceso SSH para el usuario root
              echo "PermitRootLogin no" >> /etc/ssh/sshd_config
              
              # Crear un nuevo usuario
              useradd -m Daniel
              
              # Establecer la contrasena para el nuevo usuario (puedes cambiarla)
              echo "Daniel:122334" | chpasswd
              usermod -aG sudo Daniel

              # Asegurarse de que el usuario pueda acceder a traves de SSH
              echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config
              echo "AllowUsers Daniel" >> /etc/ssh/sshd_config

              # Reiniciar el servicio SSH para que los cambios tomen efecto
              systemctl restart sshd
              
              # Obtener las IP fijas de los puertos de Terraform
              UE_IP=${openstack_networking_port_v2.Daniel_UE_AGF_port.fixed_ip[0].ip_address}
              CONTROL_IP=${openstack_networking_port_v2.Daniel_AGF_control_port.fixed_ip[0].ip_address}
              CORE_IP=${openstack_networking_port_v2.Daniel_AGF_core5G_port.fixed_ip[0].ip_address}

              # Anadir las rutas con metricas
              ip route add 10.0.2.0/24 via $CORE_IP dev ens3 metric 100
              ip route add 10.0.1.0/24 via $UE_IP dev ens4 metric 200
              ip route add 10.0.0.0/24 via $CONTROL_IP dev ens5 metric 300
              
              sudo systemctl restart systemd-networkd
              EOF
  network {
    port = openstack_networking_port_v2.Daniel_AGF_UE_port.id
  }

  network {
    port = openstack_networking_port_v2.Daniel_AGF_core5G_port.id
  }

  network {
    port = openstack_networking_port_v2.Daniel_AGF_control_port.id
  }
}

#------------

# Puerto para core5G en la subred AGF_core5G
resource "openstack_networking_port_v2" "Daniel_core5G_AGF_port" {
  name       = "Daniel_core5G_AGF_port"
  network_id = openstack_networking_network_v2.Daniel_network.id
  fixed_ip {
    subnet_id = openstack_networking_subnet_v2.Daniel_AGF_core5G_subnetwork.id
    ip_address = "10.0.2.40"
  }
  timeouts {
    create = "10m"
    delete = "10m"
  }
}

# Puerto para core5G en la subred de control
resource "openstack_networking_port_v2" "Daniel_core5G_control_port" {
  name       = "Daniel_core5G_control_port"
  network_id = openstack_networking_network_v2.Daniel_network.id
  fixed_ip {
    subnet_id = openstack_networking_subnet_v2.Daniel_control_subnetwork.id
    ip_address = "10.0.0.60"
  }
  timeouts {
    create = "10m"
    delete = "10m"
  }
}

# Puerto para core5G en la subred de internet
resource "openstack_networking_port_v2" "Daniel_core5G_internet_port" {
  name       = "Daniel_core5G_internet_port"
  network_id = openstack_networking_network_v2.Daniel_network.id
  fixed_ip {
    subnet_id = openstack_networking_subnet_v2.Daniel_core5G_internet_subnetwork.id
    ip_address = "10.0.3.30"
  }
  timeouts {
    create = "10m"
    delete = "10m"
  }
}

# Crear instancia del core5G
resource "openstack_compute_instance_v2" "Daniel_core5G" {
  name      = "Daniel_core5G"
  image_id  = "db02fc5c-cacc-42be-8e5f-90f2db65cf7c"
  flavor_id = "101"
  user_data = <<-EOF
              #!/bin/bash
              # Deshabilitar el acceso SSH para el usuario root
              echo "PermitRootLogin no" >> /etc/ssh/sshd_config
              
              # Crear un nuevo usuario
              useradd -m Daniel
              
              # Establecer la contrasena para el nuevo usuario (puedes cambiarla)
              echo "Daniel:122334" | chpasswd
              usermod -aG sudo Daniel

              # Asegurarse de que el usuario pueda acceder a traves de SSH
              echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config
              echo "AllowUsers Daniel" >> /etc/ssh/sshd_config

              # Reiniciar el servicio SSH para que los cambios tomen efecto
              systemctl restart sshd
              
              # Obtener las IP fijas de los puertos de Terraform
              AGF_IP=${openstack_networking_port_v2.Daniel_core5G_AGF_port.fixed_ip[0].ip_address}
              CONTROL_IP=${openstack_networking_port_v2.Daniel_core5G_control_port.fixed_ip[0].ip_address}
              INTERNET_IP=${openstack_networking_port_v2.Daniel_core5G_internet_port.fixed_ip[0].ip_address}

              # Anadir las rutas con metricas
              ip route add 10.0.3.0/24 via $INTERNET_IP dev ens3 metric 50
              ip route add 10.0.2.0/24 via $AGF_IP dev ens4 metric 50
              ip route add 10.0.0.0/24 via $CONTROL_IP dev ens5 metric 50
              
              sudo systemctl restart systemd-networkd
              EOF
  network {
    port = openstack_networking_port_v2.Daniel_core5G_internet_port.id
  }
  network {
    port = openstack_networking_port_v2.Daniel_core5G_AGF_port.id
  }
  network {
    port = openstack_networking_port_v2.Daniel_core5G_control_port.id
  }
}

# # Configuracion del router para conectarse a internet
# resource "openstack_networking_router_v2" "mgmt_router_core5G_Daniel" {
#   name                = "mgmt_router_core5G_Daniel"
#   admin_state_up      = true
#   external_network_id = "30157725-23a0-4b3e-bd6a-ebfc46c39cac" # ID de la red externa
# }

# # Conexion del router a la red de internet 
# resource "openstack_networking_router_interface_v2" "router_internal_interface_core" {
#   router_id = openstack_networking_router_v2.mgmt_router_core5G_Daniel.id
#   subnet_id = openstack_networking_subnet_v2.Daniel_core5G_internet_subnetwork.id
# }

# # Crear IP flotante para el core5G
# resource "openstack_networking_floatingip_v2" "floating_ip_core" {
#   pool = "extnet" # Asigna una IP en el rango de direcciones que tenemos en la red externa
# }

# # Asociar la IP flotante a la instancia
# resource "openstack_compute_floatingip_associate_v2" "server_floating_ip_assoc_core" {
#   floating_ip = openstack_networking_floatingip_v2.floating_ip_core.address
#   instance_id = openstack_compute_instance_v2.core5G_Daniel.id
#}
