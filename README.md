# 📡 Framework para la creación de escenarios de red 5G

**Interfaz web para desplegar infraestructura en una nube privada OpenStack usando Terraform.**
Desarrollada con **Python/Django**, esta aplicación permite interactuar de forma sencilla con un cliente Terraform desde un entorno web.

---

## 🛠 Requisitos previos

Antes de ejecutar la aplicación, asegúrate de tener configurado correctamente el entorno.

### 🔐 Configuración del entorno OpenStack

Es necesario crear un archivo `.env` con las credenciales y parámetros de acceso a la API de OpenStack. Para facilitar esto, se incluyen los scripts:

* `load.env.sh` (Linux)
* `load-env.ps1` (Windows)

Dentro del archivo `.env`, define las siguientes variables de entorno:

```bash
OS_USERNAME=<tu_usuario>
OS_PROJECT_NAME=<nombre_del_proyecto>
OS_PASSWORD=<tu_contraseña>
OS_AUTH_URL=<url_de_autenticación>
OS_REGION_NAME=<región>
OS_USER_DOMAIN_NAME=<dominio_de_usuario>
OS_PROJECT_DOMAIN_NAME=<dominio_del_proyecto>
OS_IDENTITY_API_VERSION=<versión_api>
ENCRYPTION_KEY=<clave_secreta>
```

Estas variables permiten autenticarte frente a la nube OpenStack y asegurar las comunicaciones internas de la app.

---

## ⚙️ Herramientas necesarias

Para ejecutar correctamente la aplicación, necesitas tener instaladas las siguientes herramientas en tu sistema:

* **Python**
  Lenguaje base de la aplicación, necesario para ejecutar Django y los scripts asociados.

* **Django**
  Framework web utilizado para construir la interfaz gráfica y lógica de negocio. Se instala como paquete de Python.

* **Terraform**
  Herramienta principal de Infrastructure as Code (IaC) usada para definir y desplegar la infraestructura.

* **OpenStack CLI (`openstack`)**
  Cliente de línea de comandos para interactuar con la nube OpenStack (consultas, gestión de recursos, etc.).

Todas las dependencias de Python necesarias se encuentran detalladas en el archivo `requirements.txt`. Basta con ejecutar:

```bash
pip install -r requirements.txt
```
