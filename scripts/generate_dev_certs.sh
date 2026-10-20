#!/usr/bin/env sh
# Certificats jetables de démonstration. Ne pas utiliser en production.
set -eu

# Prevent Git Bash from rewriting OpenSSL subject arguments such as /CN=...
# This environment variable is ignored by regular POSIX shells.
export MSYS_NO_PATHCONV=1

CERT_DIR="${1:-certs}"
mkdir -p "$CERT_DIR"
chmod 700 "$CERT_DIR"

openssl req -x509 -newkey rsa:3072 -nodes \
  -keyout "$CERT_DIR/ca.key" -out "$CERT_DIR/ca.crt" -days 30 -sha256 \
  -subj "/CN=Clinique Espoir Dev CA" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"

openssl req -new -newkey rsa:2048 -nodes \
  -keyout "$CERT_DIR/server.key" -out "$CERT_DIR/server.csr" \
  -subj "/CN=pharmacie"
cat > "$CERT_DIR/server.ext" <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:pharmacie,DNS:radiologie,DNS:localhost,IP:127.0.0.1
EOF
openssl x509 -req -in "$CERT_DIR/server.csr" \
  -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" -CAcreateserial \
  -out "$CERT_DIR/server.crt" -days 30 -sha256 -extfile "$CERT_DIR/server.ext"

for CLIENT in gateway ui probe; do
  openssl req -new -newkey rsa:2048 -nodes \
    -keyout "$CERT_DIR/$CLIENT-client.key" -out "$CERT_DIR/$CLIENT-client.csr" \
    -subj "/CN=clinique-$CLIENT"
  printf '%s\n' 'basicConstraints=critical,CA:FALSE' \
    'keyUsage=critical,digitalSignature,keyEncipherment' \
    'extendedKeyUsage=clientAuth' > "$CERT_DIR/$CLIENT-client.ext"
  openssl x509 -req -in "$CERT_DIR/$CLIENT-client.csr" \
    -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" -CAserial "$CERT_DIR/ca.srl" \
    -out "$CERT_DIR/$CLIENT-client.crt" -days 30 -sha256 -extfile "$CERT_DIR/$CLIENT-client.ext"
done

chmod 600 "$CERT_DIR"/*.key
printf 'Démo TLS générée dans %s. Utiliser ca.crt comme CA serveur et client.\n' "$CERT_DIR"
