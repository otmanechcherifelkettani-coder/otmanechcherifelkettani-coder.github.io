# HESTIM Agent — admissions et support étudiants sur WhatsApp et Instagram

Un agent IA ("Nora") qui répond à chaque message entrant en moins d'une minute, qualifie les
prospects, gère le support simple des étudiants inscrits et transmet le reste à l'équipe avec la
conversation complète. Le schéma reprend celui du document Palete (Moringa / GOMYCODE), adapté à HESTIM.

## Ce que fait l'agent

| Flux | Comportement |
|---|---|
| **Admissions** | Répond sur les programmes, l'admission et la rentrée. Qualifie chaque contact (qui écrit, niveau, programme, rentrée, ville) et le classe `ready` / `undecided` / `general` / `not_fit` / `enrolled`. Les prospects `ready` sont transmis à un conseiller (`request_counselor_call`). |
| **Nurturing** | Envoie une relance WhatsApp aux prospects indécis qui ne répondent plus (remplace l'email), dans la fenêtre des 24 h. |
| **Support étudiants** | Répond à ce que couvre la base de connaissances. Paiements, reçus et attestations sont transmis à `finance` / `scolarite` avec un résumé exploitable. |
| **Escalade** | Passe la main (handoff) si le contact demande un humain, est en colère, ou en cas de situation sensible (`urgent`). Si une question n'a pas de réponse dans la base, crée un `knowledge_gap` et continue la conversation. |
| **Langues** | Français, arabe, darija (lettres arabes et arabizi), anglais. Répond dans la langue du contact. |
| **Exactitude** | Ne répond qu'à partir de `knowledge/hestim_kb.md`. Ne cite jamais une info marquée `[À CONFIRMER]`. |

## Interface équipe (`/`)
Interface façon messagerie (liste de discussions, bulles, mode clair/sombre, mobile). Chaque membre de l'équipe a son propre identifiant (`INBOX_USERS`) ; son nom signe ses réponses.

### Rôles et équipes
Chaque discussion appartient à **une** équipe. Chaque membre ne voit que les discussions, contacts,
escalades, statistiques et exports de ses équipes. C'est appliqué côté serveur : une discussion
d'une autre équipe répond « introuvable », y compris par l'API.

| Équipe | Reçoit |
|---|---|
| `admissions` | Toutes les nouvelles discussions, appels conseiller, questions sans réponse dans la base |
| `finance` | Escalades `finance` (paiements, reçus, échéanciers) |
| `scolarite` | Escalades `scolarite` (attestations, notes, inscriptions administratives) |
| `vie_etudiante` | Escalades `urgent` (harcèlement, santé, sécurité, plaintes) |
| `admin` (rôle) | Tout, avec filtres par équipe |

Quand l'agent escalade, la discussion passe automatiquement à l'équipe concernée (une note
« Transférée de … vers … » apparaît dans le fil). Un membre peut aussi la **transférer** à une autre
équipe et ne peut l'**attribuer** qu'à un collègue de l'équipe qui la détient. Le routage se règle
dans `config.py` (`TEAMS`, `ESCALATION_TEAM`). Exemple :
`INBOX_USERS="Direction:pw0:admin,Karim:pw1:admissions,Fatima:pw2:finance,Sara:pw3:scolarite|vie_etudiante"`

- **Conversations** : recherche et filtres (IA / équipe, statut du lead) ; badge indiquant qui gère la conversation ; **Attribuer** à un collègue ; **Prendre le contrôle** (coupe l'autopilote) et **Rendre à l'IA** ; réponse manuelle. L'IA voit ensuite ce que l'équipe a écrit.
- **Contacts** : vue d'ensemble (total, abonnés et désabonnés, par canal, prêts, indécis), filtres, export CSV, et **Demandez à l'IA** (« prospects prêts intéressés par l'ingénierie à Casablanca »).
- **Escalades** : file à traiter par l'équipe, à marquer comme résolues.
- **Tester l'agent** : chatter avec l'agent comme un contact.

## Architecture

```
WhatsApp Cloud API ─┐                            ┌─ knowledge/hestim_kb.md (source de vérité)
Instagram Messaging ┴─> /webhook ─> agent/core.py ─> Claude (tools) ─> db.py (SQLite)
                                       │                                   │
                       channels/meta.py (envoi)          static/inbox.html + API /api/*
                       nurture.py (relances, toutes les 30 min)
```

- **Modèle** : `claude-opus-5-5` à effort `low` (adapté au chat ; à monter à `medium` si les réponses manquent de profondeur). Le fallback côté serveur (`fallbacks: "default"`) est activé : si un classifieur refuse une requête, l'API la relance sur un modèle de repli. Si tout échoue (refus, erreur API), la conversation passe à l'équipe avec un message d'attente : aucun contact n'est laissé sans réponse.
- **Historique** : le transcript Claude de chaque conversation est stocké en *append-only* avec les blocs exacts renvoyés par l'API, puis rejoué à chaque tour. Le cache de prompt fonctionne (prompt système + base + outils stables) et l'historique n'est jamais réécrit.
- **Outils** (`agent/tools.py`, `strict: true`) : `update_contact_profile`, `set_lead_status`, `request_counselor_call`, `escalate_to_human`, `unsubscribe_contact`.
- **Sécurité** : vérification de signature Meta (`X-Hub-Signature-256`), auth basique sur l'inbox, messages des contacts traités comme des données (résiste à l'injection de prompt), aucune collecte de mot de passe, carte bancaire ou pièce d'identité.

## Démarrage

```bash
cd hestim-agent
pip install -r requirements.txt
cp .env.example .env   # renseigner ANTHROPIC_API_KEY, INBOX_PASSWORD, etc.
```

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Ouvrir `http://localhost:8000/` puis l'onglet **Tester l'agent**. Sans jetons Meta, les envois
sont en mode *dry-run* (écrits dans les logs).

### Brancher WhatsApp et Instagram
1. Créer une app Meta, ajouter les produits **WhatsApp** et **Instagram** (messagerie).
2. URL du webhook : `https://<votre-domaine>/webhook`. Verify token : `META_VERIFY_TOKEN`.
   Abonner les champs `messages` (WhatsApp) et `messages` (Instagram).
3. Renseigner `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `INSTAGRAM_PAGE_TOKEN`, `META_APP_SECRET`.
4. Héberger derrière HTTPS (voir ci-dessous). GitHub Pages ne convient pas : il faut un serveur.

### Hébergement
L'app est un seul conteneur (`Dockerfile`) avec une base SQLite sur un volume persistant.
```bash
docker build -t hestim-agent .
```
```bash
docker run -d -p 8000:8000 --env-file .env -v hestim-data:/app/data hestim-agent
```
Fonctionne sur tout hébergeur de conteneurs avec disque persistant et HTTPS (Render, Railway,
Fly.io, ou un VPS avec Caddy/Nginx). Les données (conversations d'élèves marocains) relèvent de la
loi 09-08 : la déclaration ou l'autorisation CNDP et le lieu d'hébergement sont à valider avec HESTIM.

> WhatsApp n'autorise le texte libre que dans les 24 h suivant le dernier message du contact.
> Pour relancer au-delà, créez des **message templates** approuvés dans le WhatsApp Manager.

## Avant la mise en production (méthode Palete)

1. **Cadrage** : l'équipe admissions complète `knowledge/hestim_kb.md`. Toutes les lignes
   `[À CONFIRMER]` (frais, dates, filières, adresse, contacts) doivent être remplies ou laissées
   volontairement en escalade. Les informations actuelles viennent des sites publics de HESTIM et
   doivent être vérifiées.
2. **Tests sur personas synthétiques** :
   ```bash
   python simulate.py            # 12 personas : darija, arabe, anglais, parent, étudiant, harcèlement, injection…
   ```
   Pour générer 50 personas à partir de vraies conversations exportées (un `.txt` par conversation) :
   ```bash
   python simulate.py --generate 50 --from-transcripts exports/
   ```
   ```bash
   python simulate.py --personas personas.generated.json
   ```
   Chaque run est noté par contrôles fixes (statut du lead, handoff, escalade, désabonnement) et
   par un juge IA (langue, aucun fait inventé, ton, attentes). Itérer jusqu'à ce que tout passe.
   Ces runs appellent l'API Claude et sont donc facturés.
3. **Mise en production** avec un taux de reprise humaine élevé, à réduire au fil des preuves.
4. **Itérations mensuelles** : les escalades `knowledge_gap` du mois deviennent les ajouts à la
   base de connaissances du mois suivant. Rejouer `simulate.py` à chaque changement.

## Tests hors ligne

```bash
python -m pytest -q tests     # sans clé API : un faux client Claude simule le modèle
```

## Fichiers

| Fichier | Rôle |
|---|---|
| `app.py` | Serveur FastAPI : webhooks, API inbox, UI, planificateur |
| `agent/core.py` | Tour d'agent : rejoue l'historique, appelle Claude, exécute les outils |
| `agent/prompt.py` | Prompt système (rôle, langues, qualification, escalade, sécurité) |
| `agent/tools.py` | Définitions et exécution des outils |
| `knowledge/hestim_kb.md` | Base de connaissances HESTIM (à compléter) |
| `channels/meta.py` | Parsing des webhooks, signature, envoi WhatsApp / Instagram |
| `nurture.py` | Relances des prospects indécis |
| `db.py` | SQLite : contacts, conversations, messages, transcript, escalades |
| `simulate.py`, `personas.json` | Banc de test sur personas synthétiques |
| `static/inbox.html` | Interface équipe |
