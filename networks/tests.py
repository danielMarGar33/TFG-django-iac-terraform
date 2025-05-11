import os
import shutil
import time
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.urls import reverse
from django.test import TestCase
from networks.models import UserNetwork, UserIP
import paramiko
from django.conf import settings


class UserNetworkFlowTest(TestCase):
    def test_full_flow(self):
        """Simula el flujo completo: registro, creación de red, acceso SSH y eliminación"""

        username = 'testuser'
        user_dir = os.path.join(settings.BASE_DIR, "terraform", username)
        backup_dir = os.path.join(settings.BASE_DIR, "terraform", f"{username}_backup")

        e = None  # Para capturar cualquier excepción
        try:
            
        # 1. Registrar un nuevo usuario
            register_response = self.client.post(reverse('register'), {
                'username': username,
                'password1': 'testpassword123',
                'password2': 'testpassword123'
            })
            self.assertEqual(register_response.status_code, 302)
            self.assertRedirects(register_response, reverse('network_list'))

            self.assertTrue(User.objects.filter(username=username).exists())
            user = User.objects.get(username=username)
            print("Usuario registrado exitosamente")

         # 2. Crear una red (sin reintentos)
            create_network_response = self.client.post(reverse('create_network'), {
                'opciones': 'opcion5G_free',
                'ssh_password': 'testpassword123'
            })
            self.assertEqual(create_network_response.status_code, 302)
            self.assertRedirects(create_network_response, reverse('network_list'))

            self.assertTrue(UserNetwork.objects.filter(user=user, name="user_free5G_mgmt_network").exists())
            print("Red verificada en la base de datos")

         # 3. Acceso por SSH (sin reintentos)
            broker = UserIP.objects.filter(user=user, name="broker_free5G_mgmt_ip").first()
            self.assertIsNotNone(broker, "No se encontró broker_free5G_mgmt_ip en la base de datos")
            broker_ip = broker.ip_address

            print("Esperando 20 segundos antes de intentar la conexión SSH")
            time.sleep(20)

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                print(f"Conexión SSH a {broker_ip}...")
                ssh.connect(
                    hostname=broker_ip,
                    username='root',
                    password='testpassword123',
                    timeout=10
                )
                print("Conexión SSH exitosa")

                stdin, stdout, stderr = ssh.exec_command('echo "Conexión SSH exitosa"')
                output = stdout.read().decode().strip()
                self.assertEqual(output, "Conexión SSH exitosa")
            finally:
                ssh.close()
                
            # 4. Eliminar la red (con reintentos basados en mensajes)
            print("Esperando 40 segundos antes de eliminar la red...")
            time.sleep(40)
            delete_network_url = reverse('delete_net_5G', args=['free', 'False'])

            max_retries = 3
            for attempt in range(1, max_retries + 1):
                response = self.client.post(delete_network_url, follow=True)
                storage = get_messages(response.wsgi_request)
                messages_list = [m.message for m in storage]

                error_detectado = any("Error al eliminar la red" in m for m in messages_list)

                if not error_detectado:
                    print(f"Red eliminada exitosamente en el intento {attempt}")
                    self.assertRedirects(response, reverse('network_list'))
                    break
                else:
                    print(f"Intento {attempt} fallido al eliminar la red. Mensaje: {messages_list}")
                    if attempt < max_retries:
                        time.sleep(5)
                    else:
                        self.fail("No se pudo eliminar la red después de 3 intentos.")

            # Verifica que la red fue eliminada
            self.assertFalse(UserNetwork.objects.filter(user=user, name="user_free5G_mgmt_network").exists())

        except Exception as ex:
            e = ex  # Guardar la excepción para el bloque finally
            raise  # Para que el test falle y se capture la excepción

        finally:
            # Limpieza de archivos temporales
            if os.path.exists(user_dir):
                shutil.rmtree(user_dir)
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)

            # Mostrar mensaje solo si falló
            if e:
                print("################################################################################")
                print("❌ Error en el flujo de prueba")
                print("❗ Por favor contacte con un administrador para limpiar su prueba en OpenStack.")
                print("################################################################################")
