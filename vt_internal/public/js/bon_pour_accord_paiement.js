// Phrase de paiement CB du Web Form public bon-pour-accord-devis.
// Le numéro dépend de Quotation.company. Le texte société est échappé côté
// serveur puis écrit en textContent : aucun HTML du champ Company n'est interprété.

export const PAIEMENT_CB_SELECTOR = ".vt-paiement-cb";
export const PAIEMENT_CB_INTRO_SELECTOR = ".web-form-introduction";
export const GENERIC_PAIEMENT_CB =
	"Carte bancaire, à distance il suffit de nous contacter par téléphone.";
export const PAIEMENT_CB_HTML_SNIPPET = `<span class="vt-paiement-cb">${GENERIC_PAIEMENT_CB}</span>`;
export const BON_POUR_ACCORD_ROUTE = "/bon-pour-accord-devis";
const MAX_QUOTATION_NAME = 140;

export function isBonPourAccordPath(pathname) {
	if (typeof pathname !== "string" || !pathname) return false;
	const path = pathname.split("?")[0].split("#")[0].replace(/\/+$/, "") || "/";
	const at = path.indexOf(BON_POUR_ACCORD_ROUTE);
	if (at === -1) return false;
	const rest = path.slice(at + BON_POUR_ACCORD_ROUTE.length);
	return rest === "" || rest.startsWith("/");
}

export function quotationFromSearch(search) {
	if (typeof search !== "string" || !search) return "";
	const query = search.charAt(0) === "?" ? search.slice(1) : search;
	const value = new URLSearchParams(query).get("quotation");
	if (!value) return "";
	const name = value.trim();
	if (!name || name.length > MAX_QUOTATION_NAME) return "";
	return name;
}

// Entités produites par frappe.utils.escape_html (v15) et par html.escape.
export function decodeEscapedHtml(value) {
	if (value == null) return "";
	return String(value)
		.replace(/&lt;/gi, "<")
		.replace(/&gt;/gi, ">")
		.replace(/&quot;/gi, '"')
		.replace(/&#34;/g, '"')
		.replace(/&#x22;/gi, '"')
		.replace(/&apos;/gi, "'")
		.replace(/&#39;/g, "'")
		.replace(/&#x27;/gi, "'")
		.replace(/&amp;/gi, "&");
}

export function composePaiementCb(fallback, phone) {
	const base = String(fallback == null ? "" : fallback).trim();
	const detail = String(phone == null ? "" : phone).trim();
	if (!detail) return base;
	const stem = base.replace(/[.\s]+$/, "");
	if (!stem) return /[.!?]$/.test(detail) ? detail : `${detail}.`;
	if (/[.!?]$/.test(detail)) return `${stem} : ${detail}`;
	return `${stem} : ${detail}.`;
}

export function replaceGenericSentence(text, escapedPhone) {
	if (typeof text !== "string" || !text.includes(GENERIC_PAIEMENT_CB)) return text;
	const phone = decodeEscapedHtml(escapedPhone).trim();
	if (!phone) return text;
	const display = composePaiementCb(GENERIC_PAIEMENT_CB, phone);
	return text.split(GENERIC_PAIEMENT_CB).join(display);
}

export function replaceGenericInNode(node, escapedPhone) {
	if (!node) return 0;
	if (node.nodeType === 3) {
		const next = replaceGenericSentence(node.nodeValue, escapedPhone);
		if (next === node.nodeValue) return 0;
		node.nodeValue = next;
		return 1;
	}
	const children = node.childNodes || [];
	let count = 0;
	for (let i = 0; i < children.length; i += 1) {
		count += replaceGenericInNode(children[i], escapedPhone);
	}
	return count;
}

export function applyPaiementCbDocument(doc, escapedPhone) {
	const phone = decodeEscapedHtml(escapedPhone).trim();
	if (!phone || !doc || typeof doc.querySelectorAll !== "function") return 0;
	const spans = Array.from(doc.querySelectorAll(PAIEMENT_CB_SELECTOR) || []);
	if (spans.length) {
		spans.forEach((el) => {
			if (!el.dataset.vtPaiementCbReady) {
				el.dataset.vtPaiementCbBase = el.textContent || "";
				el.dataset.vtPaiementCbReady = "1";
			}
			el.textContent = composePaiementCb(el.dataset.vtPaiementCbBase, phone);
		});
		return spans.length;
	}
	let count = 0;
	const intros = Array.from(doc.querySelectorAll(PAIEMENT_CB_INTRO_SELECTOR) || []);
	intros.forEach((intro) => {
		count += replaceGenericInNode(intro, escapedPhone);
	});
	return count;
}
