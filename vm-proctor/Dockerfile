FROM debian:bookworm-slim
USER root
WORKDIR /opt/oiproctor

RUN echo "resolvconf resolvconf/linkify-resolvconf boolean false" | debconf-set-selections
RUN apt-get update
RUN DEBIAN_FRONTEND="noninteractive" apt install -y python3-pip pssh nodejs dnsmasq supervisor resolvconf openssh-server sudo procps moreutils vim net-tools dnsutils less inetutils-ping telnet wget shellinabox nginx
RUN pip3 install python-pytun queuelib wsgiserver --break-system-packages

RUN echo 'server {\n listen 80 default_server;\n listen 443 ssl;\n ssl_certificate /opt/oiproctor/etc/https/fullchain.pem;\n ssl_certificate_key /opt/oiproctor/etc/https/privkey.pem;\n location ~ ^/(?:status|update) {\n proxy_redirect off;\n proxy_set_header host $host;\n proxy_set_header X-real-ip $remote_addr;\n proxy_set_header X-forward-for $proxy_add_x_forwarded_for;\n proxy_pass http://127.0.0.1:81$request_uri;\n }\n location ~ ^/(?:connect|send|recv) {\n proxy_redirect off;\n proxy_set_header host $host;\n proxy_set_header X-real-ip $remote_addr;\n proxy_set_header X-forward-for $proxy_add_x_forwarded_for;\n proxy_pass http://127.0.0.1:8088$request_uri;\n }\n location /admin {\n proxy_redirect off;\n proxy_set_header host $host;\n proxy_set_header X-real-ip $remote_addr;\n proxy_set_header X-forward-for $proxy_add_x_forwarded_for;\n proxy_pass http://127.0.0.1:4200$request_uri;\n } location / {\n return 444;\n }\n}' > /etc/nginx/sites-available/default

RUN ln -s /opt/oiproctor/bin/oiproctor /usr/local/bin/oiproctor

RUN echo 'addn-hosts=/opt/oiproctor/run/connections\naddn-hosts=/opt/oiproctor/run/alias\naddn-hosts=/opt/oiproctor/run/users\nserver=8.8.8.8' > /etc/dnsmasq.d/oiproctor
# Editting /etc/resolv.conf is done from supervisord.conf as it has to be done after docker has booted, because docker replaces /etc/resolv.conf and locks it

RUN useradd -m proctor -s /bin/bash && usermod -aG sudo proctor
RUN echo 'proctor ALL=NOPASSWD: ALL' > /etc/sudoers.d/proctor

ENTRYPOINT ["/usr/bin/supervisord", "-c", "/opt/oiproctor/etc/supervisord.conf"]
