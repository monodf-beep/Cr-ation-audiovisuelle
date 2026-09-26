#!/usr/bin/env bash
# Installation du studio video sur un VPS Ubuntu ou Debian (a lancer en root, une seule fois ;
# on peut le relancer sans risque pour mettre a jour).
#
#   curl -fsSL https://raw.githubusercontent.com/monodf-beep/cr-ation-audiovisuelle/claude/hyperframe-installation-o3hduz/ops/vps/installer.sh -o installer.sh
#   sudo MOT_DE_PASSE='un-mot-de-passe' bash installer.sh
#
# Variables (toutes facultatives sauf MOT_DE_PASSE) :
#   DOMAINE       adresse du studio ; par defaut <ip>.sslip.io, qui pointe deja vers le VPS
#   UTILISATEUR   identifiant de connexion au studio (defaut : franck)
#   PROJET        projet ouvert dans le Studio (defaut : 10_cern ; changer ensuite avec `studio-projet`)
#   DRIVE         dossier Google Drive des medias, au format rclone (defaut : drive:Videos)
#   BRANCHE       branche du depot (defaut : claude/hyperframe-installation-o3hduz)
#
# Ce que ca installe : Node 22, ffmpeg, git, rclone, Caddy (https automatique + mot de passe),
# les bibliotheques de Chrome, et quatre services : le Studio HyperFrames, le serveur
# d'enregistrement, et la synchronisation GitHub / Drive toutes les 3 minutes.
set -euo pipefail

[ "$(id -u)" = 0 ] || { echo "Lancer avec sudo."; exit 1; }
: "${MOT_DE_PASSE:?Indiquer MOT_DE_PASSE='...' devant la commande.}"
IP=$(curl -fsS4 https://api.ipify.org)
DOMAINE=${DOMAINE:-${IP//./-}.sslip.io}
UTILISATEUR=${UTILISATEUR:-franck}
PROJET=${PROJET:-10_cern}
DRIVE=${DRIVE:-drive:Videos}
BRANCHE=${BRANCHE:-claude/hyperframe-installation-o3hduz}
DEPOT_URL=https://github.com/monodf-beep/cr-ation-audiovisuelle.git
RACINE=/srv/studio
DEPOT=$RACINE/depot
HF=hyperframes@0.8.75

echo "== Paquets systeme"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -yq curl git ffmpeg ca-certificates gnupg debian-keyring debian-archive-keyring apt-transport-https ufw fuse3
if ! command -v node >/dev/null || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 22 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -yq nodejs
fi
command -v rclone >/dev/null || curl -fsSL https://rclone.org/install.sh | bash
if ! command -v caddy >/dev/null; then
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -q && apt-get install -yq caddy
fi
# Bibliotheques dont Chrome a besoin pour le Studio et les rendus.
npx --yes playwright@1.56.1 install-deps chromium

echo "== Utilisateur et depot"
id studio >/dev/null 2>&1 || useradd --system --create-home --home-dir /home/studio --shell /bin/bash studio
mkdir -p "$RACINE" /etc/studio
chown studio:studio "$RACINE"
if [ ! -d "$DEPOT/.git" ]; then
  sudo -u studio git clone -q --branch "$BRANCHE" "$DEPOT_URL" "$DEPOT"
else
  sudo -u studio git -C "$DEPOT" fetch -q origin "$BRANCHE" && sudo -u studio git -C "$DEPOT" merge -q --ff-only "origin/$BRANCHE" || true
fi
for p in 08_hyperframes 10_cern; do
  [ -f "$DEPOT/$p/package.json" ] && sudo -u studio bash -c "cd '$DEPOT/$p' && npm install --silent"
done
sudo -u studio npx --yes "$HF" browser ensure

cat > /etc/studio/studio.env <<EOF
DEPOT=$DEPOT
PROJET=$PROJET
DRIVE=$DRIVE
BRANCHE=$BRANCHE
HF=$HF
EOF

echo "== Services"
install -m 755 "$DEPOT/ops/vps/synchro.sh" /usr/local/bin/studio-synchro
cat > /usr/local/bin/studio-projet <<'EOF'
#!/usr/bin/env bash
# Change le projet ouvert dans le Studio : studio-projet 08_hyperframes
set -e
[ -n "$1" ] && [ -d "/srv/studio/depot/$1" ] || { echo "Usage : studio-projet <dossier du depot>"; ls /srv/studio/depot; exit 1; }
sed -i "s/^PROJET=.*/PROJET=$1/" /etc/studio/studio.env
systemctl restart studio-hf
echo "Le Studio ouvre maintenant $1."
EOF
chmod 755 /usr/local/bin/studio-projet

cat > /etc/systemd/system/studio-hf.service <<EOF
[Unit]
Description=Studio HyperFrames
After=network-online.target
[Service]
User=studio
EnvironmentFile=/etc/studio/studio.env
ExecStart=/bin/bash -c 'cd "\$DEPOT/\$PROJET" && exec npx --yes \$HF preview --foreground --no-open --port 3002 .'
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/studio-enregistrement.service <<EOF
[Unit]
Description=Studio : pages d'enregistrement et televersement des prises
After=network-online.target
[Service]
User=studio
EnvironmentFile=/etc/studio/studio.env
Environment=PORT=8090
ExecStart=/usr/bin/node $DEPOT/ops/vps/serveur-enregistrement.mjs
Restart=always
[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/studio-synchro.service <<EOF
[Unit]
Description=Studio : synchronisation GitHub et Google Drive
[Service]
Type=oneshot
User=studio
ExecStart=/usr/local/bin/studio-synchro
EOF
cat > /etc/systemd/system/studio-synchro.timer <<EOF
[Unit]
Description=Studio : synchronisation toutes les 3 minutes
[Timer]
OnBootSec=1min
OnUnitActiveSec=3min
[Install]
WantedBy=timers.target
EOF

echo "== Caddy (https + mot de passe)"
HASH=$(caddy hash-password --plaintext "$MOT_DE_PASSE")
cat > /etc/caddy/Caddyfile <<EOF
$DOMAINE {
	basic_auth {
		$UTILISATEUR $HASH
	}
	handle_path /enregistrement/* {
		request_body {
			max_size 4GB
		}
		reverse_proxy 127.0.0.1:8090
	}
	handle {
		reverse_proxy 127.0.0.1:3002 {
			header_up Host 127.0.0.1:3002
		}
	}
}
EOF

ufw allow OpenSSH >/dev/null; ufw allow 80,443/tcp >/dev/null; ufw --force enable >/dev/null

systemctl daemon-reload
systemctl enable --now studio-hf studio-enregistrement studio-synchro.timer
systemctl restart caddy studio-hf studio-enregistrement

echo
echo "Studio      : https://$DOMAINE/"
echo "Voix off    : https://$DOMAINE/enregistrement/$PROJET/enregistrer.html"
echo "Identifiant : $UTILISATEUR (mot de passe choisi)"
if ! sudo -u studio rclone listremotes | grep -q "^${DRIVE%%:*}:"; then
  echo
  echo "Derniere etape, une seule fois : relier Google Drive."
  echo "  sudo -u studio rclone config create ${DRIVE%%:*} drive scope=drive config_is_local=false"
  echo "puis suivre les indications (voir ops/vps/README.md)."
fi
