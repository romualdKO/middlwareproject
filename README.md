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
- `rest_services/` : API et client REST.
- `tests/` : tests fonctionnels et benchmarks.
- `docs/` : documentation et schémas.
- `data/` : données fictives de démonstration.

## 5. Exécution

Les contrats pharmacie et radiologie sont dans `proto/`. Après installation des
dépendances, les modules Python peuvent être régénérés avec :

```powershell
python -m grpc_services.generate_proto
```

Lancer chaque serveur dans son propre terminal :

```powershell
python -m grpc_services.pharmacie_server  # port 50052
python -m grpc_services.radiologie_server # port 50053
```

Les données de démonstration sont dans `data/medicaments.json` et
`data/examens_radiologiques.json`. Les tests RPC individuels démarrent un serveur
local sur un port libre et se lancent depuis la racine du dépôt :

```powershell
python tests/test_pharmacie_rpc.py
python tests/test_radiologie_rpc.py
```

## 6. Équipe

Projet réalisé en groupe de sept membres dans le cadre du cours de Middleware.
