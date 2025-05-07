# TFG_django-iac-terraform
Interfaz Web para interactuar con un cliente Terraform, y instalar infraestructura en una nube privada de OpenStack. Desarrollada con Python/Django

Antes de iniciar, es necesario crear un archivo .env con la configuración para la cli de openstack. Necesario para la importar la configuración actual en caso de error

--> .env
OS_USERNAME=<Rellenar aquí>
OS_PROJECT_NAME=<Rellenar aquí>
OS_PASSWORD=<Rellenar aquí>
OS_AUTH_URL=<Rellenar aquí>
OS_REGION_NAME=RegionOne
OS_USER_DOMAIN_NAME=Default
OS_PROJECT_DOMAIN_NAME=Default
OS_IDENTITY_API_VERSION=3 


--> ejecutar   . .\load-env.ps1                                  