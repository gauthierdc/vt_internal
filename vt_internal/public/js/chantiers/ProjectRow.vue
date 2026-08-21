<template>
	<tr :class="{ sav: p.is_sav }">
		<td class="vtc-name">
			<a href="#" @click.prevent="$emit('open', p.project)">{{ p.project }}</a>
			<span v-if="p.type_projet" class="vtc-type">{{ p.type_projet }}</span>
		</td>
		<td class="vtc-client">{{ p.client }}</td>
		<td class="vtc-flux">
			<a v-if="p.ca_periode" href="#" class="flux-chip fin" :data-tip="__('Facturé (ventes)') + ' : ' + fmtMoney(p.ca_periode) + ' — ' + __('voir les factures de la période')" @click.prevent="$emit('docs', { project: p.project, kind: 'invoices' })">🧾 {{ fmtCompact(p.ca_periode) }}</a>
			<a v-if="p.po_periode" href="#" class="flux-chip po" :data-tip="__('Achats — commandes fournisseur') + ' : ' + fmtMoney(p.po_periode) + ' — ' + __('voir les commandes')" @click.prevent="$emit('docs', { project: p.project, kind: 'po' })">🛒 {{ fmtCompact(p.po_periode) }}</a>
			<a v-if="p.depense_periode" href="#" class="flux-chip dep" :data-tip="__('Dépenses (notes de frais)') + ' : ' + fmtMoney(p.depense_periode) + ' — ' + __('voir les dépenses')" @click.prevent="$emit('docs', { project: p.project, kind: 'expense' })">💳 {{ fmtCompact(p.depense_periode) }}</a>
			<a v-if="p.fab_periode" href="#" class="flux-chip fab" :data-tip="__('Fabrication VT') + ' : ' + fmtMoney(p.fab_periode) + ' — ' + __('voir les fabrications')" @click.prevent="$emit('docs', { project: p.project, kind: 'fab' })">🏭 {{ fmtCompact(p.fab_periode) }}</a>
			<span v-if="!p.ca_periode && !p.po_periode && !p.depense_periode && !p.fab_periode" class="muted">—</span>
		</td>
		<td>
			<div class="vtc-marge" :class="margeTone">
				<div class="vtc-marge-track">
					<div class="fill" :style="{ width: margeReelPct + '%' }"></div>
					<div class="theo" :style="{ left: margeTheoPct + '%' }" :data-tip="'Théorique ' + p.marge_theo + '%'"></div>
				</div>
				<div class="vtc-marge-txt">
					<b>{{ p.marge_reel }}%</b>
					<span class="diff">{{ p.marge_diff > 0 ? '+' : '' }}{{ p.marge_diff }}</span>
				</div>
			</div>
		</td>
		<td>
			<div class="vtc-hours" :class="heuresTone">
				<div class="vtc-hours-track">
					<div class="fill val" :style="{ width: hoursPct.val + '%' }"></div>
					<div class="fill draft" :style="{ width: hoursPct.draft + '%' }"></div>
				</div>
				<div class="vtc-hours-txt">
					<a v-if="p.heures_val || p.heures_draft" href="#" class="vtc-link" :data-tip="__('Voir les feuilles de temps de la période')" @click.prevent="$emit('docs', { project: p.project, kind: 'timesheet' })">
						<b>{{ p.heures_val }}h</b><span v-if="p.heures_draft" class="draft-txt">+{{ p.heures_draft }}h</span>
					</a>
					<span v-else class="none">0h</span>
				</div>
				<div class="vtc-hours-sub">
					{{ __('cumul') }} {{ p.heures_total }}h<span v-if="p.heures_expected"> / {{ p.heures_expected }}h</span>
					<span v-if="p.heures_expected && p.heures_diff > 0" class="over-badge">+{{ p.heures_diff }}h</span>
				</div>
			</div>
		</td>
		<td>
			<a class="vtc-fact vtc-link-block" href="#" :data-tip="__('Voir toutes les factures de vente du chantier')" @click.prevent="$emit('docs', { project: p.project, kind: 'invoices_all' })">
				<div class="vtc-fact-track"><div class="fill" :style="{ width: Math.min(p.pct_facture, 100) + '%' }"></div></div>
				<div class="vtc-fact-txt">{{ p.pct_facture }}%<span v-if="p.reste_a_facturer" class="reste"> · reste {{ fmtMoney(p.reste_a_facturer) }}</span></div>
			</a>
		</td>
		<td class="num"><span v-if="p.retard > 0" class="vtc-late">+{{ p.retard }}j</span><span v-else>—</span></td>
		<td class="vtc-flags">
			<span v-if="p.is_sav" class="flag sav" data-tip="Heures sur chantier déjà facturé (SAV)">SAV</span>
			<button
				v-if="p.nb_incidents"
				class="flag inc" :class="{ closed: !p.nb_incidents_ouverts }"
				:data-tip="p.nb_incidents + ' incident(s) qualité — cliquer pour ouvrir'"
				@click.stop="$emit('incidents', p.project)"
			>⚠️{{ p.nb_incidents_ouverts || p.nb_incidents }}</button>
			<span v-if="p.is_facture && !p.nb_receptions" class="flag norec" data-tip="Facturé sans réception de travaux">📝∅</span>
			<span v-if="p.nb_receptions" class="flag rec" data-tip="Réception de travaux">📝</span>
		</td>
	</tr>
</template>

<script>
import { STATUS_COLORS, fmtMoney, fmtCompact } from "./helpers.js";

export default {
	name: "ProjectRow",
	props: { p: Object, maxHours: Number },
	emits: ["open", "incidents", "docs"],
	computed: {
		statusColor() { return STATUS_COLORS[this.p.status] || "#78909c"; },
		hoursPct() {
			// Barre comparative des heures POINTÉES sur la période (val + brouillon).
			const base = Math.max(this.maxHours, 1);
			return {
				val: (this.p.heures_val / base) * 100,
				draft: (this.p.heures_draft / base) * 100,
			};
		},
		margeReelPct() { return Math.max(0, Math.min(100, this.p.marge_reel)); },
		margeTheoPct() { return Math.max(0, Math.min(100, this.p.marge_theo)); },
		margeTone() {
			const d = this.p.marge_diff;
			return d >= 0 ? "up" : d >= -7 ? "warn" : "down";
		},
		heuresTone() {
			if (!this.p.heures_expected) return "";
			return this.p.heures_diff > 0 ? "over" : "ok";
		},
	},
	methods: { fmtMoney, fmtCompact },
};
</script>

<style scoped>
.num { text-align: right; }
tr.sav td { background: rgba(198, 40, 40, .045); }
td { padding: 9px 12px; border-bottom: 1px solid var(--border-color, #f0f2f4); vertical-align: middle; }
tr:hover td { background: var(--control-bg, #f7f9fa); }
.vtc-name a { font-weight: 620; color: var(--blue-600, #1565c0); }
.vtc-link { color: var(--blue-600, #1565c0); cursor: pointer; text-decoration: none; }
.vtc-link:hover { text-decoration: underline; }
.vtc-link-block { display: block; cursor: pointer; text-decoration: none; color: inherit; }
.vtc-link-block:hover .vtc-fact-track { outline: 2px solid var(--blue-200, #bbdefb); }
.muted { color: var(--text-muted, #9aa4ad); }
.vtc-flux { min-width: 150px; }
.vtc-flux .flux-chip { display: inline-flex; align-items: center; gap: 3px; padding: 2px 7px; margin: 1px 3px 1px 0; border-radius: 6px; font-size: 11.5px; font-weight: 600; cursor: pointer; text-decoration: none; white-space: nowrap; }
.flux-chip.fin { background: rgba(46, 125, 50, .12); color: #2e7d32; }
.flux-chip.po { background: rgba(25, 118, 210, .12); color: #1565c0; }
.flux-chip.dep { background: rgba(245, 124, 0, .14); color: #e65100; }
.flux-chip.fab { background: rgba(126, 87, 194, .14); color: #6a3fb0; }
.vtc-flux .flux-chip:hover { filter: brightness(.94); text-decoration: none; }
.vtc-type { display: block; font-size: 10px; color: var(--text-muted, #9aa4ad); }
.vtc-client { color: var(--text-muted, #6c7680); max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.vtc-status { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 11px; font-weight: 600; color: #fff; }

.vtc-marge { min-width: 120px; }
.vtc-marge-track { position: relative; height: 7px; background: var(--control-bg, #eef1f3); border-radius: 4px; }
.vtc-marge-track .fill { height: 100%; border-radius: 4px; }
.vtc-marge.up .fill { background: #2e7d32; } .vtc-marge.warn .fill { background: #f9a825; } .vtc-marge.down .fill { background: #c62828; }
.vtc-marge-track .theo { position: absolute; top: -2px; width: 2px; height: 11px; background: var(--text-color, #37474f); border-radius: 1px; }
.vtc-marge-txt { display: flex; align-items: center; gap: 6px; margin-top: 3px; font-size: 12px; }
.vtc-marge-txt .diff { font-size: 11px; color: var(--text-muted, #6c7680); }

.vtc-hours { min-width: 130px; }
.vtc-hours-track { position: relative; height: 7px; background: var(--control-bg, #eef1f3); border-radius: 4px; display: flex; }
.vtc-hours-track .fill { height: 100%; } .vtc-hours-track .fill.val { background: #2e7d32; border-radius: 4px 0 0 4px; } .vtc-hours-track .fill.draft { background: #ffb74d; }
.vtc-hours.over .fill.val { background: #c62828; }
.vtc-hours-txt { margin-top: 3px; font-size: 12px; }
.vtc-hours-txt .draft-txt { color: #e08600; margin-left: 2px; } .vtc-hours-txt .none { color: var(--text-muted, #9aa4ad); }
.vtc-hours-sub { font-size: 10px; color: var(--text-muted, #9aa4ad); margin-top: 1px; }
.vtc-hours-sub .over-badge { color: #c62828; font-weight: 700; margin-left: 3px; }

.vtc-fact { min-width: 110px; }
.vtc-fact-track { height: 7px; background: var(--control-bg, #eef1f3); border-radius: 4px; overflow: hidden; }
.vtc-fact-track .fill { height: 100%; background: #1976d2; border-radius: 4px; }
.vtc-fact-txt { margin-top: 3px; font-size: 11px; color: var(--text-muted, #6c7680); }
.vtc-late { color: #c62828; font-weight: 700; }

.vtc-flags { white-space: nowrap; }
.vtc-flags .flag { display: inline-block; font-size: 10px; font-weight: 700; padding: 2px 5px; border-radius: 4px; margin-right: 3px; border: none; font-family: inherit; }
.vtc-flags .flag.sav { background: #c62828; color: #fff; }
.vtc-flags button.flag.inc { background: rgba(245, 124, 0, .16); color: #e65100; cursor: pointer; }
.vtc-flags button.flag.inc:hover { background: rgba(245, 124, 0, .3); }
.vtc-flags button.flag.inc.closed { background: var(--control-bg, #eef1f3); color: var(--text-muted, #9aa4ad); }
.vtc-flags .flag.norec { background: rgba(198, 40, 40, .12); color: #c62828; }
</style>
