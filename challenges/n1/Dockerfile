# Empaqueta el laboratorio CTF UCC (ctf1) y sustituye sus flags por las de preCTF.
# Contexto principal: este repositorio. Contexto `lab`: carpeta ctf1.
# Este repositorio no duplica el código vulnerable del lab.

# syntax=docker/dockerfile:1.7
FROM php:8.2-apache

ENV DEBIAN_FRONTEND=noninteractive \
    DB_HOST=127.0.0.1 \
    DB_PORT=3306 \
    DB_USER=ctf_web \
    DB_PASS=ctf_web_pass \
    DB_ADMIN_USER=ctf_admin \
    DB_ADMIN_PASS=ctf_admin_pass \
    DB_NAME=ctf_login

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        mariadb-server \
        mariadb-client \
    && rm -rf /var/lib/apt/lists/* \
    && docker-php-ext-install mysqli \
    && a2enmod rewrite \
    && mkdir -p /var/run/mysqld \
    && chown mysql:mysql /var/run/mysqld

COPY --from=lab servidor_web/ /var/www/html/
COPY --from=lab mysql_ssh/init.sql /opt/init.sql
COPY challenges/n1/overlay/apply-flags.php /usr/local/bin/prectf-apply-flags.php

RUN mkdir -p /opt/prectf/templates \
    && cp /var/www/html/admin.php /opt/prectf/templates/admin.php \
    && cp /var/www/html/bucket/admin_notes.md /opt/prectf/templates/admin_notes.md \
    && cp /var/www/html/config/app.ini /opt/prectf/templates/app.ini

RUN printf '%s\n' \
    '<?php' \
    '$flag = getenv("PRECTF_FLAG_N1");' \
    'if ($flag !== false && $flag !== "") {' \
    '    echo "<div class=\"gc-alert gc-alert-success\" style=\"margin-bottom:24px;\">";' \
    '    echo "<span class=\"material-icons\">flag</span><div>";' \
    '    echo "<strong>Flag de entrenamiento preCTF (Nivel 1)</strong>";' \
    '    echo "<pre class=\"gc-code\">" . htmlspecialchars($flag, ENT_QUOTES, "UTF-8") . "</pre>";' \
    '    echo "<div>Valídala en el panel de preCTF, no en el scoreboard de la clase.</div>";' \
    '    echo "</div></div>";' \
    '}' \
    > /var/www/html/prectf_banner.php \
    && sed -i "s|ctf_render_header('dashboard', 'Dashboard');|ctf_render_header('dashboard', 'Dashboard');\nif (is_file(__DIR__ . '/prectf_banner.php')) { require __DIR__ . '/prectf_banner.php'; }|" \
        /var/www/html/dashboard.php

RUN printf '%s\n' \
    '#!/bin/bash' \
    'set -euo pipefail' \
    'mkdir -p /var/run/mysqld /home/admin /opt/prectf' \
    'chown mysql:mysql /var/run/mysqld' \
    'mysqld --user=mysql --datadir=/var/lib/mysql --bind-address=127.0.0.1 --socket=/var/run/mysqld/mysqld.sock &' \
    'for i in $(seq 1 40); do' \
    '  mysqladmin --socket=/var/run/mysqld/mysqld.sock ping --silent && break' \
    '  sleep 1' \
    'done' \
    'php /usr/local/bin/prectf-apply-flags.php || echo "prectf-flags: no se pudieron aplicar las banderas de entrenamiento"' \
    'exec apache2-foreground' \
    > /usr/local/bin/prectf-n1-entry.sh \
    && chmod +x /usr/local/bin/prectf-n1-entry.sh /usr/local/bin/prectf-apply-flags.php

RUN mysql_install_db --user=mysql --datadir=/var/lib/mysql \
    && mysqld --user=mysql --datadir=/var/lib/mysql --bind-address=127.0.0.1 --socket=/var/run/mysqld/mysqld.sock & \
      pid=$! \
    && for i in $(seq 1 40); do mysqladmin --socket=/var/run/mysqld/mysqld.sock ping --silent && break; sleep 1; done \
    && mysql --socket=/var/run/mysqld/mysqld.sock -u root < /opt/init.sql \
    && mysqladmin --socket=/var/run/mysqld/mysqld.sock shutdown \
    && wait "$pid" || true \
    && chown -R www-data:www-data /var/www/html \
    && chown -R mysql:mysql /var/lib/mysql

HEALTHCHECK --interval=15s --timeout=5s --start-period=25s --retries=5 \
    CMD curl -fsS http://127.0.0.1/index.php || exit 1

EXPOSE 80

ENTRYPOINT ["/usr/local/bin/prectf-n1-entry.sh"]
