# Copyright (c) 2026, Verre & Transparence and contributors
# API du drawer d'événement (remplace le popover natif sur le calendrier Dokos).
#
#   - get_event_detail : détail enrichi (VT/FDT, adresse, téléphone) pour la modale

import frappe

# Couleur de repli par type quand l'Event n'a pas de couleur propre.
TYPE_COLORS = {
	"Public": "#1E88E5",
	"Private": "#7E57C2",
}
DEFAULT_COLOR = "#1E88E5"


def _color(color, event_type):
	return color or TYPE_COLORS.get(event_type) or DEFAULT_COLOR


def _compose_address(address_name):
	"""Adresse lisible sur une ligne depuis un doc Address."""
	if not address_name:
		return None
	a = frappe.db.get_value(
		"Address",
		address_name,
		["address_line1", "address_line2", "city", "pincode"],
		as_dict=True,
	)
	if not a:
		return None
	city_zip = f"{a.pincode} {a.city}".strip() if (a.pincode and a.city) else (a.city or a.pincode)
	parts = [a.address_line1, a.address_line2, city_zip]
	return ", ".join([p for p in parts if p]) or None


@frappe.whitelist()
def get_event_detail(name):
	"""Détail enrichi d'un Event pour la modale : dates, type, description, et
	infos de la Visite Technique / Fiche de travail liée (adresse, téléphone)."""
	doc = frappe.get_doc("Event", name)  # applique les permissions
	doc.check_permission("read")

	vt = doc.get("custom_visite_technique")
	fdt = doc.get("custom_fiche_de_travail")

	# Adresse + description LIÉE : depuis le doc de référence (FDT prioritaire, comme
	# le custom_html de l'Event). Téléphone : uniquement depuis la VT (le champ
	# n'existe pas forcément sur Fiche de travail).
	address_display = None
	phone = None
	linked_description = None
	if fdt and frappe.db.exists("Fiche de travail", fdt):
		r = frappe.db.get_value("Fiche de travail", fdt, ["address", "description"], as_dict=True) or {}
		address_display = _compose_address(r.get("address"))
		linked_description = r.get("description")
	elif vt and frappe.db.exists("Visite Technique", vt):
		r = frappe.db.get_value("Visite Technique", vt, ["address", "description"], as_dict=True) or {}
		address_display = _compose_address(r.get("address"))
		linked_description = r.get("description")

	if vt and frappe.db.exists("Visite Technique", vt):
		phone = frappe.db.get_value("Visite Technique", vt, "phone")

	return {
		"name": doc.name,
		"subject": doc.subject,
		"starts_on": str(doc.starts_on) if doc.starts_on else None,
		"ends_on": str(doc.ends_on) if doc.ends_on else None,
		"all_day": bool(doc.all_day),
		"event_type": doc.event_type,
		"color": _color(doc.color, doc.event_type),
		"event_description": doc.description or "",
		"linked_description": linked_description or "",
		"vt": vt,
		"fdt": fdt,
		"address_display": address_display,
		"phone": phone,
	}
