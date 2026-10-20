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

Une maquette de suivi est disponible dans `ui_app.py`. Après installation des
dépendances et démarrage des deux serveurs, lancer :

```powershell
streamlit run ui_app.py
```

L’interface montre la santé des deux services, permet de vérifier un médicament,
de charger le tableau des stocks depuis la pharmacie et de consulter les examens
par identifiant d’examen ou de patient. Elle est en lecture seule : le contrat
Pharmacie n’expose pas encore d’opération de mise à jour de stock.

## 6. Équipe

Projet réalisé en groupe de sept membres dans le cadre du cours de Middleware.
