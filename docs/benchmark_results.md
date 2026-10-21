# Résultats de comparaison gRPC et REST

Mesure de démonstration réalisée sur le même hôte avec les serveurs gRPC
Pharmacie/Radiologie, la passerelle FastAPI et des données fictives. Chaque
opération a été répétée 100 fois, après un appel de chauffe. Les latences sont
de bout en bout sur loopback ; elles décrivent cette machine et ne prédisent pas
les performances d'un autre réseau ou du déploiement Render.

| Opération | Latence moyenne | Médiane | p95 | Requête (octets) | Réponse (octets) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pharmacie gRPC | 0,984 ms | 0,966 ms | 1,491 ms | 10 | 66 |
| Pharmacie REST | 4,651 ms | 4,134 ms | 8,418 ms | 62 | 178 |
| Radiologie gRPC | 0,832 ms | 0,703 ms | 1,301 ms | 8 | 122 |
| Radiologie REST | 3,726 ms | 3,570 ms | 5,450 ms | 33 | 139 |

Sur cette exécution, gRPC a répondu plus vite et avec des messages applicatifs
plus compacts. La mesure REST inclut le trajet HTTP vers FastAPI puis l'appel
gRPC de la passerelle au service. Les tailles REST comptent le chemin et la
query pour les requêtes, et le corps JSON pour les réponses ; elles excluent
les en-têtes, le framing réseau et TLS. Les tailles gRPC comptent les messages
Protocol Buffers sérialisés, sans framing HTTP/2.

Pour reproduire la comparaison avec la pile Docker locale démarrée :

```sh
python -m benchmarks.compare_protocols --rest-url http://127.0.0.1:8000 \
  --iterations 100 --api-key "$API_KEY"
```

La clé API doit rester dans l'environnement local et ne pas être ajoutée au
dépôt. Les sorties sont des mesures de démonstration, pas une garantie de
performance ni une mesure de systèmes médicaux en production.
