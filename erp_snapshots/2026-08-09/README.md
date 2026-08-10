# Snapshot ERP — scripts — 2026-08-09

Export brut des **scripts** de la prod (`bureau.verretransparence.fr`), récupéré via l'API
ERPNext le 2026-08-09, juste avant leur conversion en code. Ces records ayant été
**supprimés de la base** (convertis en code app), ce dossier est leur **seule archive**.

| Fichier | DocType | Contenu | Statut dans l'app |
|---|---|---|---|
| `client_script.json` | Client Script | 50 (activés + désactivés) | Activés convertis en `public/js/*.js` |
| `server_script.json` | Server Script | 103 (tous) | Activés convertis en `events/`, `api/`, `tasks/` |

Format : sortie brute de l'API (`GET /api/resource/<DocType>?fields=["*"]`), un objet JSON
par record, tous les champs conservés (owner, creation, etc.) à des fins d'audit.

**Champs personnalisés : volontairement pas archivés ici.** Ils ne sont pas supprimés (ils
restent vivants en base, édités via l'interface) — un instantané serait redondant et périmé.
La sauvegarde de la base fait office de filet pour eux.

> Archive figée : non rejouée au `migrate`.
