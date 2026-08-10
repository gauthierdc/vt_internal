"""Supprime les Client/Server Scripts migrés vers le code de l'app.

Ces scripts (activés en prod au moment de la migration) ont été convertis en :
- fichiers JS (public/js/*.js) câblés via doctype_js / doctype_list_js ;
- modules Python (events/*.py, api/*.py, tasks.py) câblés via doc_events,
  override_whitelisted_methods et scheduler_events.

On supprime les records DB par NOM explicite pour éviter toute double-exécution.
Les scripts désactivés ne sont pas touchés. Idempotent (safe_delete ignore l'absence).
"""

import frappe

CLIENT_SCRIPTS = [
    "Bon de livraison",
    "Bon de livraison liste",
    "Bon pour accord liste",
    "Carte de travail",
    "Client",
    "Client liste",
    "Commande client",
    "Commande client liste",
    "Commande fournisseur",
    "Commande fournisseur liste",
    "Demande d'extraction de donnée via OCR",
    "Devis fournisseur",
    "Déclaration de production scanner",
    "Dépense",
    "Ecriture de paiement",
    "Fabrication VT",
    "Facture consolidée",
    "Facture d'achat en attente",
    "Facture d'achat en attente liste",
    "Facture de vente",
    "Facture de vente liste",
    "Facture fournisseur",
    "Factures d'achat",
    "Feuille de temps",
    "Feuille de temps liste",
    "Fiche de travail liste",
    "Fiche de travaux",
    "Incident qualité",
    "OCR Request list",
    "Objectif VT",
    "Order satisfaction",
    "Ordre de paiement",
    "Paramètres BMV",
    "Prix de forme",
    "Prix de forme liste",
    "Projet",
    "Reçu d'achat",
    "Reçu d'achat liste",
    "Réception de travaux",
    "Ticket liste",
    "Transaction bancaire",
    "VT Formulaire Verre Production",
    "Évenement",
]

SERVER_SCRIPTS = [
    "Après enregistrement",
    "Après validation des dépenses",
    "Article de la commande clien % reçu",
    "Article de la commande client % reçu sauv",
    "Avant l'impression",
    "Avant validation des dépenses",
    "Avant validation feuille de temps",
    "BL avant impression",
    "Before validate Commande fournisseur",
    "Bon pour accord devis",
    "Carte de travail Code bar",
    "Carte de travail VT",
    "Client récurrent",
    "Client sauvegarde",
    "Close billed projects",
    "Cocher livré sur bon de livraison",
    "Commande client annulation",
    "Commande client impression",
    "Commande client projet",
    "Commande fournisseur enregistrement",
    "Commande fournisseur enregistrement validé",
    "Commande fournisseur validation",
    "Compte de produit",
    "Coûts de fabrication du verre",
    "Coûts de fabrication du verre validation",
    "Date de livraison",
    "Date des dépense",
    "Demande de paiement",
    "Déclaration de production",
    "Dépense mail hebdomadaire",
    "En-tête Fiche de travail",
    "Evénement après la sauvegarde",
    "Evénement après la suppression",
    "Fabrication VT",
    "Facture d'achat en attente création",
    "Facture de vente ignore pricing rule",
    "Facture de vente à la création",
    "Feuille de temps annulation",
    "Feuille de temps arrondi",
    "Feuille de temps valeur par défaut",
    "Feuille de temps validation",
    "Fiche",
    "Fiche de travail avant l'annulation",
    "Fiche de travail status",
    "Fiche de travail status 2",
    "Fiche de travail status à la validation",
    "Formulaire Vision d'O Jetform",
    "Ignore pricing rule",
    "Impression fiche de travail",
    "Incident qualité sauvegarde",
    "Jetform VO",
    "Jotform create client",
    "Mise à jour des statuts de fabrication",
    "Mise à jour des statuts de fabrication dans la commande",
    "Montant restan dû",
    "Montant restant dû (avant sauvegarde)",
    "Nommage des clients",
    "Notes CRM Mail",
    "Nouvelle transaction bancaire",
    "Ordre de paiement",
    "Ouvrage avant la création",
    "Paiement devis reçu",
    "Purchase Order automation",
    "Rafraichir les termes",
    "Rapprochement transaction ordre de paiement",
    "Reçu d'achat validation",
    "Réception de travaux letter head",
    "Réception de travaux statut fiche de travail",
    "Sales Order automation",
    "Sauvegarde projet",
    "Statut de la commande client",
    "Statut de la commande client annulation",
    "Statut de la commande client validation",
    "Suppression",
    "Suppression Commande Client",
    "Titre employé",
    "Validation valide la fabrication",
    "change_company",
    "change_cost_center",
    "create_production",
    "generate_consolidate_sales_invoice",
    "new_fabrication",
    "new_visite_technique_from_quotation",
    "payment_link_from_sales_order",
    "sales_order_to_chantier_a_faire",
    "sms_delivery_note",
    "timesheet_html_block",
    "timesheet_post_api",
    "update_bmv_prices",
    "update_fiche_de_travail_status",
    "À créditer",
    "À créditer sauvegarde",
    "Évènement sync",
    "Événement avant la sauvegarde",
]


def safe_delete(doctype, name):
    try:
        frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
    except frappe.DoesNotExistError:
        pass


def execute():
    for name in SERVER_SCRIPTS:
        safe_delete("Server Script", name)
    for name in CLIENT_SCRIPTS:
        safe_delete("Client Script", name)
    frappe.logger().info(
        f"drop_migrated_scripts: {len(SERVER_SCRIPTS)} server + {len(CLIENT_SCRIPTS)} client scripts traités"
    )
