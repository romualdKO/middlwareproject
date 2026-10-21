# Fiche de raccordement gRPC — Pharmacie et Radiologie

Cette fiche est destinée aux membres qui développent le client Médecin ou un
autre client gRPC devant consulter nos services Pharmacie et Radiologie.

## Contrats et opérations

Les fichiers `.proto` sont la référence commune ; générer les stubs du langage
du client à partir de ces contrats :

| Service | Contrat | Service gRPC | Méthode principale | Port local |
| --- | --- | --- | --- | ---: |
| Pharmacie | `proto/pharmacie.proto` | `clinique.pharmacie.PharmacieService` | `VerifierStock` | `50052` |
| Radiologie | `proto/radiologie.proto` | `clinique.radiologie.RadiologieService` | `ObtenirExamen` | `50053` |

### Pharmacie — `VerifierStock`

Requête : `medicament_id` (obligatoire) et `quantite_demandee` (facultatif,
doit être supérieur à zéro). Une demande omise vérifie une unité. La réponse
contient notamment `nom`, `disponible`, `quantite`, `statut`, `message` et
`emplacement`.

Exemple fictif : `MED001`, quantité demandée `2`. L'inventaire de démo est dans
`data/mock_pharmacie_radio.py` ; utiliser ces identifiants uniquement pour les
essais.

### Radiologie — `ObtenirExamen`

Fournir `examen_id` ou `patient_id` (au moins l'un des deux). La réponse contient
`examens`, une liste dont les éléments portent `examen_id`, `patient_id`,
`type_examen`, `etat`, `resultat` et `date`.

Exemples fictifs : examen `RAD001`, patient `PAT001`. Les dossiers de démonstration
sont dans `data/mock_pharmacie_radio.py`.

## Adresses selon l'environnement

- **Même ordinateur** : `localhost:50052` et `localhost:50053`.
- **Conteneurs du même Docker Compose** : `pharmacie:50052` et
  `radiologie:50053` (noms DNS internes à Compose).
- **Machines différentes sur un réseau privé** : l'adresse IP/DNS joignable de
  l'hôte des services, avec les ports `50052` et `50053` ouverts. Par défaut,
  Compose n'écoute que sur `127.0.0.1` ; l'hôte doit explicitement choisir une
  interface réseau avant qu'un autre ordinateur puisse joindre les ports.
- **Démo Render actuelle** : l'URL `https://clinique-espoir-demo.onrender.com`
  sert l'interface et l'API HTTP. Dans cette configuration, les ports gRPC
  restent sur la boucle locale du conteneur ; ne pas utiliser l'URL `onrender.com`
  comme cible gRPC.

Pour les appels gRPC directs entre systèmes distants, utiliser un réseau privé
commun adapté ou un hôte/VPS doté de ports gRPC accessibles et de TLS/mTLS. Ne
pas exposer des ports gRPC en clair sur Internet.

## Configuration côté client

Le client Python de démonstration lit les cibles suivantes :

```text
PHARMACIE_GRPC_TARGET=hote-accessible:50052
RADIOLOGIE_GRPC_TARGET=hote-accessible:50053
GRPC_TIMEOUT_SECONDS=2
```

Puis le parcours qui interroge les deux services peut être lancé ainsi :

```sh
python -m grpc_services.medecin_client consultation MED001 RAD001 --quantite 2
```

Les clients d'autres langages doivent compiler les mêmes `.proto` et appeler
les mêmes noms de service/méthode. Le client médecin peut interroger Pharmacie
et Radiologie séparément ou en parallèle ; ces deux serveurs ne s'appellent pas
l'un l'autre. En mode parallèle, une panne d'un service ne masque pas le
résultat de l'autre : le client affiche la réponse réussie et l'erreur gRPC du
service indisponible.

## Délais et erreurs à traiter

Définir un délai par RPC (2 secondes par défaut dans le client Python). Le
serveur peut répondre avec `INVALID_ARGUMENT` (identifiant/requête invalide),
`NOT_FOUND` (élément absent), `DEADLINE_EXCEEDED` (délai dépassé), `UNAVAILABLE`
(service/réseau indisponible) ou `INTERNAL` (données fictives invalides). Le
client doit afficher/consigner le code gRPC et ne pas interpréter une absence de
réponse comme un résultat médical vide.

Les deux services exposent le protocole standard gRPC Health Checking. Les
clients de ce dépôt vérifient le statut `SERVING` avec `is_healthy()`.

## Sécurité et informations à échanger

Avant un raccordement distant, les deux équipes doivent convenir par canal
sécurisé de :

1. l'adresse DNS/IP et du port accessibles depuis l'environnement client ;
2. l'autorité de certification (CA) TLS et, si mTLS est activé, du certificat
   client et de sa clé privée ;
3. la règle pare-feu/réseau autorisant le client ;
4. l'environnement de test et des identifiants fictifs valides.

Les chemins de certificats côté clients Python peuvent être fournis par
`GRPC_TLS_CA`, `GRPC_TLS_CLIENT_CERT` et `GRPC_TLS_CLIENT_KEY`. Ne jamais
transmettre une clé privée ou des données de patient dans le dépôt, un canal
public ou les journaux.

## Message prêt à transmettre aux collègues

> Pour intégrer Pharmacie et Radiologie au client médecin, compilez les
> contrats `proto/pharmacie.proto` et `proto/radiologie.proto`. Appelez
> `clinique.pharmacie.PharmacieService/VerifierStock` sur `hôte:50052` avec
> `medicament_id` et, si besoin, `quantite_demandee`. Appelez
> `clinique.radiologie.RadiologieService/ObtenirExamen` sur `hôte:50053` avec
> `examen_id` ou `patient_id`. Les délais et erreurs gRPC doivent être traités
> côté client. Envoyez-moi l'adresse réseau joignable depuis votre exécution et
> les paramètres TLS convenus ; l'URL Render actuelle ne fournit pas d'accès
> gRPC direct. Pour les essais locaux, les identifiants fictifs sont `MED001`,
> `RAD001` et `PAT001`.

## Comprendre le nom `clinique` et les adresses

Dans un `.proto`, `package clinique.pharmacie;` définit un espace de noms :
`clinique` regroupe les contrats de la Clinique Espoir et `pharmacie` désigne
ce domaine de service. Ce n'est ni un nom DNS, ni une adresse IP, ni un serveur.
Le nom complet du service est `clinique.pharmacie.PharmacieService` ; la méthode
gRPC complète est
`/clinique.pharmacie.PharmacieService/VerifierStock`. En Radiologie, les noms
correspondants sont `clinique.radiologie.RadiologieService` et
`/clinique.radiologie.RadiologieService/ObtenirExamen`.

La cible réseau reste séparée du nom de service : `hote-accessible:50052` ou
`hote-accessible:50053`. `localhost` ne fonctionne que si le client tourne sur
la même machine que les serveurs.

## Quel lien transmettre ?

Oui, tu peux transmettre l'URL Render pour ouvrir la démo Web :
<https://clinique-espoir-demo.onrender.com>. Tu peux aussi transmettre
<https://clinique-espoir-demo.onrender.com/docs> pour la documentation de la
passerelle HTTP/JSON. Ces liens ne sont pas des cibles gRPC. Le déploiement
Render actuel écoute ses serveurs gRPC sur `127.0.0.1` dans le conteneur et
n'expose donc pas les ports `50052`/`50053` aux clients externes.

L'erreur « Clé API manquante ou incorrecte » visible sur la page est une erreur
HTTP 401 de la passerelle Web :

1. Dans Render, ouvre le service `clinique-espoir-demo`, puis **Environment**.
2. Récupère la valeur de `API_KEY` (ou régénère-la si elle est perdue) sans la
   publier dans un groupe ou un dépôt.
3. Dans la démo, saisis-la dans le champ **Clé API**, puis clique **Connecter**.

Cette clé sert à la passerelle REST et à l'interface Web. Elle ne sert pas à
l'authentification gRPC et ne donne pas accès aux ports gRPC.

## Fichiers à remettre selon le besoin

Pour intégrer un client à nos RPC, transmettre en premier les contrats :

- `proto/pharmacie.proto`
- `proto/radiologie.proto`

Si le client est en Python et veut réutiliser directement notre code client,
transmettre aussi :

- `grpc_services/clients.py` et `grpc_services/security.py`
- `grpc_services/generated/__init__.py`
- `grpc_services/generated/pharmacie_pb2.py` et
  `grpc_services/generated/pharmacie_pb2_grpc.py`
- `grpc_services/generated/radiologie_pb2.py` et
  `grpc_services/generated/radiologie_pb2_grpc.py`
- `requirements-runtime.txt` (ou installer au minimum `grpcio` et
  `grpcio-health-checking`)
- `grpc_services/medecin_client.py` comme exemple d'appels, si utile.

Pour lancer notre démonstration locale complète, transmettre plutôt le dépôt
et consulter `README.md`. Les fichiers `grpc_services/*_server.py`,
`data/mock_pharmacie_radio.py` et `compose.yaml` servent à exécuter les serveurs ;
ils ne sont pas requis au client qui ne fait que consommer les RPC.

## Ce que le service appelant doit faire

1. Générer des stubs depuis les deux `.proto` (ou importer les stubs Python
   ci-dessus).
2. Configurer les deux destinations gRPC réelles, une pour chaque service.
   Dans le réseau Docker Compose commun, utiliser `pharmacie:50052` et
   `radiologie:50053`. Depuis un autre environnement, demander l'adresse DNS/IP
   et le port réellement routables ; l'URL Render ne les fournit pas.
3. Appeler `VerifierStock` avec un identifiant médicament et une quantité
   positive, puis `ObtenirExamen` avec un `examen_id` ou un `patient_id`.
4. Fixer un délai par appel (2 secondes par défaut dans notre exemple) et
   afficher/traiter les statuts `INVALID_ARGUMENT`, `NOT_FOUND`,
   `DEADLINE_EXCEEDED` et `UNAVAILABLE`.
5. Si les appels traversent un réseau non fiable, activer TLS/mTLS : faire
   émettre un certificat client par l'autorité convenue et configurer
   `GRPC_TLS_CA`, `GRPC_TLS_CLIENT_CERT` et `GRPC_TLS_CLIENT_KEY` côté Python.
6. Tester les deux appels depuis l'environnement exact où le client sera
   exécuté, avec les données fictives `MED001`, `RAD001` ou `PAT001`.

Pour la démo Render, le collègue peut seulement ouvrir le site ou appeler les
routes REST avec l'en-tête `X-API-Key`. Pour une intégration gRPC directe, il
faut déployer nos serveurs sur un hôte/réseau qui publie les ports gRPC avec
TLS/mTLS, puis remplacer les cibles par son DNS/IP.

## Interop??rabilit?? avec Consultation et Accueil (Tailscale)

Le contrat fourni par l'??quipe Consultation est `proto/clinique.proto` (package
`clinique`). Les services Pharmacie et Radiologie de ce projet conservent leurs
contrats et leurs RPC existants, et exposent en plus le contrat partag?? n??cessaire
?? l'interop??rabilit?? :

- Radiologie appelle `clinique.Consultation/NotifierResultat` apr??s la mise ?? jour
  d'un examen, avec `id_dossier=<patient_id>`, `id_resultat=<examen_id>` et
  `type="R"`. Consultation renvoie `id_notif`.
- Pharmacie expose `clinique.Pharmacie/GetMedicamentsPharmacie`, avec les champs
  `id`, `nom` et `stock`, pour que Consultation puisse lire l'inventaire.
- Les RPC `clinique.Accueil` de ce contrat sont des appels sortants de
  Consultation vers Accueil ; notre service n'a pas ?? les impl??menter.

Configurer Radiologie avec la cible Tailscale du serveur Consultation :

```text
CONSULTATION_GRPC_TARGET=<IP_TAILSCALE_CONSULTATION>:50051
CONSULTATION_NOTIFICATION_TIMEOUT_SECONDS=2
```

Configurer le serveur Consultation avec la cible Tailscale de notre Pharmacie :

```text
PHARMACIE_ADDR=<IP_TAILSCALE_DE_CETTE_MACHINE>:50052
MOCK=0
```

Attention : la documentation Consultation donne `localhost:50053` comme valeur
par d??faut de `PHARMACIE_ADDR`, mais dans ce projet Pharmacie ??coute sur `50052`
et Radiologie sur `50053`. Il faut donc remplacer cette valeur par l'IP Tailscale
et le port r??el de Pharmacie ; le `50053` local correspond ici ?? Radiologie.

Pour les essais sur les ordinateurs de la pr??sentation, lancer les serveurs avec
`GRPC_BIND_HOST=0.0.0.0` (ou une interface joignable par Tailscale), autoriser
les ports n??cessaires dans le pare-feu, puis ??changer les IP Tailscale et les
ports. Le trafic du tailnet est chiffr?? par Tailscale ; le contrat Consultation
indique gRPC sans TLS par d??faut. Ne pas utiliser les URL Render comme cibles
pour ces RPC. En Docker Compose, le mapping actuel est limit?? ?? `127.0.0.1` par
d??faut ; pour une d??monstration entre machines, adapter `HOST_GRPC_BIND_IP` ou
lancer les serveurs Python directement.

`proto/clinique.proto` est le contrat gRPC ?? partager avec les ??quipes
Consultation/Accueil. L'API REST `POST /api/notifs` document??e par Consultation
est l'??quivalent HTTP de `NotifierResultat`, mais pour la d??monstration RPC on
appelle directement la m??thode gRPC.

## Notification Radiologie vers Consultation depuis Render

Pour la d?monstration o? les deux ?quipes utilisent leurs URL Render publiques,
configurer dans l'environnement Render de `clinique-espoir-demo` :

```text
CONSULTATION_REST_URL=https://<url-publique-consultation>
CONSULTATION_NOTIFICATION_TIMEOUT_SECONDS=5
```

Entrer seulement l'origine HTTPS (sans `/api/notifs`) ; Radiologie ajoute cette
route et envoie `id_dossier` (patient_id), `id_resultat` (examen_id) et `type="R"`.
Cette configuration REST est prioritaire sur `CONSULTATION_GRPC_TARGET` pour
cette d?monstration. Ne pas mettre l'adresse Tailscale `100.64.4.67` ici, car
elle n'est pas accessible au service Render.

Pour d?clencher l'op?ration depuis l'API Render, utiliser l'URL publique de
notre passerelle, la cl? `API_KEY` et un identifiant d'examen existant :

```sh
curl -X PUT "https://clinique-espoir-demo.onrender.com/api/v1/radiologie/examens/RAD002/etat" \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"etat":"termine","resultat":"Compte rendu de d?monstration"}'
```

La r?ponse contient `notification_envoyee` et le message de Consultation. Si
elle vaut `false`, consulter le message retourn? ainsi que les journaux Render
des deux services. Ne jamais publier la valeur de `API_KEY`.
