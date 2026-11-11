// Copy the business fields of a child row onto another row.
//
// Frappe addresses every child row as locals[doctype][name]. Grid refresh
// rebinds the visible row with `locals[doc.doctype][doc.name]`, and
// frappe.model.set_value writes to that same slot. Copying name/doctype
// (or the parent linkage) from the source row makes a later update — the
// buying price on a supplier quotation, for example — land on the source
// document still open in the desk.

const CHILD_ROW_IDENTITY_FIELDS = new Set([
	"name",
	"doctype",
	"parent",
	"parentfield",
	"parenttype",
	"idx",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
]);

export function copyChildRowData(target, source) {
	for (const key of Object.keys(source)) {
		if (CHILD_ROW_IDENTITY_FIELDS.has(key) || key.startsWith("_")) continue;
		target[key] = source[key];
	}
	return target;
}
