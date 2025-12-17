# Copyright (c) 2025, Verre & Transparence and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from collections import defaultdict


def execute(filters: dict | None = None):
	"""Point d'entrée principal du rapport."""
	report = PerformanceCommercialeReport(filters or {})
	return report.run()


class PerformanceCommercialeReport:
	def __init__(self, filters: dict):
		self.filters = frappe._dict(filters)
		self.validate_filters()

	def validate_filters(self):
		"""Valide les filtres et récupère les dates de l'année fiscale."""
		if not self.filters.get("fiscal_year"):
			frappe.throw(_("L'année fiscale est obligatoire"))
		if not self.filters.get("company"):
			frappe.throw(_("La société est obligatoire"))

		# Récupérer les dates de l'année fiscale
		fy = frappe.get_doc("Fiscal Year", self.filters.fiscal_year)
		self.filters.from_date = fy.year_start_date
		self.filters.to_date = fy.year_end_date

	def run(self):
		"""Exécute le rapport et retourne colonnes + données."""
		columns = self.get_columns()
		data = self.get_data()
		# skip_total_row car on gère notre propre ligne TOTAL
		return columns, data, None, None, None, 1

	def get_columns(self) -> list[dict]:
		"""Retourne la définition des colonnes."""
		view_type = self.filters.get("view_type", "Secteur / Centre de coût")

		# Colonne entité selon la vue
		if view_type == "Groupe de client":
			entity_label = _("Groupe de client")
		elif view_type == "Centre de coût / Secteur":
			entity_label = _("Centre de coût / Secteur")
		else:
			entity_label = _("Secteur / Centre de coût")

		columns = [
			{
				"label": entity_label,
				"fieldname": "entity",
				"fieldtype": "Data",
				"width": 250
			},
			# Devis
			{
				"label": _("Nb Devis"),
				"fieldname": "nb_devis",
				"fieldtype": "Int",
				"width": 80
			},
			{
				"label": _("Valeur Devis HT"),
				"fieldname": "valeur_devis",
				"fieldtype": "Currency",
				"width": 130
			},
			{
				"label": _("Panier Moyen Devis"),
				"fieldname": "panier_devis",
				"fieldtype": "Currency",
				"width": 130
			},
			# Commandes
			{
				"label": _("Nb Cmd"),
				"fieldname": "nb_commandes",
				"fieldtype": "Int",
				"width": 80
			},
			{
				"label": _("Valeur Cmd HT"),
				"fieldname": "valeur_commandes",
				"fieldtype": "Currency",
				"width": 130
			},
			{
				"label": _("Panier Moyen Cmd"),
				"fieldname": "panier_commandes",
				"fieldtype": "Currency",
				"width": 130
			},
			# Indicateurs
			{
				"label": _("Taux Transfo (%)"),
				"fieldname": "taux_transfo",
				"fieldtype": "Percent",
				"width": 110
			},
			{
				"label": _("Marge (%)"),
				"fieldname": "marge_pct",
				"fieldtype": "Percent",
				"width": 90
			},
			{
				"label": _("Marge (EUR)"),
				"fieldname": "marge_eur",
				"fieldtype": "Currency",
				"width": 110
			},
		]

		return columns

	def get_data(self) -> list[dict]:
		"""Récupère et agrège les données selon la vue sélectionnée."""
		view_type = self.filters.get("view_type", "Secteur / Centre de coût")

		if view_type == "Groupe de client":
			return self.get_data_by_customer_group()
		else:
			return self.get_data_hierarchical(view_type)

	def get_base_conditions(self, alias: str = "q") -> tuple[list, dict]:
		"""Retourne les conditions de base et paramètres pour les requêtes."""
		conditions = [
			f"{alias}.company = %(company)s",
			f"{alias}.transaction_date >= %(from_date)s",
			f"{alias}.transaction_date <= %(to_date)s"
		]
		params = {
			"company": self.filters.company,
			"from_date": self.filters.from_date,
			"to_date": self.filters.to_date
		}

		# Filtre centre de coût avec descendants
		if self.filters.get("cost_center"):
			cc = self.filters.cost_center
			descendants = frappe.db.get_descendants("Cost Center", cc)
			centers = [cc] + list(descendants)
			conditions.append(f"{alias}.cost_center IN %(cost_centers)s")
			params["cost_centers"] = centers

		return conditions, params

	def get_quotations(self) -> list[dict]:
		"""Récupère les devis (hors variantes)."""
		conditions, params = self.get_base_conditions("q")

		query = """
			SELECT
				q.name,
				q.cost_center,
				q.secteur_vt,
				q.grand_total,
				c.customer_group
			FROM `tabQuotation` q
			LEFT JOIN `tabCustomer` c ON c.name = q.party_name
			WHERE q.docstatus IN (0, 1)
				AND (q.custom_dernier_statut_de_suivi IS NULL
					 OR q.custom_dernier_statut_de_suivi != 'Variante')
				AND {conditions}
		""".format(conditions=" AND ".join(conditions))

		return frappe.db.sql(query, params, as_dict=True)

	def get_sales_orders_with_margin(self) -> list[dict]:
		"""Récupère les commandes avec calcul des marges via les items."""
		conditions, params = self.get_base_conditions("so")

		query = """
			SELECT
				so.name,
				so.cost_center,
				so.secteur_vt,
				so.base_net_total,
				c.customer_group,
				(SELECT COALESCE(SUM(soi.amount), 0)
				 FROM `tabSales Order Item` soi
				 WHERE soi.parent = so.name) as prix_vente,
				(SELECT COALESCE(SUM(soi.qty * COALESCE(soi.unit_cost_price, 0)), 0)
				 FROM `tabSales Order Item` soi
				 WHERE soi.parent = so.name) as prix_achat
			FROM `tabSales Order` so
			LEFT JOIN `tabCustomer` c ON c.name = so.customer
			WHERE so.docstatus IN (0, 1)
				AND {conditions}
		""".format(conditions=" AND ".join(conditions))

		return frappe.db.sql(query, params, as_dict=True)

	def get_cost_center_hierarchy(self) -> dict:
		"""Récupère la hiérarchie des centres de coûts (enfant → parent)."""
		cost_centers = frappe.get_all(
			"Cost Center",
			filters={"company": self.filters.company},
			fields=["name", "parent_cost_center", "is_group"]
		)
		return {cc.name: cc.parent_cost_center for cc in cost_centers}

	def get_data_hierarchical(self, view_type: str) -> list[dict]:
		"""Construit les données avec hiérarchie."""
		quotations = self.get_quotations()
		sales_orders = self.get_sales_orders_with_margin()

		if view_type == "Centre de coût / Secteur":
			return self._build_cost_center_hierarchy_data(quotations, sales_orders)
		else:  # "Secteur / Centre de coût"
			return self._build_secteur_hierarchy_data(quotations, sales_orders)

	def _build_secteur_hierarchy_data(self, quotations: list, sales_orders: list) -> list[dict]:
		"""Construit les données: Secteur (niveau 0) → Centre de coût (niveau 1)."""
		# Structure d'agrégation à 2 niveaux
		aggregated = defaultdict(lambda: defaultdict(lambda: self._init_totals()))

		# Agréger les devis
		for q in quotations:
			secteur = q.get("secteur_vt") or _("(Non défini)")
			cc = q.get("cost_center") or _("(Non défini)")
			aggregated[secteur][cc]["nb_devis"] += 1
			aggregated[secteur][cc]["valeur_devis"] += flt(q.grand_total)

		# Agréger les commandes
		for so in sales_orders:
			secteur = so.get("secteur_vt") or _("(Non défini)")
			cc = so.get("cost_center") or _("(Non défini)")
			aggregated[secteur][cc]["nb_commandes"] += 1
			aggregated[secteur][cc]["valeur_commandes"] += flt(so.base_net_total)
			aggregated[secteur][cc]["prix_vente"] += flt(so.prix_vente)
			aggregated[secteur][cc]["prix_achat"] += flt(so.prix_achat)

		# Calculer les totaux par secteur pour le tri
		secteur_totals_map = {}
		for secteur in aggregated.keys():
			secteur_totals_map[secteur] = self._init_totals()
			for cc in aggregated[secteur].keys():
				self._add_to_totals(secteur_totals_map[secteur], aggregated[secteur][cc])

		# Trier les secteurs par valeur_devis décroissante
		sorted_secteurs = sorted(
			aggregated.keys(),
			key=lambda s: secteur_totals_map[s]["valeur_devis"],
			reverse=True
		)

		# Construire les lignes
		data = []
		grand_totals = self._init_totals()

		for secteur in sorted_secteurs:
			secteur_totals = secteur_totals_map[secteur]

			# Trier les CC par valeur_devis décroissante
			sorted_ccs = sorted(
				aggregated[secteur].keys(),
				key=lambda cc: aggregated[secteur][cc]["valeur_devis"],
				reverse=True
			)

			secteur_children = []
			for cc in sorted_ccs:
				agg = aggregated[secteur][cc]
				row = self._build_row(cc, agg, indent=1, parent=secteur)
				secteur_children.append(row)

			# Ligne parent secteur
			secteur_row = self._build_row(secteur, secteur_totals, indent=0)
			data.append(secteur_row)
			data.extend(secteur_children)

			self._add_to_totals(grand_totals, secteur_totals)

		# Ligne TOTAL
		total_row = self._build_row("TOTAL", grand_totals, indent=0)
		data.insert(0, total_row)

		return data

	def _build_cost_center_hierarchy_data(self, quotations: list, sales_orders: list) -> list[dict]:
		"""Construit les données: CC Parent (niveau 0) → CC Enfant (niveau 1) → Secteur (niveau 2)."""
		cc_hierarchy = self.get_cost_center_hierarchy()

		# Structure d'agrégation à 3 niveaux: parent_cc → cc → secteur
		aggregated = defaultdict(
			lambda: defaultdict(
				lambda: defaultdict(lambda: self._init_totals())
			)
		)

		# Agréger les devis
		for q in quotations:
			cc = q.get("cost_center") or _("(Non défini)")
			parent_cc = cc_hierarchy.get(cc) or cc  # Si pas de parent, utiliser le CC lui-même
			secteur = q.get("secteur_vt") or _("(Non défini)")

			aggregated[parent_cc][cc][secteur]["nb_devis"] += 1
			aggregated[parent_cc][cc][secteur]["valeur_devis"] += flt(q.grand_total)

		# Agréger les commandes
		for so in sales_orders:
			cc = so.get("cost_center") or _("(Non défini)")
			parent_cc = cc_hierarchy.get(cc) or cc
			secteur = so.get("secteur_vt") or _("(Non défini)")

			aggregated[parent_cc][cc][secteur]["nb_commandes"] += 1
			aggregated[parent_cc][cc][secteur]["valeur_commandes"] += flt(so.base_net_total)
			aggregated[parent_cc][cc][secteur]["prix_vente"] += flt(so.prix_vente)
			aggregated[parent_cc][cc][secteur]["prix_achat"] += flt(so.prix_achat)

		# Calculer les totaux par parent_cc pour le tri
		parent_totals_map = {}
		cc_totals_map = {}
		for parent_cc in aggregated.keys():
			parent_totals_map[parent_cc] = self._init_totals()
			cc_totals_map[parent_cc] = {}
			for cc in aggregated[parent_cc].keys():
				cc_totals_map[parent_cc][cc] = self._init_totals()
				for secteur in aggregated[parent_cc][cc].keys():
					self._add_to_totals(cc_totals_map[parent_cc][cc], aggregated[parent_cc][cc][secteur])
				self._add_to_totals(parent_totals_map[parent_cc], cc_totals_map[parent_cc][cc])

		# Trier les parents par valeur_devis décroissante
		sorted_parents = sorted(
			aggregated.keys(),
			key=lambda p: parent_totals_map[p]["valeur_devis"],
			reverse=True
		)

		# Construire les lignes avec hiérarchie à 3 niveaux
		data = []
		grand_totals = self._init_totals()

		for parent_cc in sorted_parents:
			parent_totals = parent_totals_map[parent_cc]
			parent_children = []

			# Trier les CC par valeur_devis décroissante
			sorted_ccs = sorted(
				aggregated[parent_cc].keys(),
				key=lambda cc: cc_totals_map[parent_cc][cc]["valeur_devis"],
				reverse=True
			)

			for cc in sorted_ccs:
				cc_totals = cc_totals_map[parent_cc][cc]

				# Trier les secteurs par valeur_devis décroissante
				sorted_secteurs = sorted(
					aggregated[parent_cc][cc].keys(),
					key=lambda s: aggregated[parent_cc][cc][s]["valeur_devis"],
					reverse=True
				)

				cc_children = []
				for secteur in sorted_secteurs:
					agg = aggregated[parent_cc][cc][secteur]
					row = self._build_row(secteur, agg, indent=2, parent=cc)
					cc_children.append(row)

				# Ligne centre de coût (niveau 1)
				# Si le CC est le même que le parent, ne pas créer de niveau intermédiaire
				if cc != parent_cc:
					cc_row = self._build_row(cc, cc_totals, indent=1, parent=parent_cc)
					parent_children.append(cc_row)
					parent_children.extend(cc_children)
				else:
					# Le CC est root, les secteurs sont directement enfants
					for child in cc_children:
						child["indent"] = 1
						child["parent_entity"] = parent_cc
					parent_children.extend(cc_children)

			# Ligne parent (niveau 0)
			parent_row = self._build_row(parent_cc, parent_totals, indent=0)
			data.append(parent_row)
			data.extend(parent_children)

			self._add_to_totals(grand_totals, parent_totals)

		# Ligne TOTAL
		total_row = self._build_row("TOTAL", grand_totals, indent=0)
		data.insert(0, total_row)

		return data

	def get_data_by_customer_group(self) -> list[dict]:
		"""Vue simple par groupe de client sans hiérarchie."""
		quotations = self.get_quotations()
		sales_orders = self.get_sales_orders_with_margin()

		aggregated = defaultdict(lambda: {
			"nb_devis": 0,
			"valeur_devis": 0,
			"nb_commandes": 0,
			"valeur_commandes": 0,
			"prix_vente": 0,
			"prix_achat": 0
		})

		# Agréger les devis
		for q in quotations:
			group = q.get("customer_group") or _("(Non défini)")
			aggregated[group]["nb_devis"] += 1
			aggregated[group]["valeur_devis"] += flt(q.grand_total)

		# Agréger les commandes
		for so in sales_orders:
			group = so.get("customer_group") or _("(Non défini)")
			aggregated[group]["nb_commandes"] += 1
			aggregated[group]["valeur_commandes"] += flt(so.base_net_total)
			aggregated[group]["prix_vente"] += flt(so.prix_vente)
			aggregated[group]["prix_achat"] += flt(so.prix_achat)

		# Trier les groupes par valeur_devis décroissante
		sorted_groups = sorted(
			aggregated.keys(),
			key=lambda g: aggregated[g]["valeur_devis"],
			reverse=True
		)

		# Construire les lignes
		data = []
		grand_totals = self._init_totals()

		for group in sorted_groups:
			row = self._build_row(group, aggregated[group], indent=0)
			data.append(row)
			self._add_to_totals(grand_totals, aggregated[group])

		# Ligne TOTAL
		total_row = self._build_row("TOTAL", grand_totals, indent=0)
		data.insert(0, total_row)

		return data

	def _init_totals(self) -> dict:
		"""Initialise un dictionnaire de totaux."""
		return {
			"nb_devis": 0,
			"valeur_devis": 0,
			"nb_commandes": 0,
			"valeur_commandes": 0,
			"prix_vente": 0,
			"prix_achat": 0
		}

	def _add_to_totals(self, totals: dict, values: dict):
		"""Ajoute des valeurs aux totaux."""
		for key in totals:
			totals[key] += flt(values.get(key, 0))

	def _build_row(self, entity: str, agg: dict, indent: int = 0, parent: str = None) -> dict:
		"""Construit une ligne du rapport avec tous les calculs."""
		nb_devis = agg["nb_devis"]
		valeur_devis = agg["valeur_devis"]
		nb_commandes = agg["nb_commandes"]
		valeur_commandes = agg["valeur_commandes"]
		prix_vente = agg["prix_vente"]
		prix_achat = agg["prix_achat"]

		# Calculs des indicateurs
		panier_devis = valeur_devis / nb_devis if nb_devis > 0 else 0
		panier_commandes = valeur_commandes / nb_commandes if nb_commandes > 0 else 0
		taux_transfo = (valeur_commandes / valeur_devis * 100) if valeur_devis > 0 else 0
		marge_eur = prix_vente - prix_achat
		marge_pct = ((prix_vente - prix_achat) / prix_vente * 100) if prix_vente > 0 else 0

		row = {
			"entity": entity,
			"indent": indent,
			"nb_devis": nb_devis,
			"valeur_devis": valeur_devis,
			"panier_devis": panier_devis,
			"nb_commandes": nb_commandes,
			"valeur_commandes": valeur_commandes,
			"panier_commandes": panier_commandes,
			"taux_transfo": taux_transfo,
			"marge_pct": marge_pct,
			"marge_eur": marge_eur
		}

		if parent:
			row["parent_entity"] = parent

		return row
