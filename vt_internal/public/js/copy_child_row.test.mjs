import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { copyChildRowData } from "./copy_child_row.js";

const here = path.dirname(fileURLToPath(import.meta.url));

// Desk stand-in for the two Frappe calls that make the bug visible:
//   grid row refresh: this.doc = locals[this.doc.doctype][this.doc.name]
//   set_value:        locals[doctype][name][field] = value
function addChild(locals, parent, doctype, parentfield) {
	const row = {
		doctype,
		name: `new-${doctype}-${parent[parentfield].length + 1}`,
		parent: parent.name,
		parentfield,
		parenttype: parent.doctype,
		idx: parent[parentfield].length + 1,
		__islocal: 1,
		docstatus: 0,
	};
	locals[doctype] = locals[doctype] || {};
	locals[doctype][row.name] = row;
	parent[parentfield].push(row);
	return row;
}

function setValue(locals, doctype, name, field, value) {
	const doc = locals[doctype] && locals[doctype][name];
	if (!doc) return null;
	doc[field] = value;
	return doc;
}

function visibleRow(locals, row) {
	return locals[row.doctype] && locals[row.doctype][row.name];
}

test("copying a quotation item keeps the supplier row's own identity", () => {
	const locals = {};
	const quotation = { doctype: "Quotation", name: "DE-2503-320", items: [] };
	const source = addChild(locals, quotation, "Quotation Item", "items");
	Object.assign(source, {
		item_code: "POSE8",
		item_name: "Pose",
		qty: 1,
		uom: "Nos",
		rate: 561.29,
		amount: 561.29,
		description: "Pose vitrage",
		row_type: "",
		docstatus: 0,
	});

	const supplierQuotation = {
		doctype: "Supplier Quotation",
		name: "new-supplier-quotation-1",
		items: [],
	};
	const supplierRow = addChild(locals, supplierQuotation, "Supplier Quotation Item", "items");
	const supplierName = supplierRow.name;

	copyChildRowData(supplierRow, source);

	assert.equal(supplierRow.doctype, "Supplier Quotation Item");
	assert.equal(supplierRow.name, supplierName);
	assert.equal(supplierRow.parent, supplierQuotation.name);
	assert.equal(supplierRow.parenttype, "Supplier Quotation");
	assert.equal(supplierRow.parentfield, "items");
	assert.equal(supplierRow.idx, 1);
	assert.equal(supplierRow.__islocal, 1);
	assert.equal(supplierRow.item_code, "POSE8");
	assert.equal(supplierRow.qty, 1);
	assert.equal(supplierRow.rate, 561.29);
	assert.equal(supplierRow.amount, 561.29);
	assert.equal(supplierRow.description, "Pose vitrage");

	// Buying-price update, as erpnext transaction.js does via set_value(doctype, name, "rate", price_list_rate).
	const written = setValue(locals, supplierRow.doctype, supplierRow.name, "rate", 200);
	setValue(locals, supplierRow.doctype, supplierRow.name, "amount", 200);

	assert.equal(written, supplierRow);
	assert.equal(visibleRow(locals, supplierRow), supplierRow);
	assert.notEqual(visibleRow(locals, supplierRow), source);
	assert.equal(supplierRow.rate, 200);
	assert.equal(supplierRow.amount, 200);
	assert.equal(source.rate, 561.29);
	assert.equal(source.amount, 561.29);
	assert.equal(quotation.items[0].rate, 561.29);
});

test("Object.assign of the source row aliases the quotation row in locals", () => {
	const locals = {};
	const quotation = { doctype: "Quotation", name: "DE-2503-320", items: [] };
	const source = addChild(locals, quotation, "Quotation Item", "items");
	source.item_code = "POSE8";
	source.rate = 561.29;
	source.amount = 561.29;

	const supplierQuotation = {
		doctype: "Supplier Quotation",
		name: "new-supplier-quotation-1",
		items: [],
	};
	const supplierRow = addChild(locals, supplierQuotation, "Supplier Quotation Item", "items");
	Object.assign(supplierRow, source);

	// The grid now resolves the supplier line to the customer line.
	assert.equal(visibleRow(locals, supplierRow), source);

	setValue(locals, supplierRow.doctype, supplierRow.name, "rate", 200);
	setValue(locals, supplierRow.doctype, supplierRow.name, "amount", 200);

	assert.equal(source.rate, 200);
	assert.equal(quotation.items[0].rate, 200);
	assert.equal(quotation.items[0].amount, 200);
});

test("duplicating a row inside one table does not reuse the source name", () => {
	const locals = {};
	const objective = { doctype: "VT Objective", name: "new-vt-objective-1", details: [] };
	const last = addChild(locals, objective, "VT Objective Detail", "details");
	last.week = 1;
	last.target = 10;

	const copy = addChild(locals, objective, "VT Objective Detail", "details");
	copyChildRowData(copy, last);
	copy.idx = objective.details.length;
	copy.week = objective.details.length;

	assert.notEqual(copy.name, last.name);
	assert.equal(visibleRow(locals, copy), copy);
	assert.equal(copy.week, 2);
	assert.equal(copy.target, 10);
	assert.equal(last.week, 1);

	setValue(locals, copy.doctype, copy.name, "target", 99);
	assert.equal(copy.target, 99);
	assert.equal(last.target, 10);
});

test("custom buttons copy child rows through copyChildRowData", () => {
	const files = [
		path.join(here, "quotation.js"),
		path.join(here, "sales_order.js"),
		path.join(here, "../../vt_internal/doctype/vt_objective/vt_objective.js"),
	];
	for (const file of files) {
		const text = fs.readFileSync(file, "utf8");
		assert.match(text, /copyChildRowData\(/, path.basename(file));
		assert.doesNotMatch(text, /Object\.assign\(\s*\w+\s*,\s*(i|t|last_row|row)\s*\)/);
		assert.doesNotMatch(text, /add_child\(\s*['"]items['"]\s*,\s*t\s*\)/);
	}
});
