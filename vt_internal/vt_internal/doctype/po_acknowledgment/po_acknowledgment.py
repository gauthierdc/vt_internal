# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class POAcknowledgment(Document):

	def after_insert(self):
		if not self.received_on:
			self.db_set("received_on", frappe.utils.now(), update_modified=False)
		self._resolve_supplier()
		frappe.enqueue(
			"vt_internal.vt_internal.api.vt_bot.run_on_po_acknowledgment",
			docname=self.name,
			queue="long",
			timeout=1200,
			enqueue_after_commit=True,
		)

	def validate(self):
		if self.purchase_order and self.status == "New":
			self.status = "Matched"
		if not self.purchase_order and self.status == "Matched":
			self.status = "New"

	def _resolve_supplier(self):
		"""
		Résout le fournisseur depuis l'email expéditeur via la chaîne :
		sender_email → Contact (Contact Email) → Dynamic Link → Supplier.
		N'écrase pas un fournisseur déjà renseigné manuellement.
		"""
		if self.supplier or not self.sender_email:
			return

		from frappe.contacts.doctype.contact.contact import get_contact_name

		contact_name = get_contact_name(self.sender_email)
		if not contact_name:
			return

		contact = frappe.get_doc("Contact", contact_name)
		supplier = contact.get_link_for("Supplier")
		if supplier:
			self.db_set("supplier", supplier, update_modified=False)
			self.supplier = supplier
