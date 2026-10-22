import assert from "node:assert/strict";
import test from "node:test";
import {
	GENERIC_PAIEMENT_CB,
	PAIEMENT_CB_HTML_SNIPPET,
	applyPaiementCbDocument,
	composePaiementCb,
	decodeEscapedHtml,
	isBonPourAccordPath,
	quotationFromSearch,
	replaceGenericSentence,
} from "./bon_pour_accord_paiement.js";

const MAV = "04.90.86.63.19 (Tapez 1, n'hésitez pas à me laisser un message sur le répondeur)";
const VS = "04 77 50 92 29 (Tapez 1, n'hésitez pas à me laisser un message sur le répondeur)";
const MAV_ESCAPED = MAV.replaceAll("'", "&apos;");

function span(text) {
	return { textContent: text, dataset: {} };
}

function textNode(value) {
	return { nodeType: 3, nodeValue: value };
}

function element(children) {
	return { nodeType: 1, childNodes: children };
}

function fakeDoc({ spans = [], intros = [] } = {}) {
	return {
		querySelectorAll(selector) {
			if (selector === ".vt-paiement-cb") return spans;
			if (selector === ".web-form-introduction") return intros;
			return [];
		},
	};
}

test("route du bon pour accord, y compris un préfixe de langue", () => {
	assert.equal(isBonPourAccordPath("/bon-pour-accord-devis"), true);
	assert.equal(isBonPourAccordPath("/bon-pour-accord-devis/"), true);
	assert.equal(isBonPourAccordPath("/bon-pour-accord-devis/new"), true);
	assert.equal(isBonPourAccordPath("/fr/bon-pour-accord-devis/new"), true);
	assert.equal(isBonPourAccordPath("/"), false);
	assert.equal(isBonPourAccordPath("/bon-pour-accord-devis-autre"), false);
	assert.equal(isBonPourAccordPath("/app/quotation"), false);
	assert.equal(isBonPourAccordPath(""), false);
	assert.equal(isBonPourAccordPath(null), false);
});

test("paramètre quotation lu dans l'URL, ignoré s'il est vide ou trop long", () => {
	assert.equal(
		quotationFromSearch("?quotation=DEV-MAV-26-0001&contact_email=a@b.c"),
		"DEV-MAV-26-0001"
	);
	assert.equal(quotationFromSearch("quotation=DEV-VS-1"), "DEV-VS-1");
	assert.equal(quotationFromSearch("?quotation="), "");
	assert.equal(quotationFromSearch("?quotation=%20"), "");
	assert.equal(quotationFromSearch("?contact_email=a@b.c"), "");
	assert.equal(quotationFromSearch(""), "");
	assert.equal(quotationFromSearch("?" + "quotation=" + "X".repeat(141)), "");
});

test("les entités Frappe et html.escape redeviennent du texte", () => {
	assert.equal(
		decodeEscapedHtml("n&apos;hésitez &lt;b&gt; &quot;x&quot; &amp; y"),
		"n'hésitez <b> \"x\" & y"
	);
	assert.equal(
		decodeEscapedHtml("n&#x27;hésitez &lt;b&gt; &quot;x&quot; &amp; y"),
		"n'hésitez <b> \"x\" & y"
	);
	assert.equal(decodeEscapedHtml(""), "");
	assert.equal(decodeEscapedHtml(null), "");
});

test("MAV et VS complètent la phrase générique, un texte vide la laisse", () => {
	const mav = composePaiementCb(GENERIC_PAIEMENT_CB, MAV);
	const vs = composePaiementCb(GENERIC_PAIEMENT_CB, VS);
	assert.equal(
		mav,
		"Carte bancaire, à distance il suffit de nous contacter par téléphone : " + MAV + "."
	);
	assert.equal(
		vs,
		"Carte bancaire, à distance il suffit de nous contacter par téléphone : " + VS + "."
	);
	assert.equal(composePaiementCb(GENERIC_PAIEMENT_CB, ""), GENERIC_PAIEMENT_CB);
	assert.equal(composePaiementCb(GENERIC_PAIEMENT_CB, "   "), GENERIC_PAIEMENT_CB);
	assert.equal(
		composePaiementCb(GENERIC_PAIEMENT_CB, "Déjà une phrase."),
		`${GENERIC_PAIEMENT_CB.slice(0, -1)} : Déjà une phrase.`
	);
});

test("le snippet HTML contient la classe et la phrase de repli", () => {
	assert.ok(PAIEMENT_CB_HTML_SNIPPET.includes('class="vt-paiement-cb"'));
	assert.ok(PAIEMENT_CB_HTML_SNIPPET.includes(GENERIC_PAIEMENT_CB));
	assert.equal(PAIEMENT_CB_HTML_SNIPPET, `<span class="vt-paiement-cb">${GENERIC_PAIEMENT_CB}</span>`);
});

test("un span est rempli en texte, pas en HTML, et un second appel n'empile pas", () => {
	const target = span(GENERIC_PAIEMENT_CB);
	const doc = fakeDoc({ spans: [target] });
	assert.equal(applyPaiementCbDocument(doc, MAV_ESCAPED), 1);
	assert.equal(target.textContent, composePaiementCb(GENERIC_PAIEMENT_CB, MAV));
	assert.equal(applyPaiementCbDocument(doc, MAV_ESCAPED), 1);
	assert.equal(target.textContent, composePaiementCb(GENERIC_PAIEMENT_CB, MAV));
	assert.equal(target.innerHTML, undefined);
});

test("un message vide ou un script ne remplace pas le repli par du HTML", () => {
	const target = span(GENERIC_PAIEMENT_CB);
	const doc = fakeDoc({ spans: [target] });
	assert.equal(applyPaiementCbDocument(doc, ""), 0);
	assert.equal(target.textContent, GENERIC_PAIEMENT_CB);
	const payload = "&lt;img src=x onerror=alert(1)&gt;";
	applyPaiementCbDocument(doc, payload);
	assert.equal(
		target.textContent,
		composePaiementCb(GENERIC_PAIEMENT_CB, "<img src=x onerror=alert(1)>")
	);
	assert.equal(target.childNodes, undefined);
});

test("sans span, la phrase exacte dans l'intro est remplacée", () => {
	const node = textNode(`Intro. ${GENERIC_PAIEMENT_CB} Suite.`);
	const doc = fakeDoc({ intros: [element([node])] });
	assert.equal(applyPaiementCbDocument(doc, VS), 1);
	assert.equal(node.nodeValue, `Intro. ${composePaiementCb(GENERIC_PAIEMENT_CB, VS)} Suite.`);
	assert.equal(replaceGenericSentence(node.nodeValue, VS), node.nodeValue);
});

test("un span présent empêche le remplacement du reste de l'intro", () => {
	const target = span(GENERIC_PAIEMENT_CB);
	const node = textNode(GENERIC_PAIEMENT_CB);
	const doc = fakeDoc({ spans: [target], intros: [element([node])] });
	applyPaiementCbDocument(doc, MAV);
	assert.equal(target.textContent, composePaiementCb(GENERIC_PAIEMENT_CB, MAV));
	assert.equal(node.nodeValue, GENERIC_PAIEMENT_CB);
});
