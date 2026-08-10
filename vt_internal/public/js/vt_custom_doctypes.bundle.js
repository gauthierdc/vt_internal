/**
 * Chargement global du JS client des DocTypes CUSTOM (custom=1).
 *
 * Pour les DocTypes custom, Frappe court-circuite `Meta.add_code` (voir
 * frappe/desk/form/meta.py : `if self.custom: return`) : les hooks
 * `doctype_js` / `doctype_list_js` sont donc IGNORÉS pour ces doctypes.
 *
 * On charge leur JS ici via `app_include_js` (chargé sur tout le Desk) : les
 * `frappe.ui.form.on(...)` et `frappe.listview_settings[...]` s'enregistrent
 * globalement et s'appliquent quel que soit le flag custom.
 *
 * Les DocTypes STANDARD restent gérés par doctype_js / doctype_list_js (hooks).
 */

// --- Formulaires ---
import "./bmv_settings.js";
import "./carte_de_travail_vt.js";
import "./consolidated_invoice.js";
import "./fabrication_vt.js";
import "./fiche_de_travail.js";
import "./order_satisfaction.js";
import "./production_statement.js";
import "./quality_incident.js";
import "./vt_objective.js";
import "./work_completion_receipt.js";

// --- Listes ---
import "./fiche_de_travail_list.js";
import "./quotation_approval_list.js";
