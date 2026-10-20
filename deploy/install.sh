#!/usr/bin/env bash
# Déploiement autonome sous /bp-laposte/ sur olivier-comfaits.fr
# À exécuter en root sur le VPS OVH, depuis le dossier du projet.
set -euo pipefail

APP_DIR=/var/www/bp-laposte
DOMAIN=olivier-comfaits.fr

echo "=== Installation des dépendances ==="
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv nginx

echo "=== Copie de l'application ==="
mkdir -p "$APP_DIR"
rsync -a --exclude='data' --exclude='__pycache__' --exclude='.env' ./ "$APP_DIR/"
cd "$APP_DIR"
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt

echo "=== Fichier .env (clé IA) ==="
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Éditez $APP_DIR/.env et ajoutez XAI_API_KEY avant de continuer."
fi

echo "=== Service systemd ==="
cp deploy/posteplan.service /etc/systemd/system/
# Utiliser le venv
sed -i 's|ExecStart=/usr/bin/python3|ExecStart=/var/www/bp-laposte/.venv/bin/python|' /etc/systemd/system/posteplan.service
systemctl daemon-reload
systemctl enable posteplan
systemctl restart posteplan

echo "=== Nginx ==="
cp deploy/nginx-bp-laposte.conf /etc/nginx/snippets/bp-laposte.conf
# Inclure le snippet dans le server du domaine si pas déjà fait
if ! grep -q "bp-laposte.conf" /etc/nginx/sites-enabled/* 2>/dev/null; then
  echo "Ajoutez cette ligne dans le bloc server de $DOMAIN :"
  echo "    include snippets/bp-laposte.conf;"
fi
nginx -t && systemctl reload nginx

echo "=== Terminé ==="
echo "URL : https://$DOMAIN/bp-laposte/"
echo "Vérifiez : systemctl status posteplan"
