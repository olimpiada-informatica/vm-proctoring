# Entorno

 - Estos scripts están configurados para ejecutarse en Xubuntu 22.04
 - Descargar la extensión oimoitor.xpi en /usr/lib/firefox-addons/distribution/extensions/
 - Para no mostrar las solicitudes de actualización del sistema, se recomienda ejecutar: `sudo bash -c 'echo "Hidden=true" >> /etc/xdg/autostart/update-notifier.desktop'`
 - Aplicaciones recomendadas: vim sublime-text idle3 clang code default-jdk geany firefox, más las extensiones ms-vscode.cpptools y ms-python.python de Code

# Configuración

 - Añadir el logo en /etc/oisetup/logos/
 - Crear o editar el perfil en /etc/oisetup/profiles/ A continuación, un ejemplo de perfil:
```
  CONTEST_NAME="OIE"         # Nombre del concurso, puramente informativo
  LOGO_PATH="oie.png"        # Debe ser un archivo PNG. El archivo debe estar ubicado en /etc/oisetup/logos/
  AVAILABLE_LOCALES="ca_ES es_ES en_US en_GB" # Idiomas de interfaz disponibles
  DEFAULT_LOCALE="ca_ES"     # Idioma predeterminado cuando el sistema se inicia
  PROCTOR_TUNNEL_URL="https://proctor.olimpiada-informatica.org" # URL donde se encuentra el proctor. Debe dejarse vacío para desactivarlo
  PROCTOR_TUNNEL_PASSWORD="" # Contraseña del túnel del proctor. Debe corresponderse con el archivo tunnel.pwd del servidor de vigilancia. Debe dejarse vacío para desactivar el túnel del proctor
  PROCTOR_USER="oi"          # Este usuario debe existir previamente
  PROCTOR_MONITOR=true       # Mostrar o no el final de la IP del túnel en la parte superior de la pantalla, y monitorizar el espacio de disco libre y la resolución de pantalla
  PROCTOR_DIFF_IGNORE=""     # Lista de archivos a ignorar al hacer diff en el directorio home del concursante. Es una RegExp
  GUEST_SESSION=true         # Habilitar sesión de invitado: todos los datos del concursante se eliminarán cuando cierren sesión
  DISABLE_SCREENLOCK=true    # Deshabilitar el bloqueo de pantalla, para que los usuarios no sean desconectados por inactividad. Muy recomendado si GUEST_SESSION está habilitado
  CONTEST_URL="https://concurso.olimpiada-informatica.org"
  PERSISTENT_STORAGE=true    # Crear un directorio en el directorio home del concursante donde puedan almacenar datos que no se eliminarán cuando cierren sesión
  PERSISTENT_EXTERNAL=true   # Almacenar los datos persistentes en un USB conectado
  PERSISTENT_DIRNAME="oie"   # Nombre del directorio de almacenamiento persistente en el home del concursante
  BOOKMARKS=("aprende.olimpiada-informatica.org" "Manuales") # Lista de marcadores para añadir a Firefox, deben ingresarse como pares de URL + Nombre
  BROWSER_EXTENSIONS="oimonitor"
  DNS_LOCKDOWN=true # Restringir o no el acceso a internet para que solo ciertas URLs estén disponibles (marcadores, sitio web del concurso, servidor del proctor, otros nombres de dominio o IPs en lista blanca
  DNS_LOCKDOWN_WHITELIST=""  # Lista de dominios o IPs explícitamente en lista blanca
  DNS_LOCKDOWN_INTERFACE=""  # Restringir el acceso a internet solo en esta interfaz de red
  APT_PACKAGES=""            # Paquetes APT adicionales para instalar
  PIP_PACKAGES=""            # Paquetes PIP adicionales para instalar
```

 - Ejecutar: `sudo oisetup <perfil>`
 - Para refrescar el perfil durante el concurso, sin borrar datos del concursante, ejecutarlo sin parámetros: `sudo oisetup`


-----


# Environment

 - These scripts are set up to run on Xubuntu 22.04
 - Download the extension oimoitor.xpi to /usr/lib/firefox-addons/distribution/extensions/
 - To avoid system update prompts, it is recommended to run: `sudo bash -c 'echo "Hidden=true" >> /etc/xdg/autostart/update-notifier.desktop'`
 - Recommended applications: vim sublime-text idle3 clang code default-jdk geany firefox, plus the Code extensions ms-vscode.cpptools and ms-python.python

# Setup

 - Add the logo in /etc/oisetup/logos/
 - Create or edit the profile in /etc/oisetup/profiles/ Here is an example of a profile:
```
  CONTEST_NAME="OIE"         # Name of the contest, purely informational
  LOGO_PATH="oie.png"        # It must be a PNG file. The file must be located in /etc/oisetup/logos/
  AVAILABLE_LOCALES="ca_ES es_ES en_US en_GB" # Available interface languages
  DEFAULT_LOCALE="ca_ES"     # Default languade when the system boots
  PROCTOR_TUNNEL_URL="https://proctor.oinf.es" # URL where the proctor is located. Must be left empty to disable it
  PROCTOR_TUNNEL_PASSWORD="" # Password of the proctor tunnel. Must march the contents of the file tunnel.pwd of the proctor server. Must be left empty to disable the proctor tunnel
  PROCTOR_USER="oi"          # This user must already exist
  PROCTOR_MONITOR=true       # Whether to display the ending of the tunnel IP at the top of the screen or not, and monitor available diskspace and screen resolution
  PROCTOR_DIFF_IGNORE=""     # List of files to ignore when diff-ing the contestant's home directory. It is a RegExp
  GUEST_SESSION=true         # Enable guest session: all contestant data will be removed when they log out
  DISABLE_SCREENLOCK=true    # Disable the screenlock, so users are not logged out for inactivity. Very much recommended if GUEST_SESSION is enabled
  CONTEST_URL="https://concurso.olimpiada-informatica.org"
  PERSISTENT_STORAGE=true    # Create a directory in the contestant's home directory where they can store data that will bot be deleted when they log out
  PERSISTENT_EXTERNAL=true   # Store the persistent data in a plugged in USB
  PERSISTENT_DIRNAME="oie"   # Name of the persistent storage directory in the contestant's home
  BOOKMARKS=("aprende.olimpiada-informatica.org" "Manuales") # List of bookmarks to add to Firefox, they must be entered as pairs of URL + Name
  BROWSER_EXTENSIONS="oimonitor"
  DNS_LOCKDOWN=true          # Whether to lock down internet access so only certain URLs are available (bookmarks, contest website, proctor server, other whitelisted domainnames or IPs
  DNS_LOCKDOWN_WHITELIST=""  # List of explicitly whitelisted domains or IPs
  DNS_LOCKDOWN_INTERFACE=""  # Lock internet access only on this network interface
  APT_PACKAGES=""            # Additional APT packages to install
  PIP_PACKAGES=""            # Additional PIP packages to install
```

 - Run: `sudo oisetup <perfil>`
 - To refresh the profile during the contest, without deleting contestant data, run it without parameters: `sudo oisetup`
