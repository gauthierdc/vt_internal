# Copyright (c) 2025, Verre & Transparence and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class VisiteTechnique(Document):
	def on_trash(self):
		if self.quotation:
			frappe.db.set_value("Quotation", self.quotation, "custom_visite_technique_status", None)
		if self.sales_order:
			frappe.db.set_value("Sales Order", self.sales_order, "custom_visite_technique_status", None)

	def before_save(self):
		if self.quotation:
			frappe.db.set_value("Quotation", self.quotation, "custom_visite_technique_status", self.status)
		if self.sales_order:
			frappe.db.set_value("Sales Order", self.sales_order, "custom_visite_technique_status", self.status)

			# Auto-set de la date de complétion
			if self.status == "Fait" and not self.completion_on:
				self.completion_on = frappe.utils.today()