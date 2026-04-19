# Requisitos

 - docker compose

# Instalación

Desde el directorio donde están el archivo `docker-compose.yml` y el directorio `oiproctor/`, crear un archivo `.env` que defina la configuración. Por ejemplo:
```
# Define el servidor DNS que usará el servidor vigilante, por defecto 8.8.8.8
NAME_SERVER=
# Contraseña del túnel de comunicación entre el servidor vigilante y las máquinas virtuales. Debe ser la misma que la variable `PROCTOR_TUNNEL_PASSWORD` en el perfil `/etc/oisetup/profiles/` de las máquina virtuales
TUNNEL_PASS=
# Clave privada para conectar por SSH con las máquinas virtuales
VM_SSH_PASS=
# Contraseña de acceso a la consola del servidor vigilante
OIPROCTOR_PASS=
# Título de la página de monitorización de usuarios
USERS_MONITOR_TITLE=
# Título en las ventanas emergentes generadas por `oiproctor` en las máquinas virtuales
VM_DIALOG_TITLE=
# Nombre corto del concurso en CMS
CMS_CONTEST_SHORTNAME=
# Nombres de usuario en CMS de los concursantes a monitorizar
CMS_USERS=
```

Desde el mismo directorio, ejecutar el siguiente comando:

`docker compose build oiproctor`

Este comando debe ejecutarse cada vez que se modifique el archivo `.env`

# Uso

1. Iniciar el servidor vigilante desde el directorio donde está el archivo `docker-compose.yml`, mediante este comando:

`docker compose up -d oiproctor`

2. Iniciar las máquina virtuales de concursantes

   1. En la parte superior de cada máquina virtual se muestra un identificador único.
   2. Una vez la máquina virtual se haya conectado al servidor vigilante el identificador único quedará substituido por la mitad final de la IP que le ha asignado el servidor vigilante

3. A medida que los/las concursantes vayan identificandose en el CMS, sus nombres de usuario aparecerán en verde en la página /status del servidor de vigilancia

4. A través de la página `/admin`, se accede a la terminal de control introduciendo como usuario *proctor* y como contraseña la que esté definida en el archivo oiproctor/etc/proctor.pwd. Una vez dentro, el comando *oiproctor* puede realizar diversas acciones de control sobre las máquina de concursantes. Ejecutando `oiproctor help` se pueden ver todas las acciones disponibles. Otros comandos disponibles en el sistema: wget, telnet, netstat, ping, route, dig, less, vi, ps, top, ssh, scp, sudo, apt, ...

5. A través de la página `/alerts` se pueden leer alertas de los sistemas de los concursantes.

# Detalles funcionales

 - Para asegurar la seguridad del sistema el valor por defecto de las contraseñas es aleatorio.

 - En el archivo *oiproctor/etc/config* contiene la configuración. Esta configuración puede ser sobreescrita por las variables de entorno y/o por `docker compose` mediante el archivo `.env`
   - *USERS_MONITOR_TITLE* Título de que aparecerá en la página del monitor de usuarios
   - *VM_DIALOG_TITLE* Título de que aparecerá en todas las ventanas emergentes que abra el vigilante en las máquinas virtuales de concursantes mediante el comando `oiproctor`
   - *CMS_CONTEST_SHORTNAME* Nombre identificador del concurso en CMS (campo "Name" en el panel de configuración del concurso en CMS)
   - *CMS_USERS* Listado de los nombres de usuario de CMS que participarán en el concurso, separados por espacios

 - *oiproctor/etc/https/* En este directorio deben colocarse los archivos `fullchain.pem` y `privkey.pem` correspondientes al certificado y la clave privada, para proporcionarlos a nginx para configurar el acceso por HTTPS. Por defecto vienen unos archivos creados, que opcionalmente deberían ser substituidos por los definitivos para no recibir la alerta de invalidez de los certificados cada vez que se accede

 - *oiproctor/etc/tunnel.pass* Este archivo contendrá la contraseña del tunel de comunicación entre el servidor vigilante y las máquinas de concursantes. Es la misma contraseña para todas las máquina virtuales de concursantes. Debe ser la misma contraseña que se defina en la variable `PROCTOR_TUNNEL_PASSWORD` de `/etc/oisetup/profiles/`. Por defecto se genera una aleatoria la primera vez que se inicia el sistema

 - *oiproctor/etc/oivm.key* Clave privada con la que conectarse por SSH a las máquinas virtuales de concursantes. Debe corresponderse con la clave pública almacenada en `/home/oi/.ssh/authorized_keys` en la máquina virtual de concursantes

 - *oiproctor/etc/proctor.pwd* Contraseña del usuario proctor. Si este archivo no existe, al iniciar el contenedor se generará uno automáticamente

 - *docker compose* Por defecto el contenedor docker usa el puerto 443 (HTTPS). Este puerto podría estar ocupado por otro servicio del sistema anfitrión. En la sección *ports:* de `docker-compose.yml` se puede redirigir el puerto del sistema anfitrión a un puerto del contenedor docker indicando el puerto del sistema anfitrión antes del puerto del contenedor docker, separados por dos puntos, por ejemplo "8443:443" para permitir conexiones al puerto 8443 en lugar de al puerto 443

 - Se puede detener el servidor vigilante en cualquier momento mediate este comando: `docker compose down oiproctor`

 - Si una máquina virtual se desconecta, al volver a conectarse (con la misma dirección MAC) el túnel mantendrá su IP asignada anteriormente. Si la máquina virtual se reinicia y cambia de dirección MAC, se le asignará otra IP.

 - Si durante el concurso se reinicia el servidor vigilante, se perderán todas las conexiones con las máquina virtuales y todas las asignaciones de IPs en el túnel. Las máquinas virtuales restablecerán automáticamente la conexión del túnel y se les asignará una nueva IP en el túnel.

 - El contenido del directorio `log` se conserva entre reinicios. La hora del sistema es UTC.

 - [Esquema de funcionamiento](https://docs.google.com/drawings/d/11dJ2KmpZ8IMGM4Ud3oZfOOmw3_iYrChvPEJQvGds194/preview)


-----


# Requirements

 - docker compose

# Installation

From the directory where the `docker-compose.yml` file and `oiproctor/` are located, create an `.env` file to define your settings. For example:
```
# Define the DNS server the proctoring server will use, by default 8.8.8.8
NAME_SERVER=
# Password for the communication tunnel between the proctoring server and the VMs. It must be the same as the variable `PROCTOR_TUNNEL_PASSWORD` in the VMs' `/etc/oisetup/profiles/`
TUNNEL_PASS=
# Private key to connect against the VMs through SSH
VM_SSH_PASS=
# Password to access the proctoring server's shell
OIPROCTOR_PASS=
# Title on the users monitor page
USERS_MONITOR_TITLE=
# Title on `oiproctor`'s popups in the VMs
VM_DIALOG_TITLE=
# Contest's shortname on CMS
CMS_CONTEST_SHORTNAME=
# Contest's CMS users to monitor
CMS_USERS=
```

From the same directory, the following command must be executed:

`docker compose build oiproctor`

This command must be run every time the `.env` file is modified.

# Usage

1. Start the proctor server from the directory where the docker-compose.yml file is located, using this command:

`docker compose up -d oiproctor` (the proctor server can be stopped at any time using this command: `docker compose down oiproctor` )

2. Start the contestants' virtual machines

   1. At the top of each virtual machine, a unique identifier is displayed.
   2. Once the virtual machine has connected to the proctor server, the unique identifier will be replaced by the latter half of the IP assigned by the proctor server

3. As contestants identify themselves in the CMS, their usernames will appear in green on the `/status` page of the surveillance server

4. Through the `/admin` page, you access the control terminal by entering proctor as the user and the password defined in the `oiproctor/etc/proctor.pwd` file. Once inside, the *oiproctor* command can perform various control actions on the contestants' machines. Running `oiproctor help` you can see all available actions. Other available commands in the system: wget, telnet, netstat, ping, route, dig, less, vi, ps, top, ssh, scp, sudo, apt, …

5. Through the `/alerts` page, you can receive alerts from the contestants' systems.

# Operational details

To ensure system security, all default passwords are set to random values.

 - In the file oiproctor/etc/config contains the settings. This settings can be overwriten with environmental variables and/or `docker compose`'s `.env` file.
   - *USERS_MONITOR_TITLE* Title on the users monitor page
   - *VM_DIALOG_TITLE* Title that will appear in all the pop-up windows that the proctor opens on the contestants' virtual machines through the oiproctor command
   - *CMS_CONTEST_SHORTNAME* Identifier name of the contest in CMS (the "Name" field in the contest configuration panel in CMS)
   - *CMS_USERS* List of CMS usernames that will participate in the contest, separated by spaces

 - *oiproctor/etc/https/* In this directory, the `fullchain.pem` and `privkey.pem` files corresponding to the certificate and private key must be placed to provide them to nginx to configure HTTPS access. By default it comes with a pair of file, which can be replaced by the definitive ones to avoid the certificate invalidity alert each time it is accessed

 - *oiproctor/etc/tunnel.pass* This file will contain the password for the communication tunnel between the proctor server and the contestants' machines. It is the same password for all the contestants' virtual machines. It must be the same password that is defined in the `PROCTOR_TUNNEL_PASSWORD` variable of `/etc/oisetup/profiles/`. By default, it will generate an automatic one on the first boot

 - *oiproctor/etc/oivm.key* Private key to connect via SSH to the contestants' virtual machines. It must correspond to the public key stored in `/home/oi/.ssh/authorized_keys` on the contestant's virtual machine

 - *oiproctor/etc/proctor.pwd* Proctor user password. If this file does not exist, one will be automatically generated when the container starts

 - *docker compose* By default, the docker container uses port 443 (HTTPS). This port could be occupied by the host system of the docker container. In the ports: section, the host system port can be redirected to a docker container port by indicating the host system port before the docker container port, separated by a colon, for example "8443:443" to allow connections to port 8443 instead of port 443

 - The watchdog server can be stopped at any time using this command: `docker compose down oiproctor`

 - If a virtual machine disconnects, when it reconnects (with the same MAC address) the tunnel will retain the IP previously assigned to it. If the virtual machine restarts and changes its MAC address, it will be assigned a different IP.

 - If during the contest the watchdog server restarts, all connections to the virtual machines and all IP allocations in the tunnel will be lost. The virtual machines will automatically reestablish the tunnel connection and will be assigned a new IP in the tunnel.

 - The contents of the `log` directory are preserved between reboots. The system's timezone is UTC.

 - [Functional scheme](https://docs.google.com/drawings/d/11dJ2KmpZ8IMGM4Ud3oZfOOmw3_iYrChvPEJQvGds194/preview)
