# Requisitos

 - docker-compose

# Configuración

La mayor parte de la configuración se puede dejar tal como viene por defecto. Sin embargo, existen algunes elementos que conviene personalizar, y otros que para asegurar la seguridad del sistema se ha tomado la decisión de no darles valores por defecto por lo que es absolutamente necesario inicializarlos manualmente para poner el sistema en funcionamiento.

 - En el archivo *oiproctor/etc/config* conviene personalizar los siguientes tres campos:
   - *VM_DIALOG_TITLE* Título de que aparecerá en todas las ventanas emergentes que abra el vigilante en las máquinas virtuales de concursantes mediante el comando oiproctor
   - *CONTEST_SHORTNAME* Nombre identificador del concurso en CMS (campo "Name" en el panel de configuración del concurso en CMS)
   - *USERS* Listado de los nombres de usuario de CMS que participarán en el concurso, separados con espacios

 - *oiproctor/etc/https/* En este directorio deben colocarse los archivos fullchain.pem y privkey.pem correspondientes al certificado y la clave privada para proporcionarlos a nginx para configurar el acceso por HTTPS. Por defecto vienen unos archivos creados, que deben ser substituidos por los definitivos para no recibir la alerta de invalidez de los certificados cada vez que se accede

 - *oiproctor/etc/tunnel.pass* Este archivo contendrá la contraseña del tunel de comunicación entre el servidor vigilante y las máquinas de concursantes. Es la misma contraseña para todas las máquina virtuales de concursantes. Debe ser la misma contraseña que se defina en la variable PROCTOR_TUNNEL_PASSWORD de /etc/oisetup/profiles/. Por defecto vienen una definida, por seguridad debe cambiarse

 - *oiproctor/etc/oivm.key* Clave privada con la que conectarse por SSH a las máquinas virtuales de concursantes. Debe corresponderse con la clave pública almacenada en /home/oi/.ssh/authorized_keys en la máquina virtual de concursantes

 - *oiproctor/etc/proctor.pwd* Contraseña del usuario proctor. Si este archivo no existe, al iniciar el contenedor se generará uno automáticamente

 - *docker-compose* Por defecto el contenedor docker usa el puerto 443 (HTTPS). Este puerto podría estar ocupados por el sistema anfitrión del contenedor docker. En la sección *ports:* se puede redirigir el puerto del sistema anfitrión a un puerto del contenedor docker indicando el puerto del sistema anfitrión antes del puerto del contenedor docker, separados por dos puntos, por ejemplo "8443:443" para permitir conexiones al puerto 8443 en lugar de al puerto 443

# Instalación

Una vez configurado el sistema, se puede proceder a su instalación.

Desde el directorio donde está el archivo docker-compose.yml y oiproctor/, y una vez en él se debe ejecutar el siguiente comando:

`docker-compose build oiproctor`

# Uso

1. Iniciar el servidor vigilante desde el directorio donde está el archivo docker-compose.yml, mediante este comando:

`docker-compose up oiproctor``

2. Iniciar las máquina virtuales de concursantes

   1. En la parte superior de cada máquina virtual se muestra un identificador único.
   2. Una vez la máquina virtual se haya conectado al servidor vigilante el identificador único quedará substituido por la mitad final de la IP que le ha asignado el servidor vigilante

3. A medida que los/las concursantes vayan identificandose en el CMS, sus nombres de usuario aparecerán en verde en la página /status del servidor de vigilancia

4. A través de la página /admin, se accede a la terminal de control introduciendo como usuario *proctor* y como contraseña la que esté definida en el archivo oiproctor/etc/proctor.pwd. Una vez dentro, el comando *oiproctor* puede realizar diversas acciones de control sobre las máquina de concursantes. Ejecutando `oiproctor help` se pueden ver todas las acciones disponibles. Otros comandos disponibles: wget, telnet, netstat, ping, route, dig, less, vi, ps, top, ssh, scp, sudo, apt, ...

# Diagrama de funcionamiento

[Esquema de funcionamiento](https://docs.google.com/drawings/d/11dJ2KmpZ8IMGM4Ud3oZfOOmw3_iYrChvPEJQvGds194/preview)


-----


# Requirements

 - docker-compose

# Configuration

Most of the configuration can be left as is by default. However, there are some elements that it is advisable to customize, and others that, to ensure system security, have been decided not to be given default values, so it is absolutely necessary to initialize them manually to get the system up and running.


 - In the file oiproctor/etc/config, it is advisable to customize the following three fields:
   - *VM_DIALOG_TITLE* Title that will appear in all the pop-up windows that the proctor opens on the contestants' virtual machines through the oiproctor command
   - *CONTEST_SHORTNAME* Identifier name of the contest in CMS (the "Name" field in the contest configuration panel in CMS)
   - *USERS* List of CMS usernames that will participate in the contest, separated by spaces

 - *oiproctor/etc/https/ In this directory, the fullchain.pem and privkey.pem files corresponding to the certificate and private key must be placed to provide them to nginx to configure HTTPS access. By default, some created files come, which must be replaced by the definitive ones to avoid the certificate invalidity alert each time access is made

 - *oiproctor/etc/tunnel.pass This file will contain the password for the communication tunnel between the proctor server and the contestants' machines. It is the same password for all the contestants' virtual machines. It must be the same password that is defined in the PROCTOR_TUNNEL_PASSWORD variable of /etc/oisetup/profiles/. By default, one is defined, for security it must be changed

 - *oiproctor/etc/oivm.key Private key to connect via SSH to the contestants' virtual machines. It must correspond to the public key stored in /home/oi/.ssh/authorized_keys on the contestant's virtual machine

 - *oiproctor/etc/proctor.pwd Proctor user password. If this file does not exist, one will be automatically generated when the container starts

 - *docker-compose By default, the docker container uses port 443 (HTTPS). This port could be occupied by the host system of the docker container. In the ports: section, the host system port can be redirected to a docker container port by indicating the host system port before the docker container port, separated by a colon, for example "8443:443" to allow connections to port 8443 instead of port 443

# Installation

Once the system is configured, you can proceed with its installation.

From the directory where the docker-compose.yml file and oiproctor/ are located, and once in it, the following command must be executed:

p docker-compose build oiproctorp 

# Usage

1. Start the proctor server from the directory where the docker-compose.yml file is located, using this command:

`docker-compose up oiproctor`

2. Start the contestants' virtual machines

   1. At the top of each virtual machine, a unique identifier is displayed.
   2. Once the virtual machine has connected to the proctor server, the unique identifier will be replaced by the latter half of the IP assigned by the proctor server

3. As contestants identify themselves in the CMS, their usernames will appear in green on the /status page of the surveillance server

4. Through the /admin page, you access the control terminal by entering proctor as the user and the password defined in the oiproctor/etc/proctor.pwd file. Once inside, the oiproctor command can perform various control actions on the contestants' machines. Running oiproctor help you can see all available actions. Other available commands: wget, telnet, netstat, ping, route, dig, less, vi, ps, top, ssh, scp, sudo, apt, …

# Operation Diagram

[Scheme](https://docs.google.com/drawings/d/11dJ2KmpZ8IMGM4Ud3oZfOOmw3_iYrChvPEJQvGds194/preview)
