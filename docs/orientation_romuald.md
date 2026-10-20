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

## Évolutions backend prévues

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

## Maquette UI

Une interface de démonstration indépendante pourra ensuite appeler les deux
stubs, afficher les stocks et comptes-rendus, simuler des changements de stock
et montrer l'état de santé des services. Cette maquette reste un chantier
distinct du backend gRPC actuel.
