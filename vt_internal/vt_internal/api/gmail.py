# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt
#
# Lecture seule pour l'add-on Gmail : fiche client / fournisseur à partir
# de l'adresse de l'expéditeur. Aucun écriture, aucun hook.

from __future__ import annotations

import re
from urllib.parse import quote

import frappe

# Derniers documents affichés par type, et plafond du panneau.
RECENT_LIMIT = 5
MAX_PARTIES = 5
MAX_CONTACTS = 20
MAX_AGGREGATE_ROWS = 2000

# Webmails et FAI grand public. Pas de repli par domaine : deux inconnus
# @gmail.com ne sont pas la même société. Les préfixes couvrent yahoo.*,
# outlook.*, hotmail.* et live.* (aliases du même service).
GENERIC_EMAIL_DOMAINS = frozenset(
	{
		"gmail.com",
		"googlemail.com",
		"hotmail.com",
		"hotmail.fr",
		"orange.fr",
		"free.fr",
		"wanadoo.fr",
		"icloud.com",
		"me.com",
		"mac.com",
		"laposte.net",
		"sfr.fr",
	}
)
GENERIC_EMAIL_DOMAIN_PREFIXES = ("yahoo.", "outlook.", "hotmail.", "live.")

# Statuts stockés en anglais (options Select ERPNext), pas le libellé traduit.
OPEN_SALES_ORDER_STATUSES = ("To Deliver and Bill", "To Bill", "To Deliver", "On Hold")
OPEN_PURCHASE_ORDER_STATUSES = ("To Receive and Bill", "To Bill", "To Receive", "On Hold")
# Encore de la marchandise à réceptionner. « To Bill » est déjà réceptionné.
RECEIVABLE_PURCHASE_ORDER_STATUSES = ("To Receive and Bill", "To Receive", "On Hold")

PARTY_DOCTYPES = ("Customer", "Supplier", "Lead")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ANGLE_ADDRESS = re.compile(r"<([^>]+)>")

CONTACT_FIELDS = [
	"name",
	"full_name",
	"first_name",
	"last_name",
	"email_id",
	"phone",
	"mobile_no",
	"`tabContact Email`.email_id as matched_email",
]
CUSTOMER_FIELDS = [
	"name",
	"customer_name",
	"customer_group",
	"territory",
	"email_id",
	"mobile_no",
	"disabled",
]
SUPPLIER_FIELDS = [
	"name",
	"supplier_name",
	"supplier_group",
	"email_id",
	"mobile_no",
	"disabled",
]
LEAD_FIELDS = [
	"name",
	"lead_name",
	"company_name",
	"status",
	"email_id",
	"phone",
	"mobile_no",
]


@frappe.whitelist(methods=["GET"])
def lookup_by_email(email=None):
	"""Retourne la fiche ERP de l'expéditeur. Lecture seule, aucune écriture.

	GET /api/method/vt_internal.vt_internal.api.gmail.lookup_by_email?email=
	Authorization: token <api_key>:<api_secret>

	Frappe enveloppe le retour dans ``{"message": <cet objet>}``.

	L'adresse est normalisée (minuscules, forme ``Nom <adresse>`` acceptée).
	Sans correspondance, les listes sont vides et ``match_type`` vaut ``null`` :
	ce n'est pas une erreur. Une adresse invalide donne le même objet vide,
	avec ``create`` à ``null``.

	Correspondance, dans l'ordre :

	1. Exacte, insensible à la casse (collation ``*_ci`` du site) sur
	   Contact Email, ``Contact.email_id``, ``Customer.email_id``,
	   ``Supplier.email_id``, ``Lead.email_id`` et ``Address.email_id``.
	   Les liens dynamiques rattachent le contact ou l'adresse au client,
	   au fournisseur ou à la piste.
	2. Sinon, et seulement si le domaine n'est pas un webmail / FAI listé
	   dans ``GENERIC_EMAIL_DOMAINS``, repli sur le domaine exact
	   (``match_type`` = ``"domain"``). ``user@notexemple.fr`` ne correspond
	   pas à ``exemple.fr``.

	Une même adresse peut renvoyer un client et un fournisseur. Les droits
	de l'utilisateur API s'appliquent (``has_permission`` + ``get_list``) :
	un DocType illisible est simplement absent, sans lever d'erreur.

	Les listes récentes incluent les brouillons (``docstatus`` 0) et les
	documents validés (1), pas les annulés (2). Les agrégats « ouverts »
	ne comptent que les documents validés encore ouverts.

	``amount_to_receive`` est une estimation TTC : somme, sur les commandes
	fournisseur ouvertes encore à réceptionner (statuts To Receive and Bill,
	To Receive, On Hold), de ``grand_total * (100 - per_received) / 100``.
	``per_received`` est un pourcentage de quantité. Pas de conversion de
	devise : les sommes additionnent les montants enregistrés.

	Forme::

	    {
	        "email": "Jean <jean.dupont@exemple.fr>",
	        "normalized_email": "jean.dupont@exemple.fr",
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
	                "phone": "04 90 00 00 00",
	                "mobile": "06 00 00 00 00",
	                "email": "jean.dupont@exemple.fr",
	                "disabled": false,
	                "url": "https://bureau.verretransparence.fr/app/customer/CUST-0001",
	                "match_sources": ["contact", "customer_email"],
	                "contacts": [
	                    {
	                        "doctype": "Contact",
	                        "name": "CONTACT-0001",
	                        "full_name": "Jean Dupont",
	                        "email": "jean.dupont@exemple.fr",
	                        "emails": ["jean.dupont@exemple.fr"],
	                        "phone": "04 90 00 00 00",
	                        "mobile": "06 00 00 00 00",
	                        "url": "https://bureau.verretransparence.fr/app/contact/CONTACT-0001",
	                    }
	                ],
	                "quotations": [DOCUMENT],
	                "sales_orders": [DOCUMENT],
	                "sales_invoices": [DOCUMENT],
	                "aggregates": {
	                    "outstanding_amount": 1230.0,
	                    "unpaid_invoice_count": 2,
	                    "open_order_count": 1,
	                    "open_order_total": 4500.0,
	                },
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
	                "email": "arc@verrier.example",
	                "disabled": false,
	                "url": "https://bureau.verretransparence.fr/app/supplier/SUP-0001",
	                "match_sources": ["contact"],
	                "contacts": [],
	                "supplier_quotations": [DOCUMENT],
	                "purchase_orders": [DOCUMENT],
	                "purchase_invoices": [DOCUMENT_ACHAT],
	                "aggregates": {
	                    "open_purchase_order_count": 2,
	                    "open_purchase_order_total": 8000.0,
	                    "amount_to_receive": 5000.0,
	                    "unpaid_invoice_count": 1,
	                    "outstanding_amount": 1200.0,
	                },
	            }
	        ],
	        "leads": [
	            {
	                "doctype": "Lead",
	                "name": "CRM-LEAD-0001",
	                "lead_name": "Jean Dupont",
	                "company_name": "Dupont SA",
	                "status": "Open",
	                "email": "jean.dupont@exemple.fr",
	                "phone": null,
	                "mobile": null,
	                "url": "https://bureau.verretransparence.fr/app/lead/CRM-LEAD-0001",
	                "match_sources": ["lead_email"],
	                "contacts": [],
	            }
	        ],
	        "unlinked_contacts": [],
	        "create": {
	            "contact": "https://bureau.verretransparence.fr/app/contact/new?email_id=jean.dupont%40exemple.fr",
	            "customer": "https://bureau.verretransparence.fr/app/customer/new",
	            "supplier": "https://bureau.verretransparence.fr/app/supplier/new?email_id=jean.dupont%40exemple.fr",
	        },
	    }

	``DOCUMENT`` : ``doctype``, ``name``, ``date`` (ISO), ``status``,
	``docstatus``, ``grand_total``, ``currency``, ``company``, ``url``.
	``DOCUMENT_ACHAT`` (facture fournisseur) ajoute ``bill_no``.
	``match_sources`` : ``contact``, ``address``, ``customer_email``,
	``supplier_email``, ``lead_email``.
	"""
	raw = _raw_email(email)
	normalized = normalize_email(raw)
	if not normalized:
		return empty_result(raw)

	domain = email_domain(normalized)
	generic = is_generic_domain(domain)
	exact = _search(normalized, "exact")
	if _has_hit(exact):
		return _build(raw, normalized, domain, generic, "exact", exact)
	if not domain or generic:
		return empty_result(raw, normalized, domain, generic)

	by_domain = _search(domain, "domain")
	if not _has_hit(by_domain):
		return empty_result(raw, normalized, domain, generic)
	return _build(raw, normalized, domain, generic, "domain", by_domain)


def normalize_email(value):
	"""Adresse exploitable en minuscules, ou chaîne vide."""
	if value is None:
		return ""
	if isinstance(value, (list, tuple)):
		value = value[0] if value else ""
	raw = str(value).strip()
	if not raw:
		return ""
	match = _ANGLE_ADDRESS.search(raw)
	if match:
		raw = match.group(1).strip()
	raw = raw.strip().strip("<>").lower()
	if raw.startswith("mailto:"):
		raw = raw[7:].strip()
	if len(raw) > 254 or not _EMAIL_RE.fullmatch(raw):
		return ""
	return raw


def email_domain(email):
	"""Domaine d'une adresse, ou le domaine lui-même s'il est déjà nu."""
	if not email:
		return ""
	text = str(email).strip().lower().rstrip(".")
	if "@" in text:
		text = text.rsplit("@", 1)[1]
	if not text or "." not in text or "@" in text:
		return ""
	if any(char in text for char in " \t/%\\"):
		return ""
	return text


def is_generic_domain(domain):
	"""Webmail ou FAI : le repli par domaine regrouperait des inconnus."""
	domain = email_domain(domain) if domain and "@" in str(domain) else (domain or "")
	domain = str(domain).strip().lower().rstrip(".")
	if not domain:
		return False
	if domain in GENERIC_EMAIL_DOMAINS:
		return True
	return any(domain.startswith(prefix) for prefix in GENERIC_EMAIL_DOMAIN_PREFIXES)


def empty_result(raw, normalized="", domain="", generic=False):
	return _envelope(raw, normalized, domain, generic, None, False, [], [], [], [])


def _raw_email(email):
	if email is None:
		return ""
	if isinstance(email, (list, tuple)):
		return "" if not email else str(email[0])
	return str(email)


def _envelope(raw, normalized, domain, generic, match_type, truncated, customers, suppliers, leads, unlinked):
	return {
		"email": raw,
		"normalized_email": normalized or None,
		"domain": domain or None,
		"generic_domain": bool(generic),
		"match_type": match_type,
		"truncated": bool(truncated),
		"customers": customers,
		"suppliers": suppliers,
		"leads": leads,
		"unlinked_contacts": unlinked,
		"create": _create_urls(normalized) if normalized else None,
	}


def _create_urls(email):
	base = frappe.utils.get_url().rstrip("/")
	quoted = quote(email, safe="")
	return {
		"contact": f"{base}/app/contact/new?email_id={quoted}",
		"customer": f"{base}/app/customer/new",
		"supplier": f"{base}/app/supplier/new?email_id={quoted}",
	}


def _form_url(doctype, name):
	if not name:
		return None
	return frappe.utils.get_url_to_form(doctype, name)


def _has_hit(found):
	if found["contacts"] or found["customer_names"] or found["supplier_names"] or found["lead_names"]:
		return True
	return bool(found["address_links"])


def _search(needle, mode):
	contacts, truncated = _find_contacts(needle, mode)
	contact_links = _links("Contact", [contact["name"] for contact in contacts])
	addresses, address_truncated = _find_addresses(needle, mode)
	address_links = _links("Address", [address["name"] for address in addresses])
	return {
		"truncated": truncated or address_truncated,
		"contacts": contacts,
		"contact_links": contact_links,
		"addresses": addresses,
		"address_links": address_links,
		"customer_names": _find_party_names("Customer", needle, mode),
		"supplier_names": _find_party_names("Supplier", needle, mode),
		"lead_names": _find_party_names("Lead", needle, mode),
	}


def _find_contacts(needle, mode):
	if not _can_read("Contact"):
		return [], False
	operator, value = _email_operator(needle, mode)
	rows = _get_list(
		"Contact",
		or_filters=[
			["Contact Email", "email_id", operator, value],
			["email_id", operator, value],
		],
		fields=CONTACT_FIELDS,
		limit_page_length=MAX_CONTACTS * 4,
	)
	truncated = len(rows) >= MAX_CONTACTS * 4
	merged = {}
	order = []
	for row in rows:
		matched = row.get("matched_email") or ""
		parent_email = row.get("email_id") or ""
		matched_ok = _email_ok(matched, needle, mode)
		parent_ok = _email_ok(parent_email, needle, mode)
		if not matched_ok and not parent_ok:
			continue
		name = row.get("name")
		if not name:
			continue
		if name not in merged:
			merged[name] = {
				"name": name,
				"full_name": row.get("full_name"),
				"first_name": row.get("first_name"),
				"last_name": row.get("last_name"),
				"email_id": parent_email or None,
				"phone": row.get("phone"),
				"mobile_no": row.get("mobile_no"),
				"matched_emails": [],
			}
			order.append(name)
		bucket = merged[name]
		if matched_ok:
			_append_email(bucket, matched)
		if parent_ok:
			_append_email(bucket, parent_email)
	if len(order) > MAX_CONTACTS:
		truncated = True
		order = order[:MAX_CONTACTS]
	return [merged[name] for name in order], truncated


def _find_addresses(needle, mode):
	if not _can_read("Address"):
		return [], False
	operator, value = _email_operator(needle, mode)
	filters = {"email_id": value} if operator == "=" else {"email_id": [operator, value]}
	rows = _get_list(
		"Address",
		filters=filters,
		fields=["name", "email_id", "phone", "address_title"],
		limit_page_length=MAX_CONTACTS * 2,
	)
	kept = []
	for row in rows:
		if not row.get("name") or not _email_ok(row.get("email_id"), needle, mode):
			continue
		kept.append(row)
		if len(kept) >= MAX_CONTACTS:
			return kept, True
	return kept, len(rows) >= MAX_CONTACTS * 2


def _find_party_names(doctype, needle, mode):
	if not _can_read(doctype):
		return []
	operator, value = _email_operator(needle, mode)
	filters = {"email_id": value} if operator == "=" else {"email_id": [operator, value]}
	rows = _get_list(
		doctype,
		filters=filters,
		fields=["name", "email_id"],
		limit_page_length=MAX_PARTIES * 4,
	)
	names = []
	for row in rows:
		name = row.get("name")
		if not name or not _email_ok(row.get("email_id"), needle, mode):
			continue
		if name not in names:
			names.append(name)
	return names


def _email_operator(needle, mode):
	if mode == "exact":
		return "=", needle
	return "like", _domain_like(needle)


def _domain_like(domain):
	escaped = domain.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
	return f"%@{escaped}"


def _email_ok(value, needle, mode):
	if not value or not needle:
		return False
	if mode == "exact":
		return _emails_equal(value, needle)
	return email_domain(value) == needle


def _emails_equal(left, right):
	if not left or not right or "@" not in str(left):
		return False
	return str(left).strip().lower() == str(right).strip().lower()


def _append_email(bucket, value):
	if not value:
		return
	lowered = str(value).strip().lower()
	if lowered in {item.lower() for item in bucket["matched_emails"]}:
		return
	bucket["matched_emails"].append(str(value).strip())


def _links(parenttype, names):
	if not names or not _can_read(parenttype):
		return []
	rows = _get_list(
		parenttype,
		filters={"name": ["in", names]},
		fields=[
			"name",
			"`tabDynamic Link`.link_doctype as link_doctype",
			"`tabDynamic Link`.link_name as link_name",
		],
		limit_page_length=max(len(names) * 8, 1),
	)
	links = []
	seen = set()
	for row in rows:
		link_doctype = row.get("link_doctype")
		link_name = row.get("link_name")
		parent = row.get("name")
		if link_doctype not in PARTY_DOCTYPES or not link_name or not parent:
			continue
		key = (parent, link_doctype, link_name)
		if key in seen:
			continue
		seen.add(key)
		links.append({"parent": parent, "link_doctype": link_doctype, "link_name": link_name})
	return links


def _build(raw, normalized, domain, generic, match_type, found):
	contacts = {contact["name"]: contact for contact in found["contacts"]}
	addresses = {address["name"]: address for address in found["addresses"]}
	customer_acc, supplier_acc, lead_acc = _accumulate(found)

	customers = _load_docs("Customer", list(customer_acc), CUSTOMER_FIELDS)
	suppliers = _load_docs("Supplier", list(supplier_acc), SUPPLIER_FIELDS)
	leads = _load_docs("Lead", list(lead_acc), LEAD_FIELDS)

	customer_names = _ordered(customer_acc, customers, "customer_name")
	supplier_names = _ordered(supplier_acc, suppliers, "supplier_name")
	lead_names = _ordered(lead_acc, leads, "lead_name")
	truncated = found["truncated"]
	if (
		len(customer_names) > MAX_PARTIES
		or len(supplier_names) > MAX_PARTIES
		or len(lead_names) > MAX_PARTIES
	):
		truncated = True
	customer_names = customer_names[:MAX_PARTIES]
	supplier_names = supplier_names[:MAX_PARTIES]
	lead_names = lead_names[:MAX_PARTIES]

	customer_blocks = [
		_customer_block(name, customers[name], customer_acc[name], contacts, addresses)
		for name in customer_names
	]
	supplier_blocks = [
		_supplier_block(name, suppliers[name], supplier_acc[name], contacts, addresses)
		for name in supplier_names
	]
	lead_blocks = [_lead_block(name, leads[name], lead_acc[name], contacts, addresses) for name in lead_names]

	linked_contact_ids = set()
	for bucket, names in (
		(customer_acc, customer_names),
		(supplier_acc, supplier_names),
		(lead_acc, lead_names),
	):
		for name in names:
			linked_contact_ids.update(bucket[name]["contacts"])
	# Aussi les contacts des fiches lisibles mais non rendues (plafond) :
	# ils ne sont pas « sans fiche ».
	for bucket, loaded in ((customer_acc, customers), (supplier_acc, suppliers), (lead_acc, leads)):
		for name in bucket:
			if name in loaded:
				linked_contact_ids.update(bucket[name]["contacts"])

	unlinked = [
		_public_contact(contact) for name, contact in contacts.items() if name not in linked_contact_ids
	]
	return _envelope(
		raw,
		normalized,
		domain,
		generic,
		match_type,
		truncated,
		customer_blocks,
		supplier_blocks,
		lead_blocks,
		unlinked,
	)


def _accumulate(found):
	customers, suppliers, leads = {}, {}, {}
	buckets = {"Customer": customers, "Supplier": suppliers, "Lead": leads}

	def touch(doctype, name, source, contact_id=None, address_id=None):
		if not name or doctype not in buckets:
			return
		entry = buckets[doctype].setdefault(name, {"sources": set(), "contacts": [], "addresses": []})
		entry["sources"].add(source)
		if contact_id and contact_id not in entry["contacts"]:
			entry["contacts"].append(contact_id)
		if address_id and address_id not in entry["addresses"]:
			entry["addresses"].append(address_id)

	for link in found["contact_links"]:
		touch(link["link_doctype"], link["link_name"], "contact", contact_id=link["parent"])
	for link in found["address_links"]:
		touch(link["link_doctype"], link["link_name"], "address", address_id=link["parent"])
	for name in found["customer_names"]:
		touch("Customer", name, "customer_email")
	for name in found["supplier_names"]:
		touch("Supplier", name, "supplier_email")
	for name in found["lead_names"]:
		touch("Lead", name, "lead_email")
	return customers, suppliers, leads


def _ordered(bucket, loaded, label_field):
	names = [name for name in bucket if name in loaded]
	names.sort(key=lambda name: ((loaded[name].get(label_field) or "").lower(), name))
	return names


def _load_docs(doctype, names, fields):
	if not names or not _can_read(doctype):
		return {}
	rows = _get_list(
		doctype,
		filters={"name": ["in", names]},
		fields=fields,
		limit_page_length=max(len(names), 1),
	)
	return {row["name"]: row for row in rows if row.get("name")}


def _customer_block(name, row, acc, contacts, addresses):
	raw_contacts = [contacts[cid] for cid in acc["contacts"] if cid in contacts]
	raw_addresses = [addresses[aid] for aid in acc["addresses"] if aid in addresses]
	phone, mobile = _phones(row, raw_contacts, raw_addresses)
	return {
		"doctype": "Customer",
		"name": name,
		"customer_name": row.get("customer_name") or name,
		"customer_group": row.get("customer_group") or None,
		"territory": row.get("territory") or None,
		"phone": phone,
		"mobile": mobile,
		"email": _party_email(row, raw_contacts),
		"disabled": _flag(row.get("disabled")),
		"url": _form_url("Customer", name),
		"match_sources": sorted(acc["sources"]),
		"contacts": [_public_contact(contact) for contact in raw_contacts],
		"quotations": _recent(
			"Quotation",
			{"party_name": name, "quotation_to": "Customer", "docstatus": ["<", 2]},
			"transaction_date",
		),
		"sales_orders": _recent(
			"Sales Order",
			{"customer": name, "docstatus": ["<", 2]},
			"transaction_date",
		),
		"sales_invoices": _recent(
			"Sales Invoice",
			{"customer": name, "docstatus": ["<", 2]},
			"posting_date",
		),
		"aggregates": _sales_aggregates(name),
	}


def _supplier_block(name, row, acc, contacts, addresses):
	raw_contacts = [contacts[cid] for cid in acc["contacts"] if cid in contacts]
	raw_addresses = [addresses[aid] for aid in acc["addresses"] if aid in addresses]
	phone, mobile = _phones(row, raw_contacts, raw_addresses)
	return {
		"doctype": "Supplier",
		"name": name,
		"supplier_name": row.get("supplier_name") or name,
		"supplier_group": row.get("supplier_group") or None,
		"phone": phone,
		"mobile": mobile,
		"email": _party_email(row, raw_contacts),
		"disabled": _flag(row.get("disabled")),
		"url": _form_url("Supplier", name),
		"match_sources": sorted(acc["sources"]),
		"contacts": [_public_contact(contact) for contact in raw_contacts],
		"supplier_quotations": _recent(
			"Supplier Quotation",
			{"supplier": name, "docstatus": ["<", 2]},
			"transaction_date",
		),
		"purchase_orders": _recent(
			"Purchase Order",
			{"supplier": name, "docstatus": ["<", 2]},
			"transaction_date",
		),
		"purchase_invoices": _recent(
			"Purchase Invoice",
			{"supplier": name, "docstatus": ["<", 2]},
			"posting_date",
			["bill_no"],
		),
		"aggregates": _purchase_aggregates(name),
	}


def _lead_block(name, row, acc, contacts, addresses):
	raw_contacts = [contacts[cid] for cid in acc["contacts"] if cid in contacts]
	raw_addresses = [addresses[aid] for aid in acc["addresses"] if aid in addresses]
	phone, mobile = _phones(row, raw_contacts, raw_addresses)
	return {
		"doctype": "Lead",
		"name": name,
		"lead_name": row.get("lead_name") or name,
		"company_name": row.get("company_name") or None,
		"status": row.get("status") or None,
		"email": _party_email(row, raw_contacts),
		"phone": phone,
		"mobile": mobile,
		"url": _form_url("Lead", name),
		"match_sources": sorted(acc["sources"]),
		"contacts": [_public_contact(contact) for contact in raw_contacts],
	}


def _public_contact(row):
	emails = list(row.get("matched_emails") or [])
	label = (row.get("full_name") or "").strip()
	if not label:
		label = " ".join(part for part in (row.get("first_name"), row.get("last_name")) if part).strip()
	return {
		"doctype": "Contact",
		"name": row.get("name"),
		"full_name": label or row.get("name"),
		"email": emails[0] if emails else _blank(row.get("email_id")),
		"emails": emails,
		"phone": _blank(row.get("phone")),
		"mobile": _blank(row.get("mobile_no")),
		"url": _form_url("Contact", row.get("name")),
	}


def _party_email(row, raw_contacts):
	email = _blank(row.get("email_id"))
	if email:
		return email
	for contact in raw_contacts:
		emails = contact.get("matched_emails") or []
		if emails:
			return emails[0]
		if contact.get("email_id"):
			return contact["email_id"]
	return None


def _phones(party_row, raw_contacts, raw_addresses):
	"""Le contact qui a écrit, puis la fiche, puis l'adresse."""
	phone = None
	mobile = None
	for contact in raw_contacts:
		phone = phone or _blank(contact.get("phone"))
		mobile = mobile or _blank(contact.get("mobile_no"))
	phone = phone or _blank(party_row.get("phone"))
	mobile = mobile or _blank(party_row.get("mobile_no"))
	for address in raw_addresses:
		phone = phone or _blank(address.get("phone"))
	return phone, mobile


def _sales_aggregates(customer):
	invoices = _get_list(
		"Sales Invoice",
		filters={"customer": customer, "docstatus": 1, "outstanding_amount": [">", 0]},
		fields=["outstanding_amount"],
		limit_page_length=MAX_AGGREGATE_ROWS,
	)
	orders = _get_list(
		"Sales Order",
		filters={
			"customer": customer,
			"docstatus": 1,
			"status": ["in", list(OPEN_SALES_ORDER_STATUSES)],
		},
		fields=["grand_total"],
		limit_page_length=MAX_AGGREGATE_ROWS,
	)
	return {
		"outstanding_amount": _sum(invoices, "outstanding_amount"),
		"unpaid_invoice_count": len(invoices),
		"open_order_count": len(orders),
		"open_order_total": _sum(orders, "grand_total"),
	}


def _purchase_aggregates(supplier):
	orders = _get_list(
		"Purchase Order",
		filters={
			"supplier": supplier,
			"docstatus": 1,
			"status": ["in", list(OPEN_PURCHASE_ORDER_STATUSES)],
		},
		fields=["grand_total", "per_received", "status"],
		limit_page_length=MAX_AGGREGATE_ROWS,
	)
	invoices = _get_list(
		"Purchase Invoice",
		filters={"supplier": supplier, "docstatus": 1, "outstanding_amount": [">", 0]},
		fields=["outstanding_amount"],
		limit_page_length=MAX_AGGREGATE_ROWS,
	)
	return {
		"open_purchase_order_count": len(orders),
		"open_purchase_order_total": _sum(orders, "grand_total"),
		"amount_to_receive": round(sum(_remaining_to_receive(row) for row in orders), 2),
		"unpaid_invoice_count": len(invoices),
		"outstanding_amount": _sum(invoices, "outstanding_amount"),
	}


def _remaining_to_receive(row):
	if row.get("status") not in RECEIVABLE_PURCHASE_ORDER_STATUSES:
		return 0.0
	grand = _num(row.get("grand_total")) or 0.0
	received = _num(row.get("per_received")) or 0.0
	if received < 0:
		received = 0.0
	if received >= 100:
		return 0.0
	return grand * (100.0 - received) / 100.0


def _recent(doctype, filters, date_field, extra_fields=None):
	if not _can_read(doctype):
		return []
	fields = ["name", date_field, "status", "docstatus", "grand_total", "currency", "company"]
	if extra_fields:
		fields = fields + list(extra_fields)
	rows = _get_list(
		doctype,
		filters=filters,
		fields=fields,
		order_by=f"{date_field} desc",
		limit_page_length=RECENT_LIMIT,
	)
	return [_document(doctype, row, date_field, extra_fields) for row in rows]


def _document(doctype, row, date_field, extra_fields):
	payload = {
		"doctype": doctype,
		"name": row.get("name"),
		"date": _iso(row.get(date_field)),
		"status": row.get("status"),
		"docstatus": int(row.get("docstatus") or 0),
		"grand_total": _num(row.get("grand_total")),
		"currency": row.get("currency") or None,
		"company": row.get("company"),
		"url": _form_url(doctype, row.get("name")),
	}
	for field in extra_fields or []:
		payload[field] = _blank(row.get(field))
	return payload


def _can_read(doctype):
	try:
		if frappe.has_permission(doctype, "read"):
			return True
	except Exception:
		return False
	try:
		return bool(frappe.has_permission(doctype, "select"))
	except Exception:
		return False


def _get_list(doctype, **kwargs):
	if "ignore_permissions" in kwargs or not _can_read(doctype):
		return []
	kwargs.setdefault("limit_page_length", 20)
	try:
		rows = frappe.get_list(doctype, **kwargs)
	except frappe.PermissionError:
		return []
	return [dict(row) for row in (rows or [])]


def _sum(rows, field):
	return round(sum(_num(row.get(field)) or 0 for row in rows), 2)


def _num(value):
	if value is None or value == "":
		return None
	return round(float(value), 2)


def _iso(value):
	if value is None or value == "":
		return None
	if hasattr(value, "isoformat"):
		return value.isoformat()[:10]
	text = str(value).strip()
	return text[:10] if text else None


def _blank(value):
	if value is None:
		return None
	text = str(value).strip()
	return text or None


def _flag(value):
	if value in (None, "", False, 0, "0"):
		return False
	return bool(int(value)) if str(value).isdigit() else bool(value)
