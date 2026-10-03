// Miroir des cas de vt_internal/vt_internal/utils/test_ca_facture.py.
// Lancer : node --test --experimental-detect-module public/js/chantiers/variation.test.mjs

import assert from "node:assert/strict";
import test from "node:test";

import { aggregateMargin, periodVariation } from "./helpers.js";

test("nearly empty comparison base is n.s.", () => {
	const result = periodVariation(178000, 1000);
	assert.equal(result.insignificant, true);
	assert.equal(result.deltaText, "n.s.");
	assert.equal(result.delta, null);
});

test("zero base is n.s.", () => {
	assert.equal(periodVariation(96000, 0).deltaText, "n.s.");
});

test("comparable base shows a percent", () => {
	const result = periodVariation(178000, 90000);
	assert.equal(result.insignificant, false);
	assert.equal(result.delta, 98);
	assert.equal(result.deltaText, "▲ +98%");
	assert.equal(result.deltaClass, "good");
});

test("a drop is bad unless the metric is inverted", () => {
	assert.equal(periodVariation(100, 200).deltaText, "▼ -50%");
	assert.equal(periodVariation(100, 200).deltaClass, "bad");
	assert.equal(periodVariation(100, 200, true).deltaClass, "good");
});

test("flat and empty bases", () => {
	assert.equal(periodVariation(10, 10).deltaText, "= 0%");
	assert.equal(periodVariation(0, 0).deltaText, "");
	assert.equal(periodVariation(10, null).deltaText, "");
});

test("exactly 5 percent of current still shows a percent", () => {
	const result = periodVariation(100000, 5000);
	assert.equal(result.insignificant, false);
	assert.equal(result.delta, 1900);
});

test("selection margin is weighted by sales", () => {
	const result = aggregateMargin([
		{ vente: 100, cout_reel: 90 },
		{ vente: 900, cout_reel: 450 },
	]);
	assert.equal(result.pct, 46);
	assert.equal(result.eur, 460);
});

test("no sales means no margin rate", () => {
	const result = aggregateMargin([{ vente: 0, cout_reel: 40 }, {}]);
	assert.equal(result.pct, null);
	assert.equal(result.eur, -40);
});
