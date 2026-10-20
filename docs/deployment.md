# Déploiement sur un VPS avec Docker Compose

## Ce que contient le déploiement

- `pharmacie` et `radiologie` : serveurs gRPC, ports internes 50052 et 50053.
- Les deux serveurs exposent gRPC Health Checking avec état `SERVING`.
- `gateway` : passerelle REST FastAPI, port interne 8000, documentation OpenAPI
  à `/docs`.
- `ui` : tableau de bord Streamlit sur le port interne 8501.
- Les contrôles de santé Compose attendent que les serveurs gRPC répondent avant
  de lancer la passerelle et l'interface.

Les données restent des mocks en mémoire. La mise à jour de stock sert à la
démonstration et disparaît au redémarrage du conteneur. Ce déploiement ne doit
pas recevoir de données médicales réelles.

## Démarrage local ou démonstration sur VPS

1. Installer Docker Engine et le plugin Docker Compose sur le VPS.
2. Cloner le dépôt puis sélectionner la branche livrée :

   ```sh
   git clone --branch romuald-pharmacie-radiologie https://github.com/romualdKO/middlwareproject.git
   cd middlwareproject
   ```

3. Copier `.env.example` en `.env`, générer une clé API et la mettre dans `API_KEY` :

   ```sh
   cp .env.example .env
   python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
   ```

4. Configurer le pare-feu du VPS. Garder les ports gRPC, REST et UI liés à
   `127.0.0.1` pour les appels via un proxy sur le même hôte. Ouvrir au public
   seulement les ports 80/443 du proxy.
5. Construire et lancer :

   ```sh
   docker compose up --build -d --wait --wait-timeout 180
   docker compose ps
   docker compose logs -f gateway ui pharmacie radiologie
   ```

Accès local sur le VPS : `http://127.0.0.1:8000/docs` et
`http://127.0.0.1:8501`. Un reverse proxy TLS (Caddy, Nginx ou équivalent) peut
publier ces deux interfaces sous des noms DNS HTTPS. `/health/live` vérifie le
processus API et `/health/ready` vérifie aussi les deux services gRPC. Protéger
l'interface Streamlit par une authentification au reverse proxy ou un VPN avant
toute exposition hors réseau privé.

## Contrats HTTP pour systèmes externes

La passerelle publie OpenAPI sur `/openapi.json` et Swagger UI sur `/docs`.
Si `API_KEY` est renseignée, chaque route `/api/v1/*` exige l'en-tête
`X-API-Key`. La clé d'écriture `STOCK_WRITE_API_KEY` peut être distincte;
à défaut, la clé `API_KEY` protège aussi les requêtes `PUT`. Les endpoints de
santé restent accessibles au proxy.

```sh
curl -H "X-API-Key: $API_KEY" http://127.0.0.1:8000/api/v1/pharmacie/medicaments
curl -H "X-API-Key: $API_KEY" 'http://127.0.0.1:8000/api/v1/pharmacie/medicaments/MED001/stock?quantite_demandee=2'
curl -H "X-API-Key: $API_KEY" http://127.0.0.1:8000/api/v1/radiologie/patients/PAT001/examens
curl -X PUT -H "X-API-Key: ${STOCK_WRITE_API_KEY:-$API_KEY}" -H 'Content-Type: application/json' \
  -d '{"nouvelle_quantite":25}' \
  http://127.0.0.1:8000/api/v1/pharmacie/medicaments/MED001/stock
```

Un client gRPC externe utilise les contrats dans `proto/`, les stubs générés
dans `grpc_services/generated/`, les cibles DNS/ports publiées et un délai
borné. Les ports gRPC ne doivent pas être ouverts en clair sur Internet.

## TLS mutuel pour gRPC

`compose.tls.yaml` active TLS avec authentification mutuelle : les serveurs
présentent leur certificat et exigent un certificat client signé par
`TLS_CLIENT_CA_PATH`. Les clients intégrés (REST et UI) présentent chacun leur
certificat. Le certificat serveur doit contenir les noms DNS `pharmacie` et
`radiologie` dans son SAN pour les appels internes Compose. Pour les clients
gRPC directs depuis Internet, ajouter aussi le DNS public utilisé par ces
clients au SAN du certificat serveur. Ce profil exige également `API_KEY` pour
protéger la passerelle REST.

Pour une démonstration locale uniquement, un certificat de courte durée peut
être généré avec OpenSSL : `sh scripts/generate_dev_certs.sh`. Le script crée
des clés sous `certs/`, répertoire ignoré par Git; utiliser le même `ca.crt`
comme CA serveur et client dans `.env`. Ne pas utiliser cette CA de
développement en production. Sur le VPS, installer les certificats émis par
votre autorité et vérifier que l'utilisateur du conteneur (UID 10001) peut lire
les clés montées. Garder les clés privées hors du dépôt et limiter leur lecture
aux processus des conteneurs concernés.

Renseigner dans `.env` les chemins vers les certificats, la clé serveur et les
CA serveur/client, ainsi que les certificats clients de la passerelle et de
l'interface. Restreindre l'accès aux clés au compte d'administration, ne pas
les ajouter au dépôt, puis démarrer avec :

```sh
docker compose -f compose.yaml -f compose.tls.yaml up --build -d
```

Pour que des systèmes externes se connectent directement en gRPC, configurer
`HOST_GRPC_BIND_IP=0.0.0.0` et n'autoriser dans le pare-feu que leurs IP ou le
proxy réseau prévu. Les clients externes activent la même configuration avec `GRPC_TLS_CA`,
`GRPC_TLS_CLIENT_CERT` et `GRPC_TLS_CLIENT_KEY`, puis ciblent le DNS et le port
gRPC accessibles. Les variables `PHARMACIE_GRPC_TARGET` et
`RADIOLOGIE_GRPC_TARGET` sélectionnent les destinations pour les applications.

## Tests avant publication

```sh
python -m pip install -r requirements.txt
python -m grpc_services.generate_proto
python tests/test_pharmacie_rpc.py
python tests/test_radiologie_rpc.py
python tests/test_delais_rpc.py
python tests/test_medecin_integration.py
python -m pytest -q tests/test_api_gateway.py
docker compose config
docker compose build
```

Avec les quatre conteneurs démarrés, comparer REST et gRPC depuis l'hôte :

```sh
python -m benchmarks.compare_protocols --rest-url http://127.0.0.1:8000 \
  --iterations 100 --api-key "$API_KEY"
```

Le rapport donne moyenne, médiane, p95 et tailles des messages applicatifs. Il
exclut les en-têtes HTTP/2, l'encapsulation réseau et TLS; il sert à comparer
les sérialisations et les temps mesurés de bout en bout sur cet environnement.

La destination VPS, ses DNS, les certificats et les règles réseau appartiennent
à l'équipe qui administre l'infrastructure; aucun déploiement public n'est
effectué par ces fichiers Compose.

## Déploiement manuel par GitHub Actions

Le workflow `.github/workflows/deploy-vps.yml` est manuel (`workflow_dispatch`)
et déploie la branche `romuald-pharmacie-radiologie` dans
`/opt/clinique-rpc` sur le VPS. Avant de le lancer :

1. Installer Docker Compose et cloner la branche sous `/opt/clinique-rpc`.
2. Préparer `/opt/clinique-rpc/.env` avec `API_KEY`, chemins des certificats,
   ports et configuration du proxy. Installer les certificats sous `certs/`.
3. Créer un compte SSH dédié, installer sa clé publique dans `authorized_keys`
   et configurer son accès au moteur Docker. Préférer [Docker rootless](https://docs.docker.com/engine/security/rootless/);
   un compte membre du groupe `docker` peut obtenir des privilèges équivalents
   à root.
4. Définir les secrets GitHub `VPS_HOST`, `VPS_USER`, `VPS_SSH_PRIVATE_KEY` et
   `VPS_KNOWN_HOSTS`. `VPS_KNOWN_HOSTS` doit contenir la clé d'hôte SSH vérifiée
   hors bande; le workflow n'utilise pas `ssh-keyscan` non vérifié.
5. Lancer **Deploy to VPS** depuis Actions, puis vérifier l'état des conteneurs,
   `/health/ready`, les logs et le reverse proxy.

Le workflow ne se déclenche pas à chaque push et n'embarque aucun secret. Il
attend que l'équipe renseigne l'accès et la configuration de son VPS.
