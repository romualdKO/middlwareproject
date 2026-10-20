# Clinique Espoir — Projet gRPC et REST

## 1. Présentation

Ce projet consiste à développer et comparer deux approches de communication entre les systèmes d'information d'une clinique :

- gRPC, basé sur des contrats Protocol Buffers.
- REST, basé sur HTTP et JSON.

L'objectif est de faciliter les échanges entre les services d'accueil, de consultation, de laboratoire, de pharmacie et de radiologie.

## 2. Technologies

- Python
- gRPC
- Protocol Buffers
- FastAPI
- Uvicorn
- HTTPX
- Pytest
- Git et GitHub

## 3. Installation

Créer et activer l'environnement virtuel :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Installer les dépendances :

```powershell
python -m pip install -r requirements.txt
```

## 4. Organisation

- `proto/` : contrats de communication.
- `grpc_services/` : serveurs et clients gRPC.
- `rest_services/` : passerelle API REST vers les serveurs gRPC.
- `tests/` : tests fonctionnels et benchmarks.
- `benchmarks/` : comparaison des temps de réponse et tailles gRPC/REST.
- `docs/` : documentation et schémas.
- `data/` : données fictives de démonstration.
- `compose.yaml` : démarrage local des deux serveurs, passerelle REST et UI.

## 5. Exécution

Les contrats pharmacie et radiologie sont dans `proto/`. Après installation des
dépendances, les modules Python peuvent être régénérés avec :

```powershell
python -m grpc_services.generate_proto
```

Les clients gRPC partagés sont dans `grpc_services/clients.py`. Les appels
externes peuvent aussi utiliser la passerelle REST FastAPI documentée dans
`docs/deployment.md` (`/docs` pour OpenAPI, clé `X-API-Key` configurable).
Les deux serveurs publient aussi le protocole standard gRPC Health Checking.

Lancer chaque serveur dans son propre terminal :

```powershell
python -m grpc_services.pharmacie_server  # port 50052
python -m grpc_services.radiologie_server # port 50053
```

Les données de démonstration sont dans `data/mock_pharmacie_radio.py`. Les ports
et latences peuvent être configurés avec `PHARMACIE_PORT`, `RADIOLOGIE_PORT`,
`PHARMACIE_LATENCE_MS` et `RADIOLOGIE_LATENCE_MS` (latence en millisecondes).
Les tests RPC individuels démarrent un serveur local sur un port libre et se
lancent depuis la racine du dépôt :

```powershell
python tests/test_pharmacie_rpc.py
python tests/test_radiologie_rpc.py
python tests/test_delais_rpc.py
python tests/test_medecin_integration.py
python tests/test_api_gateway.py
```

Un client médecin de démonstration est disponible pour valider l'appel aux deux
services une fois ceux-ci démarrés :

```powershell
python -m grpc_services.medecin_client pharmacie MED001 --quantite 2
python -m grpc_services.medecin_client radiologie --patient PAT001
python -m grpc_services.medecin_client radiologie --examen RAD001
```

Ce client sert de référence d'intégration locale. Le client médecin de l'équipe
pourra reprendre les mêmes stubs et confirmer ses contrats avant l'intégration
finale.

Après démarrage des serveurs gRPC et de la passerelle REST, comparer les
protocoles avec :

```powershell
python -m benchmarks.compare_protocols --iterations 100 --api-key VOTRE_CLE_API
```

Une maquette de suivi est disponible dans `ui_app.py`. Elle peut consulter et
simuler l'ajustement des stocks fictifs (en mémoire seulement). Après
installation des dépendances et démarrage des deux serveurs, lancer :

```powershell
streamlit run ui_app.py
```

Pour démarrer toute la pile en local avec Docker Compose :

```powershell
Copy-Item .env.example .env
docker compose up --build
```

La passerelle REST est sur `http://localhost:8000/docs`; l'interface est sur
`http://localhost:8501`. Pour lancer la passerelle hors Compose, utiliser
`python -m uvicorn rest_services.gateway:app --host 0.0.0.0 --port 8000` après
avoir lancé les serveurs gRPC.

L'interface montre la santé des deux services, permet de vérifier un médicament,
de charger l'inventaire et d'ajuster un stock de démonstration. Elle consulte les
examens par identifiant d'examen ou de patient.

## 6. Déploiement

La configuration Docker Compose démarre les deux services gRPC, la passerelle
REST et l'interface Streamlit. Voir [docs/deployment.md](docs/deployment.md) pour
les ports, les clés API, TLS mutuel et les étapes de déploiement VPS. Les mocks
ne conviennent pas à des données de patients réelles.

## 7. Équipe

Projet réalisé en groupe de sept membres dans le cadre du cours de Middleware.
