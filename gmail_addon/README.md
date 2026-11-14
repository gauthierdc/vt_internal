# Add-on Gmail — fiche client et fournisseur

Panneau latéral Gmail : à l'ouverture d'un e-mail, l'add-on interroge ERPNext et affiche le client et/ou le fournisseur qui correspondent à l'expéditeur, avec les derniers devis, commandes et factures.

L'API ne fait aucune écriture. Elle ne renvoie que ce que l'utilisateur API a le droit de lire.

## Endpoint

```
GET /api/method/vt_internal.vt_internal.api.gmail.lookup_by_email?email=jean.dupont@exemple.fr
Authorization: token <api_key>:<api_secret>
```

Frappe enveloppe la réponse dans `{"message": { ... }}`. Le contrat complet (clés, `match_type`, agrégats, repli par domaine) est la docstring de `lookup_by_email` dans `vt_internal/vt_internal/api/gmail.py`.

Sans correspondance, les listes sont vides et `match_type` vaut `null`. Ce n'est pas une erreur.

Exemple (objet `message`, client et fournisseur pour la même adresse) :

```json
{
  "email": "compta@exemple.fr",
  "normalized_email": "compta@exemple.fr",
  "domain": "exemple.fr",
  "generic_domain": false,
  "match_type": "exact",
  "truncated": false,
  "customers": [
    {
      "doctype": "Customer",
      "name": "CUST-0001",
      "customer_name": "Dupont SA",
      "customer_group": "Commercial",
      "territory": "France",
      "phone": "0490112233",
      "mobile": "0611223344",
      "email": "compta@exemple.fr",
      "disabled": false,
      "url": "https://bureau.verretransparence.fr/app/customer/CUST-0001",
      "match_sources": ["contact"],
      "contacts": [
        {
          "doctype": "Contact",
          "name": "CONTACT-0001",
          "full_name": "Jean Dupont",
          "email": "compta@exemple.fr",
          "emails": ["compta@exemple.fr"],
          "phone": "0490112233",
          "mobile": "0611223344",
          "url": "https://bureau.verretransparence.fr/app/contact/CONTACT-0001"
        }
      ],
      "quotations": [
        {
          "doctype": "Quotation",
          "name": "DEV-26-00042",
          "date": "2026-11-02",
          "status": "Open",
          "docstatus": 1,
          "grand_total": 1840.0,
          "currency": "EUR",
          "company": "Miroiterie Avignonnaise",
          "url": "https://bureau.verretransparence.fr/app/quotation/DEV-26-00042"
        }
      ],
      "sales_orders": [],
      "sales_invoices": [],
      "aggregates": {
        "outstanding_amount": 920.0,
        "unpaid_invoice_count": 1,
        "open_order_count": 0,
        "open_order_total": 0.0
      }
    }
  ],
  "suppliers": [
    {
      "doctype": "Supplier",
      "name": "SUP-0001",
      "supplier_name": "Verrier du Sud",
      "supplier_group": "Vitrage",
      "phone": null,
      "mobile": null,
      "email": "compta@exemple.fr",
      "disabled": false,
      "url": "https://bureau.verretransparence.fr/app/supplier/SUP-0001",
      "match_sources": ["supplier_email"],
      "contacts": [],
      "supplier_quotations": [],
      "purchase_orders": [
        {
          "doctype": "Purchase Order",
          "name": "CFA-26-00018",
          "date": "2026-11-10",
          "status": "Draft",
          "docstatus": 0,
          "grand_total": 640.0,
          "currency": "EUR",
          "company": "Vitrerie Stéphanoise",
          "url": "https://bureau.verretransparence.fr/app/purchase-order/CFA-26-00018"
        }
      ],
      "purchase_invoices": [
        {
          "doctype": "Purchase Invoice",
          "name": "FFA-26-00007",
          "date": "2026-10-28",
          "status": "Unpaid",
          "docstatus": 1,
          "grand_total": 1200.0,
          "currency": "EUR",
          "company": "Vitrerie Stéphanoise",
          "bill_no": "FAC-2026-441",
          "url": "https://bureau.verretransparence.fr/app/purchase-invoice/FFA-26-00007"
        }
      ],
      "aggregates": {
        "open_purchase_order_count": 1,
        "open_purchase_order_total": 2100.0,
        "amount_to_receive": 1050.0,
        "unpaid_invoice_count": 1,
        "outstanding_amount": 1200.0
      }
    }
  ],
  "leads": [],
  "unlinked_contacts": [],
  "create": {
    "contact": "https://bureau.verretransparence.fr/app/contact/new?email_id=compta%40exemple.fr",
    "customer": "https://bureau.verretransparence.fr/app/customer/new",
    "supplier": "https://bureau.verretransparence.fr/app/supplier/new?email_id=compta%40exemple.fr"
  }
}
```

```bash
curl -s -G "https://bureau.verretransparence.fr/api/method/vt_internal.vt_internal.api.gmail.lookup_by_email" \
  --data-urlencode "email=jean.dupont@exemple.fr" \
  -H "Authorization: token ${ERP_API_KEY}:${ERP_API_SECRET}"
```

Correspondance :

1. Adresse exacte (insensible à la casse) sur le contact, le client, le fournisseur, la piste et l'adresse.
2. Sinon, domaine de l'adresse (`match_type: "domain"`), sauf webmail et FAI grand public (`gmail.com`, `hotmail.fr`, `orange.fr`, `free.fr`, `wanadoo.fr`, `yahoo.*`, `outlook.*`, `icloud.com`, `laposte.net`, `sfr.fr`, et les alias `googlemail.com`, `live.*`, `me.com`).

Une même adresse peut renvoyer un client et un fournisseur. Les deux sont typés (`doctype`).

## 1. Utilisateur API en lecture seule

Sur https://bureau.verretransparence.fr, avec un compte System Manager :

1. **Utilisateur** : créer un utilisateur système, par exemple `gmail-addon@verretransparence.fr`. Ne pas lui donner le rôle System Manager. Décocher l'envoi de l'e-mail de bienvenue si vous n'en avez pas besoin.
2. **Rôle** : créer un rôle `Gmail Add-on` et ne lui donner **que** Lecture (et Sélection, si la case existe) sur :

   | DocType | Pour |
   | --- | --- |
   | Contact, Address | retrouver la personne et ses liens |
   | Customer, Lead | fiche client, piste |
   | Quotation, Sales Order, Sales Invoice | devis, commandes, factures |
   | Supplier | fiche fournisseur |
   | Supplier Quotation, Purchase Order, Purchase Invoice | devis, commandes et factures fournisseur |

   Pas de Créer, Écrire, Soumettre, Annuler ni Supprimer. L'API ne s'en sert pas, et la clé ne doit pas pouvoir le faire non plus.
3. Assigner **uniquement** ce rôle à l'utilisateur.
4. **Autorisations utilisateur** (restriction par société) : les laisser vides si le panneau doit voir MAV, VS, EDC et les autres sociétés. Une restriction Société masque les documents des autres sociétés, y compris dans cet add-on.
5. Sur la fiche utilisateur, section **Accès API** : **Générer des clés**. Copier le secret tout de suite : il ne s'affiche qu'une fois. La clé reste visible.

Vérifier avec le `curl` ci-dessus qu'une adresse connue renvoie un client ou un fournisseur, et qu'une adresse inconnue renvoie des listes vides.

## 2. Projet Apps Script

1. Ouvrir [script.google.com](https://script.google.com) avec le compte Google Workspace qui utilisera l'add-on, puis **Nouveau projet**.
2. Renommer le projet, par exemple `VT Gmail ERP`.
3. Coller `Code.gs` à la place du fichier par défaut.
4. Afficher le fichier manifeste (`Paramètres du projet` → cocher `Afficher le fichier manifeste appsscript.json`) et remplacer son contenu par `appsscript.json`.
5. Remplacer `logoUrl` par une image HTTPS publique de la société (environ 96×96) avant une installation plus large. L'icône actuelle est un placeholder Apps Script.
6. `urlFetchWhitelist` et `openLinkUrlPrefixes` sont limités à `https://bureau.verretransparence.fr/`. Si `ERP_BASE_URL` change d'hôte, ajouter ce préfixe aux deux listes.

## 3. Propriétés du script

`Paramètres du projet` → `Propriétés du script` :

| Propriété | Valeur |
| --- | --- |
| `ERP_API_KEY` | clé API |
| `ERP_API_SECRET` | secret API |
| `ERP_BASE_URL` | optionnel, `https://bureau.verretransparence.fr` |

Ne pas coller le secret dans `Code.gs`, le manifeste ou un dépôt.

## 4. Déployer en add-on de test

1. **Déployer** → **Déploiements de test**.
2. Type **Module complémentaire de l'éditeur**, puis **Installer**.
3. Autoriser les scopes demandés (lire le message ouvert, appeler un service externe).
4. Ouvrir Gmail, ouvrir un message. Le panneau **Verre Transparence** affiche la fiche, ou les boutons **Créer le contact**, **Créer le client** et **Créer le fournisseur** si rien ne correspond. Le contact et le fournisseur sont préremplis avec l'adresse (`email_id`). Le client ne l'est pas : son e-mail est recopié du contact principal.

Le déclencheur contextuel est `onGmailMessage`. Sans message ouvert, la page d'accueil rappelle d'en ouvrir un.

Pour les autres comptes du domaine, il faudra ensuite une fiche du SDK Google Workspace Marketplace en visibilité interne. Le déploiement de test suffit pour valider le panneau.
