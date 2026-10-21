# Orientation de la partie Pharmacie et Radiologie

Ce document conserve les consignes de travail reçues pour poursuivre cette
partie du projet de façon autonome et recentrer les évolutions futures.

## Architecture retenue

- Les services Pharmacie et Radiologie sont autonomes et utilisent des données
  fictives locales.
- Ils exposent leurs opérations via les contrats Protocol Buffers et gRPC.
- Les clients Médecin, REST ou UI consomment les stubs sans dépendre de leur
  implémentation interne.
- Les ports de référence demandés initialement sont `50052` (Pharmacie) et
  `50053` (Radiologie). Le plan reçu cite aussi `50054` et `50055` comme ports
  alternatifs. Conserver les ports initiaux par défaut et rendre les ports
  configurables avant toute intégration qui requiert ces alternatives.

## Services auxquels le client Médecin doit se connecter

L'énoncé demande au logiciel du médecin d'interroger trois systèmes distincts :
le Laboratoire, la Pharmacie et la Radiologie. Il s'agit d'appels gRPC séparés
depuis le client Médecin ; Pharmacie et Radiologie n'ont pas à s'appeler l'une
l'autre.

- Pharmacie : `proto/pharmacie.proto`, service `clinique.pharmacie.PharmacieService`,
  RPC `VerifierStock` (et `ListerMedicaments` pour l'inventaire), port local
  `50052`.
- Radiologie : `proto/radiologie.proto`, service `clinique.radiologie.RadiologieService`,
  RPC `ObtenirExamen`, port local `50053`.
- Laboratoire : c'est une dépendance distincte du client Médecin, développée
  par les autres membres. Le présent travail raccorde les RPC Pharmacie et
  Radiologie ; le client Médecin peut appeler chacun de ces services sans
  dépendre du service Laboratoire.

Le client Médecin de démonstration (`grpc_services/medecin_client.py`) prouve
les appels gRPC directs vers Pharmacie et Radiologie. Sa commande `consultation`
appelle `VerifierStock` et `ObtenirExamen` en parallèle. REST est conservé pour
la passerelle Web et la comparaison demandée dans le sujet ; il ne remplace pas
les appels gRPC entre services.

Pour connecter le client Médecin aux serveurs sur un autre hôte, définir
`PHARMACIE_GRPC_TARGET=hote:50052` et
`RADIOLOGIE_GRPC_TARGET=hote:50053`, puis lancer :

```sh
python -m grpc_services.medecin_client consultation MED001 RAD001 --quantite 2
```

En Docker Compose, les clients du réseau Compose utilisent les noms DNS
`pharmacie:50052` et `radiologie:50053`. Depuis une autre machine sur le réseau
local, l'hôte des services doit publier les ports vers son interface réseau et
autoriser ces ports dans son pare-feu ; utiliser le profil TLS/mTLS pour les
appels qui traversent un réseau non fiable.

## Déploiement et accessibilité gRPC

En local, utiliser Docker Compose ou lancer les serveurs sur `50052` et `50053`.
La démo Render actuelle garde ces ports sur `127.0.0.1` dans le même conteneur :
le client Médecin exécuté dans ce conteneur peut les joindre, mais un client
gRPC externe ne peut pas appeler directement les ports via l'URL `onrender.com`.
Pour des échanges gRPC directs entre systèmes hébergés, déployer les services
sur un réseau privé commun (services Render compatibles et accessibles sur ce
réseau) ou sur un VPS avec ports gRPC, pare-feu et TLS/mTLS configurés. Garder
les clés et certificats dans les variables/secrets d'environnement, jamais dans
le dépôt.

## Fonctionnalités backend déjà réalisées

- Enrichir les jeux de données : code, nom, quantité, statut et emplacement des
  médicaments ; patient, examen, type d'acte, statut et compte-rendu en
  Radiologie.
- Permettre la recherche radiologique par identifiant d'examen et, si le
  contrat commun le permet, par identifiant patient.
- Gérer les arguments invalides et les éléments absents avec les statuts gRPC
  appropriés (`INVALID_ARGUMENT`, `NOT_FOUND`).
- Latence configurable maintenant disponible via `PHARMACIE_LATENCE_MS` et
  `RADIOLOGIE_LATENCE_MS`, et ports configurables via `PHARMACIE_PORT` et
  `RADIOLOGIE_PORT`.
- Garder les contrats `.proto` comme interface partagée et vérifier leur
  compatibilité avant de modifier les messages ou les méthodes RPC.

Le client médecin conserve les erreurs par service : si Pharmacie est
indisponible, il affiche tout de même une réponse Radiologie réussie (et
inversement), puis signale l'échec RPC correspondant. Chaque appel garde son
propre délai maximal.

## Maquette UI

La maquette `ui_app.py` appelle les deux stubs, affiche les stocks et les
comptes-rendus, indique l'état de santé des services et peut ajuster le stock
fictif en mémoire. Cette modification est réinitialisée au redémarrage.
