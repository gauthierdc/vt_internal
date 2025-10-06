// Copyright (c) 2025, Dokos SAS and contributors
// For license information, please see license.txt

// ...existing code...
frappe.query_reports["Order book"] = {
    filters: [
        // Standard filters (status and per_billed handled server-side)
        ...frappe.get_meta("Sales Order").fields
            .filter(df => df.in_standard_filter && df.fieldname !== "status")
            .map(df => ({
                fieldname: df.fieldname,
                label: __(df.label),
                fieldtype: df.fieldtype,
                options: df.options,
                default: df.default
            })),
    ],
    // Color the Age column: <30 green, <100 orange, else red
    formatter: function(value, row, column, data, default_formatter) {
        let html = default_formatter(value, row, column, data);
        if (column.fieldname === "age" && value != null) {
            let color = value < 30 ? "green" : value < 100 ? "orange" : "red";
            html = `<span style="color:${color}">${value}</span>`;
        }
        return html;
    }
};