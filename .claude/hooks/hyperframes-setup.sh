#!/bin/bash
# Prepare l'environnement HyperFrames au demarrage d'une session Claude Code web :
# ffmpeg, Chrome headless et confiance du proxy HTTPS pour Chrome (sinon les CDN
# comme GSAP ne se chargent pas pendant le rendu).
set -euo pipefail

# Uniquement dans les conteneurs distants ; en local, rien a faire.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v certutil >/dev/null 2>&1; then
  apt-get update -qq >/dev/null 2>&1 || true
  apt-get install -y -qq ffmpeg libnss3-tools >/dev/null 2>&1
fi

# Chrome lit ~/.pki/nssdb : on y ajoute la CA du proxy.
CA=/root/.ccr/agent-proxy-ca.crt
NSSDB="$HOME/.pki/nssdb"
if [ -f "$CA" ]; then
  mkdir -p "$NSSDB"
  certutil -d "sql:$NSSDB" -L >/dev/null 2>&1 || certutil -d "sql:$NSSDB" -N --empty-password
  certutil -d "sql:$NSSDB" -L -n ccr-agent-proxy >/dev/null 2>&1 \
    || certutil -d "sql:$NSSDB" -A -t "C,," -n ccr-agent-proxy -i "$CA"
fi

cd "$CLAUDE_PROJECT_DIR/08_hyperframes"
npx --yes hyperframes@0.8.75 browser ensure >/dev/null 2>&1
