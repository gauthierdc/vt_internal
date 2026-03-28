import frappe


def _quotation_response(quotation, prompt_name):
    doc = frappe.get_doc("Quotation", quotation)
    print_html = frappe.get_print("Quotation", doc.name, doc.meta.default_print_format or "Standard")
    prompt = frappe.db.get_value("Prompt IA", prompt_name, "prompt") or ""
    frappe.response["message"] = {"prompt": prompt, "print_html": print_html}


@frappe.whitelist(allow_guest=True)
def quotation_details(quotation):
    _quotation_response(quotation, "Analyse devis client")


@frappe.whitelist(allow_guest=True)
def quotation_internal(quotation):
    _quotation_response(quotation, "Analyse devis interne")

