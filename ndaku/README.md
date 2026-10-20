# Ndaku — location & vente de maisons (style Airbnb, orange/blanc)

Comptes **client** / **hôte**, annonces location ou vente, filtres par ville/quartier/prix, « meilleures maisons » (avis vérifiés + favoris + hôte vérifié), demandes de visite, avis, signalements, modération.

## Lancer
```bash
pip install -r requirements.txt
python seed.py --reset      # données de démo (mot de passe : Ndaku2026)
python app.py               # http://localhost:5000
python -m pytest tests -q
```
Comptes démo : `admin@ndaku.app`, `jean@ndaku.app` / `grace@ndaku.app` (hôtes), `aline@ndaku.app` (client).

**Version web / déploiement** : `docker build -t ndaku . && docker run -p 8000:8000 -v ndaku-data:/app/instance ndaku` (gunicorn, cookies `Secure`). Le disque `instance/` (SQLite + photos) doit être persistant.

## Photos réelles de Kinshasa
`python fetch_photos.py` télécharge des photos sous licence libre (Wikimedia Commons) dans `seed_photos/` avec leurs crédits (`credits.json`), puis `python seed.py --reset` les utilise. Sans elles, des illustrations générées sont utilisées. Vérifiez visuellement les photos avant usage.

## Anti-fraude
| Menace | Parade |
|---|---|
| Même photo réutilisée (copie, redimensionnée, recompressée, recadrée, en miroir) | Empreinte exacte + dHash/pHash comparées à **toutes** les annonces ; contrainte `UNIQUE(sha)` contre les courses concurrentes ; refus par photo avec motif |
| Photos volées / vides | Min. 480×320, rejet des images uniformes, ré-encodage (EXIF/GPS supprimé) |
| Même bien publié par deux hôtes | Clé d'adresse normalisée unique par type d'offre |
| Sortie de la plateforme (téléphone, e-mail, WhatsApp, liens) | Refusé dans titre/description |
| Prix « trop beau pour être vrai » | Écart à la médiane locale (€/m²) → modération |
| Description copiée | Similarité de Jaccard (3-grammes) → modération |
| Faux avis | Avis réservés aux clients ayant contacté l'hôte, un par annonce |
| Annonces trompeuses | 3 signalements distincts → masquage automatique + file de modération |
| Abus de compte | Verrouillage après 5 échecs, quota 5 annonces/24 h, hôte « vérifié » par l'admin, CSRF (en-tête), CSP |

Limites : la comparaison d'images est linéaire (passer à un index BK-tree/LSH au-delà de ~100 k photos) ; l'identité de l'hôte n'est pas vérifiée automatiquement (KYC/OTP à brancher) ; un fraudeur peut photographier un écran — d'où la modération et les signalements.
