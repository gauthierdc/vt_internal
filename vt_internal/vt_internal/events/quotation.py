# vt_internal/quotation/events.py
import frappe

# ---------------------------------------------------------------------------
# Hooks Quotation : événements du document Quotation
# ---------------------------------------------------------------------------
# Chaque fonction est appelée à un moment clé du cycle de vie du document.
# Les hooks sont utilisés pour automatiser, valider, ou enrichir le document.

def autoname(doc, method=None):
    """Appelé lors de la génération du nom (avant insert)."""
    pass

def before_validate(doc, method=None):
    """Avant la validation du document (préparation)."""
    doc.flags.ignore_pricing_rule = True

def validate(doc, method=None):
    """Validations fonctionnelles avant sauvegarde."""
    pass

def before_insert(doc, method=None):
    """Avant l'insertion en base : concatène les termes du devis."""
    company_terms = frappe.db.get_value("Company", doc.company, "custom_quotation_terms") or ""
    cost_center_terms = frappe.db.get_value("Cost Center", doc.cost_center, "custom_quotation_terms") or ""
    doc.terms = f"{company_terms}\n{cost_center_terms}"

def after_insert(doc, method=None):
    """Juste après l'insertion en base."""
    pass

def _update_status_fields(doc):
    """
    Met à jour les champs de statut interne et le montant attendu.
    Utilisé dans before_save et before_update_after_submit.
    """
    if doc.custom_status_internes:
        last_status = doc.custom_status_internes[-1]
        doc.custom_dernier_statut_de_suivi = last_status.statut
        doc.custom_dernière_description_de_suivi = last_status.description

        if "perdu" in last_status.statut or "aband" in last_status.statut:
            doc.status = "Lost"
            doc.custom_probabilite_de_conversion = 0
            # doc.docstatus = 1  # à ne mettre que dans before_save si besoin
    else:
        doc.custom_dernier_statut_de_suivi = None
        doc.custom_dernière_description_de_suivi = None

    if doc.custom_probabilite_de_conversion is not None:
        doc.custom_expected_amount = doc.total * doc.custom_probabilite_de_conversion / 100

def before_save(doc, method=None):
    """
    Avant sauvegarde : met à jour le statut de suivi, la probabilité, le lien BPA, etc.
    """
    _update_status_fields(doc)
    # doc.docstatus = 1 est gardé ici pour le workflow
    if doc.status == "Lost":
        doc.docstatus = 1

    # Génération du lien BPA
    mobile = doc.contact_mobile or ""
    email = doc.contact_email or ""
    doc.custom_quotation_approval_link = (
        f"https://bureau.verretransparence.fr/bon-pour-accord-devis/new?"
        f"quotation={doc.name}&contact_mobile={mobile}&contact_email={email}"
    )

def before_print(doc, method=None):
    """
    Avant impression : calcule les poids, quantités et surfaces visibles.
    Met à jour les champs d'affichage et les prix par surface.
    """
    doc.weigth_of_visible_items = round(
        sum(i.total_weight for i in doc.items if i.row_print_style != "Hide Row" and i.row_type == ""), 1
    )
    doc.qty_of_visible_items = sum(
        i.qty for i in doc.items if i.row_print_style != "Hide Row" and i.row_type == ""
    )
    doc.surface_of_visible_items = 0

    for item in doc.items:
        if item.bom_no:
            bom = frappe.db.get_value("BOM", item.bom_no, ["reference_ligne", "hauteur", "largeur"])
            item.reference_ligne = bom[0]
            # Calcul du prix par surface
            surface = bom[1] / 1000 * bom[2] / 1000 if bom[1] and bom[2] else 0
            item.price_par_surface = round(item.rate / surface, 2) if surface else 0
            doc.surface_of_visible_items = round(
                doc.surface_of_visible_items + item.qty * surface, 2
            )

def after_save(doc, method=None):
    """Après sauvegarde complète."""
    pass

def before_submit(doc, method=None):
    """Juste avant soumission."""
    pass

def on_submit(doc, method=None):
    """Après soumission."""
    pass

def after_submit(doc, method=None):
    """Après soumission (hook complémentaire)."""
    pass

def before_cancel(doc, method=None):
    """Juste avant annulation."""
    pass

def on_cancel(doc, method=None):
    """Après annulation."""
    pass

def after_cancel(doc, method=None):
    """Après annulation (hook complémentaire)."""
    pass

def before_update_after_submit(doc, method=None):
    """
    Avant mise à jour d’un doc déjà soumis : met à jour le statut de suivi et le montant attendu.
    """
    _update_status_fields(doc)

def on_update_after_submit(doc, method=None):
    """Après mise à jour d’un doc déjà soumis."""
    pass

def before_delete(doc, method=None):
    """Juste avant suppression."""
    pass

def after_delete(doc, method=None):
    """Juste après suppression."""
    pass
