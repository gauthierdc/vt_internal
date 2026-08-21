<template>
	<div class="vtc-root" :class="{ 'vtc-busy': store.loading && data }" @mousemove="onTipMove" @mouseleave="tipShow = false">
		<!-- Barre de chargement (indéterminée) -->
		<div v-if="store.loading" class="vtc-loadbar"><div class="bar"></div></div>

		<!-- Infobulle flottante (les title natifs ne s'affichent pas dans le Desk) -->
		<div v-if="tipShow" class="vtc-tooltip" :style="{ left: tipX + 'px', top: tipY + 'px' }">{{ tipText }}</div>

		<!-- Sélecteur de période (toujours visible, piloté par l'app) -->
		<div class="vtc-periodbar">
			<button class="vtc-nav" data-tip="Décaler à la période précédente" @click="shiftPeriod(-1)">‹</button>
			<div class="vtc-quick">
				<button
					v-for="q in quickRanges" :key="q.label"
					class="vtc-quick-btn" :class="{ active: isActive(q) }"
					@click="applyQuick(q)"
				>{{ q.label }}</button>
			</div>
			<div class="vtc-dates">
				<span class="vtc-date-lbl">{{ __('Du') }}</span>
				<input type="date" class="vtc-date" :value="store.filters.start_date" @change="onDate('start', $event)" :max="store.filters.end_date" />
				<span class="vtc-date-lbl">{{ __('au') }}</span>
				<input type="date" class="vtc-date" :value="store.filters.end_date" @change="onDate('end', $event)" :min="store.filters.start_date" />
			</div>
			<button class="vtc-nav" data-tip="Décaler à la période suivante" @click="shiftPeriod(1)">›</button>
			<span v-if="data" class="vtc-period-sub">{{ data.period.days }} {{ __('jours') }} · {{ __('vs') }} {{ prevLabel }}</span>
			<span class="vtc-refreshing" :class="{ show: store.loading }">{{ __('actualisation…') }}</span>
		</div>

		<!-- Filtres globaux (recalculent tout côté serveur) -->
		<div class="vtc-globalfilters" v-if="data">
			<!-- Conducteurs (multi-sélection) -->
			<div class="vtc-ms">
				<button class="vtc-ms-btn" :class="{ on: selectedCM.length }" @click="cmOpen = !cmOpen">
					👷 {{ conducteurLabel }} <span class="caret">▾</span>
				</button>
				<template v-if="cmOpen">
					<div class="vtc-ms-backdrop" @click="cmOpen = false"></div>
					<div class="vtc-ms-pop">
						<label class="vtc-ms-opt all" @click="clearCM">{{ __('Tous les conducteurs') }}</label>
						<label class="vtc-ms-opt" v-for="c in data.meta.conducteurs" :key="c.value">
							<input type="checkbox" :value="c.value" v-model="selectedCM" @change="applyCM" />
							{{ c.label }}
						</label>
						<div v-if="!data.meta.conducteurs.length" class="vtc-ms-empty">{{ __('Aucun conducteur défini') }}</div>
					</div>
				</template>
			</div>

			<!-- Société -->
			<select class="vtc-select" :value="store.filters.company || ''" @change="onCompany($event)">
				<option value="">{{ __('Toutes les sociétés') }}</option>
				<option v-for="co in data.meta.companies" :key="co" :value="co">{{ co }}</option>
			</select>

			<button v-if="selectedCM.length || store.filters.company" class="vtc-clearall" @click="clearGlobal">
				✕ {{ __('Réinitialiser') }}
			</button>
		</div>

		<!-- Chargement -->
		<template v-if="store.loading && !store.data">
			<div class="vtc-kpis">
				<div class="vtc-skel-card" v-for="n in 6" :key="n"></div>
			</div>
			<div class="vtc-skel-block"></div>
		</template>

		<div v-else-if="store.error" class="vtc-error">{{ store.error }}</div>

		<template v-else-if="data">
			<!-- KPIs -->
			<div class="vtc-kpis">
				<div
					class="vtc-kpi" v-for="k in kpiCards" :key="k.key"
					:class="[k.tone, { clickable: kpiClickable(k.key) }]"
					:data-tip="k.tip + (kpiClickable(k.key) ? '  —  Cliquer pour ouvrir la liste.' : '')"
					@click="kpiClick(k.key)"
				>
					<div class="vtc-kpi-label">{{ k.label }} <span class="vtc-info">{{ kpiClickable(k.key) ? '↗' : 'ⓘ' }}</span></div>
					<div class="vtc-kpi-value">{{ k.value }}</div>
					<div class="vtc-kpi-foot">
						<span class="vtc-kpi-sub">{{ k.sub }}</span>
						<span v-if="k.delta !== null" class="vtc-delta" :class="k.deltaClass" data-tip="Variation vs période précédente de même durée">{{ k.deltaText }}</span>
					</div>
				</div>
			</div>

			<!-- Alertes cliquables -->
			<div class="vtc-alerts" v-if="alerts.length">
				<button
					v-for="a in alerts"
					:key="a.key"
					class="vtc-alert"
					:class="[a.tone, { active: activeAlert === a.key }]"
					:data-tip="a.tip"
					@click="toggleAlert(a.key)"
				>
					<span class="vtc-alert-ic">{{ a.icon }}</span>
					<span class="vtc-alert-n">{{ a.count }}</span>
					<span class="vtc-alert-lbl">{{ a.label }}</span>
				</button>
			</div>

			<!-- Répartition des heures hors chantier -->
			<div class="vtc-charts" v-if="data.activity.length">
				<!-- Donut activité hors chantier -->
				<div class="vtc-card vtc-chart">
					<div class="vtc-card-title">{{ __('Heures hors chantier') }} · {{ activityTotal }} h</div>
					<div class="vtc-donut-wrap">
						<svg viewBox="0 0 42 42" class="vtc-donut">
							<circle cx="21" cy="21" r="15.915" class="donut-bg" />
							<circle
								v-for="(seg, i) in donut" :key="'d' + i"
								cx="21" cy="21" r="15.915"
								class="donut-seg"
								:stroke="seg.color"
								:stroke-dasharray="`${seg.pct} ${100 - seg.pct}`"
								:stroke-dashoffset="seg.offset"
							/>
							<text x="21" y="20" class="donut-c1">{{ activityTotal }}</text>
							<text x="21" y="25" class="donut-c2">heures</text>
						</svg>
						<div class="vtc-donut-legend">
							<div v-for="(seg, i) in donut" :key="'dl' + i" class="leg">
								<span class="sw" :style="{ background: seg.color }"></span>
								<span class="nm">{{ seg.label }}</span>
								<span class="vl">{{ seg.hours }} h</span>
							</div>
						</div>
					</div>
				</div>

			</div>

			<!-- Barre d'outils tableau -->
			<div class="vtc-toolbar">
				<input class="vtc-search" v-model="search" :placeholder="__('Rechercher un chantier, client…')" />
				<div class="vtc-flux-filter">
					<button
						v-for="ft in fluxTypes" :key="ft.key"
						class="flux-toggle" :class="[ft.key, { off: !fluxFilter[ft.key] }]"
						:data-tip="(fluxFilter[ft.key] ? __('Masquer') : __('Afficher')) + ' : ' + __('chantiers avec') + ' ' + ft.label"
						@click="fluxFilter[ft.key] = !fluxFilter[ft.key]"
					>{{ ft.icon }} {{ ft.label }}</button>
				</div>
				<select class="vtc-select" v-model="facetType">
					<option value="">{{ __('Tous les types') }}</option>
					<option v-for="t in typeOptions" :key="t" :value="t">{{ t }}</option>
				</select>
				<label class="vtc-check"><input type="checkbox" v-model="groupByCM" /> {{ __('Grouper par conducteur') }}</label>
				<span class="vtc-count">{{ filtered.length }} / {{ data.projects.length }} {{ __('chantiers') }}</span>
			</div>

			<!-- Tableau -->
			<div class="vtc-card vtc-table-wrap">
				<table class="vtc-table">
					<thead>
						<tr>
							<th @click="sortBy('project')" class="sortable" :data-tip="__('Code du chantier. Cliquer sur une ligne pour ouvrir le détail complet (marges, documents, paiements).')">{{ __('Chantier') }} <SortIc :dir="sortDir" :on="sortKey === 'project'" /></th>
							<th @click="sortBy('client')" class="sortable">{{ __('Client') }} <SortIc :dir="sortDir" :on="sortKey === 'client'" /></th>
							<th @click="sortBy('flux')" class="sortable" :data-tip="__('Flux financiers de la période, par chantier : 🧾 Facturé (ventes) · 🛒 Achats (commandes fournisseur) · 💳 Dépenses (notes de frais) · 🏭 Fabrication VT. Cliquer un montant ouvre la liste correspondante. Tri = total.')">{{ __('Flux (pér.)') }} <SortIc :dir="sortDir" :on="sortKey === 'flux'" /></th>
							<th @click="sortBy('marge_reel')" class="sortable" :data-tip="__('Barre = marge réelle (vente − coûts réels) ÷ vente. Trait vertical = marge théorique (basée sur les devis). Badge = écart réel − théorique, en points.')">{{ __('Marge') }} <SortIc :dir="sortDir" :on="sortKey === 'marge_reel'" /></th>
							<th @click="sortBy('heures_periode')" class="sortable" :data-tip="__('Heures pointées SUR LA PÉRIODE : validées + non validées (brouillon). Sous-texte : cumul total du chantier / heures prévues (vendues).')">{{ __('Pointé (pér.)') }} <SortIc :dir="sortDir" :on="sortKey === 'heures_periode'" /></th>
							<th @click="sortBy('pct_facture')" class="sortable" :data-tip="__('Avancement de facturation (tout l’historique) : total facturé ÷ total commandé (HT). « reste » = commandé − facturé.')">{{ __('Facturation cumul') }} <SortIc :dir="sortDir" :on="sortKey === 'pct_facture'" /></th>
							<th @click="sortBy('retard')" class="sortable num" :data-tip="__('Jours écoulés depuis la date de fin prévue, pour les chantiers non encore facturés.')">{{ __('Retard') }} <SortIc :dir="sortDir" :on="sortKey === 'retard'" /></th>
							<th :data-tip="__('SAV = repointage sur chantier facturé · ⚠️ = incidents qualité (cliquable) · 📝∅ = facturé sans réception · 📝 = réception présente.')">{{ __('Alertes') }}</th>
						</tr>
					</thead>

					<!-- Groupé par conducteur -->
					<template v-if="groupByCM">
						<tbody v-for="g in grouped" :key="g.name">
							<tr class="vtc-group-row">
								<td colspan="8">
									<span class="vtc-group-name">👷 {{ g.name }}</span>
									<span class="vtc-group-meta">{{ g.rows.length }} {{ __('chantiers') }} · {{ g.heures }}h · {{ fmtMoney(g.ca) }}</span>
								</td>
							</tr>
							<ProjectRow v-for="p in g.rows" :key="p.project" :p="p" :maxHours="maxHours" @open="store.openProject" @incidents="openIncidents([$event])" @docs="openDocs" />
						</tbody>
					</template>
					<tbody v-else>
						<ProjectRow v-for="p in filtered" :key="p.project" :p="p" :maxHours="maxHours" @open="store.openProject" @incidents="openIncidents([$event])" @docs="openDocs" />
						<tr v-if="!filtered.length"><td colspan="8" class="vtc-empty">{{ __('Aucun chantier') }}</td></tr>
					</tbody>
				</table>
			</div>

			<!-- Chantiers sans pointage -->
			<div class="vtc-card vtc-nopointage" v-if="data.sans_pointage.length">
				<div class="vtc-card-title">
					⚠️ {{ __('Chantiers décrochés — pointés la période précédente, plus rien depuis') }}
					<span class="vtc-badge-count">{{ data.sans_pointage.length }}</span>
				</div>
				<div class="vtc-chips">
					<button
						v-for="s in data.sans_pointage" :key="s.project"
						class="vtc-chip-np" :class="{ late: s.retard > 0 }"
						@click="store.openProject(s.project)"
						:title="s.customer"
					>
						<b>{{ s.project }}</b>
						<span class="np-client">{{ s.customer }}</span>
						<span v-if="s.retard > 0" class="np-late">+{{ s.retard }}j</span>
						<span class="np-cm">{{ s.conducteur_nom || '—' }}</span>
					</button>
				</div>
			</div>
		</template>
	</div>
</template>

<script>
import { h } from "vue";
import ProjectRow from "./ProjectRow.vue";
import { ACT_COLORS, fmtMoney, fmtCompact } from "./helpers.js";

// Petite flèche de tri (composant fonctionnel avec fonction de rendu, donc
// sans compilation de template à l'exécution — Frappe bundle Vue runtime-only).
const SortIc = (props) =>
	h("span", { class: "vtc-sortic" + (props.on ? " on" : "") }, props.on ? (props.dir === 1 ? "▲" : "▼") : "⇅");
SortIc.props = ["dir", "on"];

export default {
	name: "ChantiersApp",
	components: { SortIc, ProjectRow },
	props: { store: Object },
	data() {
		return {
			search: "",
			facetType: "",
			// Filtres par type de flux (tous cochés par défaut).
			fluxFilter: { pointe: true, facture: true, achat: true, depense: true, fab: true },
			fluxTypes: [
				{ key: "pointe", icon: "🕒", label: __("Pointé") },
				{ key: "facture", icon: "🧾", label: __("Facturé") },
				{ key: "achat", icon: "🛒", label: __("Achats") },
				{ key: "depense", icon: "💳", label: __("Dépense") },
				{ key: "fab", icon: "🏭", label: __("Fabrication") },
			],
			groupByCM: false,
			activeAlert: null,
			cmOpen: false,
			selectedCM: [...(this.store.filters.conducteurs || [])],
			// Infobulle flottante
			tipShow: false, tipText: "", tipX: 0, tipY: 0,
			sortKey: "flux",
			sortDir: -1,
			// Géométrie graphes semaine
			chartW: 300, chartH: 120, pad: 6,
			quickRanges: [
				{ label: __("7 j"), days: 7 },
				{ label: __("14 j"), days: 14 },
				{ label: __("30 j"), days: 30 },
				{ label: __("90 j"), days: 90 },
				{ label: __("Cette semaine"), type: "week" },
				{ label: __("Ce mois"), type: "month" },
			],
		};
	},
	computed: {
		data() { return this.store.data; },
		kpis() { return this.data ? this.data.kpis : {}; },
		prev() { return this.data ? this.data.kpis_prev : {}; },

		periodLabel() {
			const p = this.data.period;
			return `${this.fmtDate(p.start_date)} → ${this.fmtDate(p.end_date)}`;
		},
		prevLabel() {
			const p = this.data.period;
			return `(${this.fmtDate(p.prev_start)} → ${this.fmtDate(p.prev_end)})`;
		},

		kpiCards() {
			const k = this.kpis, pv = this.prev;
			return [
				this.card("ca", __("CA facturé"), fmtCompact(k.ca_periode), __("factures validées"), k.ca_periode, pv.ca_periode, false,
					__("Somme des factures de vente validées (hors acomptes et hors avoirs) rattachées à un chantier réel (heures estimées > 1), dont la date de facturation tombe dans la période.")),
				this.card("po", __("Commandé fournisseur"), fmtCompact(k.commande_fournisseur), __("commandes fournisseur"), k.commande_fournisseur, pv.commande_fournisseur, true,
					__("Somme des montants des lignes de commandes fournisseur (non annulées) rattachées à un chantier, dont la commande est datée dans la période.")),
				this.card("depenses", __("Dépenses"), fmtCompact(k.depenses), __("notes de frais"), k.depenses, pv.depenses, true,
					__("Somme des notes de frais (dépenses) rattachées à un chantier, dont la date de dépense tombe dans la période.")),
				this.card("fabrication", __("Fabrication VT"), fmtCompact(k.fabrication), __("coût fabrication"), k.fabrication, pv.fabrication, true,
					__("Coût des fabrications VT (hors annulées) rattachées à un chantier, créées pendant la période.")),
				this.card("hfact", __("Heures fact. / réalisées"), k.pct_heures + "%", `${k.heures_facturees}h / ${k.heures_realisees}h`, k.pct_heures, pv.pct_heures, false,
					__("Heures facturées (heures de main-d'œuvre portées par les factures de la période) ÷ heures réalisées (pointages validés, hors Fabrication et Livraison). Objectif : facturer autant qu'on produit.")),
				this.card("chantier", __("% temps chantier"), k.pct_chantier + "%", `${k.heures_chantier}h / ${k.heures_chantier + k.heures_hors_chantier}h`, k.pct_chantier, pv.pct_chantier, false,
					__("Part des heures passées sur un chantier : heures validées avec projet ÷ total des heures validées (chantier + hors chantier), hors Fabrication et Livraison.")),
				this.card("sav", __("Heures SAV"), k.heures_sav + " h", __("sur chantiers facturés"), k.heures_sav, pv.heures_sav, true,
					__("Heures validées pointées pendant la période sur des chantiers DÉJÀ facturés (statut Terminé) : reprises / SAV, qui grèvent la marge après coup.")),
				this.card("nb", __("Chantiers pointés"), String(k.nb_chantiers_pointes), __("sur la période"), k.nb_chantiers_pointes, pv.nb_chantiers_pointes, false,
					__("Nombre de chantiers distincts ayant reçu au moins un pointage (validé ou brouillon) sur la période.")),
			];
		},

		// --- Graphes hebdo ---
		weekly() { return this.data.weekly || []; },
		caTotal() { return this.weekly.reduce((s, w) => s + w.ca, 0); },
		maxCA() { return Math.max(1, ...this.weekly.map((w) => w.ca)); },
		maxWeekHours() { return Math.max(1, ...this.weekly.map((w) => w.val + w.draft)); },
		barW() { return this.weekly.length ? (this.chartW - 2 * this.pad) / this.weekly.length * 0.68 : 0; },

		// --- Donut activité ---
		activityTotal() { return (this.data.activity || []).reduce((s, a) => s + a.hours, 0); },
		donut() {
			const tot = this.activityTotal || 1;
			let offset = 25; // 12h position
			return (this.data.activity || []).map((a, i) => {
				const pct = (a.hours / tot) * 100;
				const seg = { label: a.activity_type, hours: a.hours, pct, offset, color: ACT_COLORS[i % ACT_COLORS.length] };
				offset = (offset - pct + 100) % 100;
				return seg;
			});
		},
		maxCM() { return Math.max(1, ...(this.data.conducteurs || []).map((c) => c.h_val + c.h_draft)); },

		// --- Tableau ---
		typeOptions() { return [...new Set(this.data.projects.map((p) => p.type_projet).filter(Boolean))].sort(); },
		conducteurLabel() {
			const n = this.selectedCM.length;
			return n === 0 ? __("Tous les conducteurs") : n === 1 ? this.cmName(this.selectedCM[0]) : `${n} ${__("conducteurs")}`;
		},
		maxHours() {
			return Math.max(1, ...this.data.projects.map((p) => p.heures_val + p.heures_draft));
		},
		alerts() {
			const P = this.data.projects;
			const k = this.kpis;
			const mk = (key, icon, label, tone, count, tip) => ({ key, icon, label, tone, count, tip });
			return [
				mk("nonval", "⏳", __("h non validées"), "warn", k.heures_non_validees,
					__("Heures pointées mais dont la feuille de temps est encore en brouillon (non soumise), sur la période. Cliquer pour AFFICHER ces feuilles de temps à valider.")),
				mk("over", "⏱", __("Dépassement heures"), "warn", P.filter((p) => p.heures_expected && p.heures_diff > 0).length,
					__("Chantiers dont le cumul d'heures pointées dépasse les heures prévues (vendues). Cliquer pour filtrer le tableau.")),
				mk("margin", "📉", __("Marge en chute"), "danger", P.filter((p) => p.marge_diff < -7).length,
					__("Chantiers dont la marge réelle est inférieure de plus de 7 points à la marge théorique. Cliquer pour filtrer.")),
				mk("sav", "🔧", __("SAV (repointage)"), "danger", P.filter((p) => p.is_sav).length,
					__("Chantiers déjà facturés (Terminé) sur lesquels des heures ont été repointées pendant la période. Cliquer pour filtrer.")),
				mk("inc", "⚠️", __("Incidents ouverts"), "danger", P.filter((p) => p.nb_incidents_ouverts > 0).length,
					__("Chantiers avec au moins un incident qualité non résolu. Cliquer pour OUVRIR la liste des incidents concernés.")),
				mk("norec", "📝", __("Facturé sans réception"), "warn", P.filter((p) => p.is_facture && !p.nb_receptions).length,
					__("Chantiers facturés (Terminé) sans réception de travaux enregistrée. Cliquer pour filtrer.")),
			].filter((a) => a.count > 0);
		},
		filtered() {
			let rows = this.data.projects.slice();
			const q = this.search.trim().toLowerCase();
			if (q) rows = rows.filter((p) => (p.project + " " + p.client + " " + p.conducteur_nom).toLowerCase().includes(q));
			if (this.facetType) rows = rows.filter((p) => p.type_projet === this.facetType);
			// Filtre par type de flux (OU sur les types cochés). Si tout est coché,
			// aucun filtrage (tous les chantiers ont au moins un flux).
			const ff = this.fluxFilter;
			if (!Object.values(ff).every(Boolean)) {
				rows = rows.filter((p) =>
					(ff.pointe && (p.heures_val + p.heures_draft) > 0) ||
					(ff.facture && p.ca_periode > 0) ||
					(ff.achat && p.po_periode > 0) ||
					(ff.depense && p.depense_periode > 0) ||
					(ff.fab && p.fab_periode > 0)
				);
			}
			if (this.activeAlert) rows = rows.filter((p) => this.matchAlert(p, this.activeAlert));
			const key = this.sortKey, dir = this.sortDir;
			const flux = (p) => (p.ca_periode || 0) + (p.po_periode || 0) + (p.depense_periode || 0) + (p.fab_periode || 0);
			rows.sort((a, b) => {
				let va = key === "heures_periode" ? a.heures_val + a.heures_draft : key === "flux" ? flux(a) : a[key];
				let vb = key === "heures_periode" ? b.heures_val + b.heures_draft : key === "flux" ? flux(b) : b[key];
				if (typeof va === "string") return va.localeCompare(vb) * dir;
				return ((va || 0) - (vb || 0)) * dir;
			});
			return rows;
		},
		grouped() {
			const map = {};
			this.filtered.forEach((p) => {
				const name = p.conducteur_nom || "Sans conducteur";
				(map[name] = map[name] || []).push(p);
			});
			return Object.keys(map).sort().map((name) => {
				const rows = map[name];
				return {
					name, rows,
					heures: rows.reduce((s, p) => s + p.heures_val + p.heures_draft, 0),
					ca: rows.reduce((s, p) => s + p.ca_periode, 0),
				};
			});
		},
	},
	methods: {
		fmtMoney,
		// --- Période ---
		iso(d) {
			return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
		},
		computeRange(q) {
			const end = new Date();
			let start = new Date();
			if (q.type === "week") {
				const dow = (start.getDay() + 6) % 7; // lundi = 0
				start.setDate(start.getDate() - dow);
			} else if (q.type === "month") {
				start = new Date(end.getFullYear(), end.getMonth(), 1);
			} else {
				start.setDate(start.getDate() - (q.days - 1));
			}
			return { start: this.iso(start), end: this.iso(end) };
		},
		applyQuick(q) {
			const r = this.computeRange(q);
			this.store.setPeriod(r.start, r.end);
		},
		// Décale la fenêtre de sa propre durée (‹ précédent / › suivant).
		shiftPeriod(dir) {
			const s = new Date(this.store.filters.start_date + "T00:00:00");
			const e = new Date(this.store.filters.end_date + "T00:00:00");
			const len = Math.round((e - s) / 86400000) + 1;
			s.setDate(s.getDate() + dir * len);
			e.setDate(e.getDate() + dir * len);
			this.store.setPeriod(this.iso(s), this.iso(e));
		},
		isActive(q) {
			const r = this.computeRange(q);
			return r.start === this.store.filters.start_date && r.end === this.store.filters.end_date;
		},
		onDate(which, e) {
			const v = e.target.value;
			if (!v) return;
			this.store.filters[which + "_date"] = v;
			this.store.reload();
		},
		// --- Filtres globaux (conducteurs / société → recalcul serveur) ---
		cmName(value) {
			const c = (this.data.meta.conducteurs || []).find((x) => x.value === value);
			return c ? c.label : value;
		},
		applyCM() {
			this.store.filters.conducteurs = [...this.selectedCM];
			this.store.reload();
		},
		clearCM() {
			this.selectedCM = [];
			this.cmOpen = false;
			this.applyCM();
		},
		onCompany(e) {
			this.store.filters.company = e.target.value || null;
			this.store.reload();
		},
		clearGlobal() {
			this.selectedCM = [];
			this.store.filters.conducteurs = [];
			this.store.filters.company = null;
			this.store.reload();
		},
		card(key, label, value, sub, cur, prev, invert, tip) {
			let delta = null, deltaText = "", deltaClass = "";
			if (prev != null && prev !== 0) {
				const pct = Math.round(((cur - prev) / Math.abs(prev)) * 100);
				delta = pct;
				const up = pct > 0;
				deltaText = (up ? "▲ +" : pct < 0 ? "▼ " : "= ") + pct + "%";
				const good = invert ? pct <= 0 : pct >= 0;
				deltaClass = pct === 0 ? "flat" : good ? "good" : "bad";
			} else if (prev === 0 && cur > 0) {
				delta = 100; deltaText = "▲ nouveau"; deltaClass = invert ? "bad" : "good";
			}
			return { key, label, value, sub, delta, deltaText, deltaClass, tone: "", tip };
		},
		toggleAlert(key) {
			// Certaines alertes ouvrent directement une liste (les autres filtrent
			// le tableau).
			if (key === "inc") {
				const names = this.data.projects.filter((p) => p.nb_incidents_ouverts > 0).map((p) => p.project);
				this.openIncidents(names);
				return;
			}
			if (key === "nonval") {
				const { start_date, end_date } = this.store.filters;
				frappe.route_options = { docstatus: 0, end_date: ["between", [start_date, end_date]] };
				frappe.set_route("List", "Timesheet");
				return;
			}
			this.activeAlert = this.activeAlert === key ? null : key;
		},
		// --- Infobulle flottante ---
		onTipMove(e) {
			const el = e.target.closest("[data-tip]");
			if (!el) { this.tipShow = false; return; }
			this.tipText = el.getAttribute("data-tip");
			this.tipShow = true;
			const w = 320;
			let x = e.clientX + 14;
			if (x + w > window.innerWidth) x = window.innerWidth - w - 12;
			this.tipX = x;
			this.tipY = e.clientY + 18;
		},
		// --- KPI cliquables (listes globales de la période) ---
		kpiClickable(key) { return ["ca", "po", "depenses", "fabrication"].includes(key); },
		kpiClick(key) {
			if (!this.kpiClickable(key)) return;
			const { start_date, end_date } = this.store.filters;
			const between = ["between", [start_date, end_date]];
			const map = {
				ca: { dt: "Sales Invoice", ro: { docstatus: 1, is_return: 0, is_down_payment_invoice: 0, posting_date: between } },
				po: { dt: "Purchase Order", ro: { transaction_date: between } },
				depenses: { dt: "Expense", ro: { expense_date: between } },
				fabrication: { dt: "Fabrication VT", ro: { creation: between } },
			};
			const cfg = map[key];
			frappe.route_options = cfg.ro;
			frappe.set_route("List", cfg.dt);
		},
		openIncidents(projectNames) {
			if (!projectNames || !projectNames.length) return;
			frappe.route_options = { project: ["in", projectNames] };
			frappe.set_route("List", "Quality Incident");
		},
		// Ouvre la liste Frappe filtrée sur le chantier (+ période pour les
		// montants/heures de la période). Frappe résout automatiquement `project`
		// vers la table enfant quand le champ n'est pas au niveau du document
		// (ex : Timesheet → Timesheet Detail).
		openDocs({ project, kind }) {
			const { start_date, end_date } = this.store.filters;
			const between = ["between", [start_date, end_date]];
			const map = {
				invoices: { dt: "Sales Invoice", ro: { project, posting_date: between } },
				invoices_all: { dt: "Sales Invoice", ro: { project } },
				// Le montant vient des lignes (Purchase Order Item.project) : on filtre
				// explicitement sur la table enfant pour que la liste corresponde.
				po: { dt: "Purchase Order", ro: { "Purchase Order Item.project": project, transaction_date: between } },
				timesheet: { dt: "Timesheet", ro: { project, end_date: between } },
				expense: { dt: "Expense", ro: { project, expense_date: between } },
				fab: { dt: "Fabrication VT", ro: { project, creation: between } },
			};
			const cfg = map[kind];
			if (!cfg) return;
			frappe.route_options = cfg.ro;
			frappe.set_route("List", cfg.dt);
		},
		matchAlert(p, key) {
			switch (key) {
				case "over": return p.heures_expected && p.heures_diff > 0;
				case "margin": return p.marge_diff < -7;
				case "sav": return p.is_sav;
				case "inc": return p.nb_incidents_ouverts > 0;
				case "norec": return p.is_facture && !p.nb_receptions;
			}
			return true;
		},
		sortBy(key) {
			if (this.sortKey === key) this.sortDir *= -1;
			else { this.sortKey = key; this.sortDir = key === "project" || key === "client" || key === "status" ? 1 : -1; }
		},
		fmtDate(d) { return d ? frappe.datetime.str_to_user(d) : ""; },
		weekShort(d) {
			const dt = new Date(d + "T00:00:00");
			return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "2-digit" }).format(dt);
		},
		barX(i) { return this.pad + i * ((this.chartW - 2 * this.pad) / this.weekly.length) + ((this.chartW - 2 * this.pad) / this.weekly.length - this.barW) / 2; },
		caBarH(v) { return (v / this.maxCA) * (this.chartH - 2 * this.pad); },
		hBarH(v) { return (v / this.maxWeekHours) * (this.chartH - 2 * this.pad); },
		cdW(v) { return (v / this.maxCM) * 100; },
	},
};
</script>

<style scoped>
.vtc-root { padding: 4px 2px 40px; font-family: var(--font-stack, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif); color: var(--text-color, #1f272e); }
.vtc-error { padding: 40px; text-align: center; color: var(--red-500, #c62828); }

.vtc-period { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin: 2px 4px 14px; }
.vtc-period-main { font-size: 17px; font-weight: 680; }
.vtc-period-sub { font-size: 12px; color: var(--text-muted, #6c7680); }
.vtc-refreshing { font-size: 12px; color: var(--blue-500, #1976d2); opacity: 0; transition: opacity .15s; display: inline-flex; align-items: center; gap: 4px; }
.vtc-refreshing.show { opacity: 1; }
.vtc-refreshing::before { content: ""; width: 11px; height: 11px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; display: inline-block; animation: vtc-spin .7s linear infinite; }
.vtc-refreshing { position: relative; }
@keyframes vtc-spin { to { transform: rotate(360deg); } }

/* Barre de chargement indéterminée */
.vtc-loadbar { position: sticky; top: 0; left: 0; right: 0; height: 3px; background: var(--control-bg, #eef1f3); overflow: hidden; border-radius: 3px; z-index: 30; margin-bottom: 6px; }
.vtc-loadbar .bar { position: absolute; height: 100%; width: 35%; background: var(--blue-500, #1976d2); border-radius: 3px; animation: vtc-slide 1.1s ease-in-out infinite; }
@keyframes vtc-slide { 0% { left: -35%; } 60% { left: 100%; } 100% { left: 100%; } }
.vtc-busy .vtc-kpis, .vtc-busy .vtc-alerts, .vtc-busy .vtc-charts, .vtc-busy .vtc-table-wrap, .vtc-busy .vtc-nopointage { opacity: .5; pointer-events: none; transition: opacity .15s; }

/* Barre de période */
.vtc-periodbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 2px 2px 16px; }
.vtc-nav { width: 30px; height: 30px; border: 1px solid var(--border-color, #e2e6ea); background: var(--control-bg, #fff); color: var(--text-color, #1f272e); border-radius: 8px; font-size: 18px; line-height: 1; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; }
.vtc-nav:hover { border-color: var(--blue-400, #64b5f6); color: var(--blue-600, #1565c0); }
.vtc-quick { display: inline-flex; gap: 4px; background: var(--control-bg, #eef1f3); padding: 3px; border-radius: 10px; }
.vtc-quick-btn { border: none; background: transparent; padding: 6px 12px; border-radius: 8px; font-size: 13px; font-weight: 560; color: var(--text-muted, #6c7680); cursor: pointer; transition: all .12s; }
.vtc-quick-btn:hover { color: var(--text-color, #1f272e); }
.vtc-quick-btn.active { background: var(--card-bg, #fff); color: var(--blue-600, #1565c0); box-shadow: 0 1px 3px rgba(0,0,0,.12); }
.vtc-dates { display: inline-flex; align-items: center; gap: 6px; }
.vtc-date-lbl { font-size: 12px; color: var(--text-muted, #6c7680); }
.vtc-date { padding: 6px 10px; border: 1px solid var(--border-color, #e2e6ea); border-radius: 8px; background: var(--control-bg, #fff); color: var(--text-color, #1f272e); font-size: 13px; font-family: inherit; }
.vtc-date:focus { outline: none; border-color: var(--blue-400, #64b5f6); }
.vtc-periodbar .vtc-refreshing { margin-left: auto; }

/* KPIs */
.vtc-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 14px; }
.vtc-kpi { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #e2e6ea); border-radius: 12px; padding: 14px 16px; cursor: help; }
.vtc-kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--text-muted, #6c7680); font-weight: 600; display: flex; align-items: center; gap: 4px; }
.vtc-info { opacity: .4; font-size: 10px; font-style: normal; }
.vtc-kpi:hover .vtc-info { opacity: .9; }
.vtc-kpi.clickable { cursor: pointer; transition: border-color .12s, transform .12s; }
.vtc-kpi.clickable:hover { border-color: var(--blue-400, #64b5f6); transform: translateY(-1px); }
.vtc-kpi.clickable .vtc-info { color: var(--blue-500, #1976d2); opacity: .9; }

/* Infobulle flottante */
.vtc-tooltip {
	position: fixed; z-index: 9999; max-width: 320px; pointer-events: none;
	background: #1f272e; color: #fff; padding: 8px 11px; border-radius: 8px;
	font-size: 12px; line-height: 1.45; box-shadow: 0 6px 24px rgba(0,0,0,.28);
}
.vtc-kpi-value { font-size: 28px; font-weight: 720; margin: 6px 0 2px; line-height: 1.1; }
.vtc-kpi-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.vtc-kpi-sub { font-size: 11px; color: var(--text-muted, #9aa4ad); }
.vtc-delta { font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 999px; white-space: nowrap; }
.vtc-delta.good { color: #1b7d3e; background: rgba(46,125,50,.14); }
.vtc-delta.bad { color: #c62828; background: rgba(198,40,40,.14); }
.vtc-delta.flat { color: var(--text-muted, #6c7680); background: var(--control-bg, #eef1f3); }

/* Alertes */
.vtc-alerts { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.vtc-alert { display: inline-flex; align-items: center; gap: 7px; border: 1px solid var(--border-color, #e2e6ea); background: var(--card-bg, #fff); border-radius: 10px; padding: 7px 12px; cursor: pointer; font-size: 13px; color: var(--text-color, #1f272e); transition: all .12s; }
.vtc-alert:hover { border-color: var(--gray-400, #b0b8bf); }
.vtc-alert.active { box-shadow: 0 0 0 2px var(--blue-300, #90caf9) inset; }
.vtc-alert.warn { border-left: 3px solid #f57c00; }
.vtc-alert.danger { border-left: 3px solid #c62828; }
.vtc-alert-n { font-weight: 800; font-size: 15px; }
.vtc-alert-lbl { color: var(--text-muted, #6c7680); }

/* Charts */
.vtc-charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin-bottom: 16px; }
.vtc-card { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #e2e6ea); border-radius: 12px; padding: 14px 16px; }
.vtc-chart.wide { grid-column: 1 / -1; }
.vtc-card-title { font-size: 12px; font-weight: 680; text-transform: uppercase; letter-spacing: .03em; color: var(--text-muted, #6c7680); margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
.vtc-svg { width: 100%; height: 110px; display: block; }
.bar-ca { fill: #1976d2; } .bar-val { fill: #2e7d32; } .bar-draft { fill: #ffb74d; }
.vtc-xlabels { display: flex; justify-content: space-around; font-size: 9px; color: var(--text-muted, #9aa4ad); margin-top: 2px; }
.vtc-chart-legend { font-size: 11px; color: var(--text-muted, #6c7680); margin-top: 8px; display: flex; align-items: center; gap: 6px; }
.vtc-chart-legend .dot { width: 9px; height: 9px; border-radius: 2px; display: inline-block; }
.dot.ca { background: #1976d2; } .dot.val { background: #2e7d32; } .dot.draft { background: #ffb74d; margin-left: 8px; }

.vtc-donut-wrap { display: flex; gap: 14px; align-items: center; }
.vtc-donut { width: 108px; height: 108px; flex: none; transform: rotate(-90deg); }
.donut-bg { fill: none; stroke: var(--control-bg, #eef1f3); stroke-width: 5; }
.donut-seg { fill: none; stroke-width: 5; }
.donut-c1 { transform: rotate(90deg); transform-origin: center; font-size: 8px; font-weight: 800; fill: var(--text-color, #1f272e); text-anchor: middle; }
.donut-c2 { transform: rotate(90deg); transform-origin: center; font-size: 3px; fill: var(--text-muted, #9aa4ad); text-anchor: middle; }
.vtc-donut-legend { flex: 1; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.vtc-donut-legend .leg { display: flex; align-items: center; gap: 6px; font-size: 12px; }
.vtc-donut-legend .sw { width: 10px; height: 10px; border-radius: 2px; flex: none; }
.vtc-donut-legend .nm { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-muted, #6c7680); }
.vtc-donut-legend .vl { font-weight: 700; }

.vtc-hbars { display: flex; flex-direction: column; gap: 8px; }
.vtc-hbar { display: grid; grid-template-columns: 140px 1fr 160px; align-items: center; gap: 10px; }
.vtc-hbar-name { font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.vtc-hbar-track { height: 14px; background: var(--control-bg, #eef1f3); border-radius: 7px; overflow: hidden; display: flex; }
.vtc-hbar-track .seg.val { background: #2e7d32; } .vtc-hbar-track .seg.draft { background: #ffb74d; }
.vtc-hbar-val { font-size: 12px; color: var(--text-color, #1f272e); }
.vtc-hbar-val .draft-txt { color: #e08600; } .vtc-hbar-nb { color: var(--text-muted, #9aa4ad); }

/* Filtres globaux */
.vtc-globalfilters { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin: -6px 2px 16px; }
.vtc-ms { position: relative; }
.vtc-ms-btn { display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; border: 1px solid var(--border-color, #e2e6ea); border-radius: 8px; background: var(--control-bg, #fff); color: var(--text-color, #1f272e); font-size: 13px; cursor: pointer; }
.vtc-ms-btn.on { border-color: var(--blue-400, #64b5f6); color: var(--blue-600, #1565c0); font-weight: 560; }
.vtc-ms-btn .caret { color: var(--text-muted, #9aa4ad); font-size: 10px; }
.vtc-ms-backdrop { position: fixed; inset: 0; z-index: 20; }
.vtc-ms-pop { position: absolute; top: calc(100% + 4px); left: 0; z-index: 21; min-width: 240px; max-height: 320px; overflow-y: auto; background: var(--card-bg, #fff); border: 1px solid var(--border-color, #e2e6ea); border-radius: 10px; box-shadow: 0 8px 30px rgba(0,0,0,.16); padding: 6px; }
.vtc-ms-opt { display: flex; align-items: center; gap: 8px; padding: 7px 10px; border-radius: 7px; font-size: 13px; cursor: pointer; color: var(--text-color, #1f272e); }
.vtc-ms-opt:hover { background: var(--control-bg, #f4f5f6); }
.vtc-ms-opt.all { color: var(--blue-600, #1565c0); font-weight: 560; border-bottom: 1px solid var(--border-color, #eef1f3); border-radius: 0; margin-bottom: 4px; }
.vtc-ms-empty { padding: 12px; font-size: 12px; color: var(--text-muted, #9aa4ad); text-align: center; }
.vtc-clearall { padding: 7px 12px; border: 1px dashed var(--border-color, #e2e6ea); border-radius: 8px; background: transparent; color: var(--text-muted, #6c7680); font-size: 13px; cursor: pointer; }
.vtc-clearall:hover { color: var(--text-color, #1f272e); }

/* Toolbar */
.vtc-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-bottom: 10px; }
.vtc-search { flex: 1; min-width: 200px; padding: 7px 12px; border: 1px solid var(--border-color, #e2e6ea); border-radius: 8px; background: var(--control-bg, #fff); color: var(--text-color, #1f272e); font-size: 13px; }
.vtc-select { padding: 7px 10px; border: 1px solid var(--border-color, #e2e6ea); border-radius: 8px; background: var(--control-bg, #fff); color: var(--text-color, #1f272e); font-size: 13px; }
.vtc-seg { display: inline-flex; gap: 3px; background: var(--control-bg, #eef1f3); padding: 3px; border-radius: 9px; }
.vtc-seg button { border: none; background: transparent; padding: 5px 12px; border-radius: 7px; font-size: 13px; font-weight: 540; color: var(--text-muted, #6c7680); cursor: pointer; }
.vtc-seg button.active { background: var(--card-bg, #fff); color: var(--blue-600, #1565c0); box-shadow: 0 1px 3px rgba(0,0,0,.12); }
.vtc-check { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-muted, #6c7680); cursor: pointer; }
.vtc-count { font-size: 12px; color: var(--text-muted, #9aa4ad); margin-left: auto; }

/* Filtres par type de flux */
.vtc-flux-filter { display: inline-flex; gap: 5px; flex-wrap: wrap; }
.flux-toggle { display: inline-flex; align-items: center; gap: 4px; padding: 5px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; cursor: pointer; border: 1px solid transparent; transition: all .12s; }
.flux-toggle.pointe { background: rgba(96, 125, 139, .14); color: #455a64; }
.flux-toggle.facture { background: rgba(46, 125, 50, .14); color: #2e7d32; }
.flux-toggle.achat { background: rgba(25, 118, 210, .14); color: #1565c0; }
.flux-toggle.depense { background: rgba(245, 124, 0, .16); color: #e65100; }
.flux-toggle.fab { background: rgba(126, 87, 194, .16); color: #6a3fb0; }
.flux-toggle.off { background: transparent; color: var(--text-muted, #9aa4ad); border-color: var(--border-color, #e2e6ea); text-decoration: line-through; }

/* Table */
.vtc-table-wrap { padding: 0; overflow-x: auto; }
.vtc-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.vtc-table th { text-align: left; padding: 11px 12px; font-size: 11px; text-transform: uppercase; letter-spacing: .03em; color: var(--text-muted, #6c7680); border-bottom: 1px solid var(--border-color, #e2e6ea); white-space: nowrap; position: sticky; top: 0; background: var(--card-bg, #fff); z-index: 1; }
.vtc-table th.sortable { cursor: pointer; user-select: none; }
.vtc-table th.num, .vtc-table td.num { text-align: right; }
.vtc-sortic { opacity: .35; font-size: 10px; } .vtc-sortic.on { opacity: 1; color: var(--blue-500, #1976d2); }
.vtc-table td { padding: 9px 12px; border-bottom: 1px solid var(--border-color, #f0f2f4); vertical-align: middle; }
.vtc-table tbody tr:hover td { background: var(--control-bg, #f7f9fa); }
.vtc-table tr.sav td { background: rgba(198,40,40,.045); }
.vtc-name a { font-weight: 620; color: var(--blue-600, #1565c0); }
.vtc-type { display: block; font-size: 10px; color: var(--text-muted, #9aa4ad); }
.vtc-client { color: var(--text-muted, #6c7680); max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.vtc-status { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 11px; font-weight: 600; color: #fff; }

.vtc-marge { min-width: 120px; }
.vtc-marge-track { position: relative; height: 7px; background: var(--control-bg, #eef1f3); border-radius: 4px; overflow: visible; }
.vtc-marge-track .fill { height: 100%; border-radius: 4px; }
.vtc-marge.up .fill { background: #2e7d32; } .vtc-marge.warn .fill { background: #f9a825; } .vtc-marge.down .fill { background: #c62828; }
.vtc-marge-track .theo { position: absolute; top: -2px; width: 2px; height: 11px; background: var(--text-color, #37474f); border-radius: 1px; }
.vtc-marge-txt { display: flex; align-items: center; gap: 6px; margin-top: 3px; font-size: 12px; }
.vtc-marge-txt .diff { font-size: 11px; color: var(--text-muted, #6c7680); }

.vtc-hours { min-width: 130px; }
.vtc-hours-track { position: relative; height: 7px; background: var(--control-bg, #eef1f3); border-radius: 4px; display: flex; overflow: visible; }
.vtc-hours-track .fill { height: 100%; } .vtc-hours-track .fill.val { background: #2e7d32; border-radius: 4px 0 0 4px; } .vtc-hours-track .fill.draft { background: #ffb74d; }
.vtc-hours.over .fill.val { background: #c62828; }
.vtc-hours-track .marker { position: absolute; top: -2px; width: 2px; height: 11px; background: var(--text-color, #37474f); }
.vtc-hours-txt { margin-top: 3px; font-size: 12px; }
.vtc-hours-txt .draft-txt { color: #e08600; } .vtc-hours-txt .exp { color: var(--text-muted, #9aa4ad); margin-left: 3px; }

.vtc-fact { min-width: 110px; }
.vtc-fact-track { height: 7px; background: var(--control-bg, #eef1f3); border-radius: 4px; overflow: hidden; }
.vtc-fact-track .fill { height: 100%; background: #1976d2; border-radius: 4px; }
.vtc-fact-txt { margin-top: 3px; font-size: 11px; color: var(--text-muted, #6c7680); }
.vtc-late { color: #c62828; font-weight: 700; }

.vtc-flags { white-space: nowrap; }
.vtc-flags .flag { display: inline-block; font-size: 10px; font-weight: 700; padding: 2px 5px; border-radius: 4px; margin-right: 3px; }
.vtc-flags .flag.sav { background: #c62828; color: #fff; }
.vtc-flags .flag.inc { background: rgba(245,124,0,.16); color: #e65100; }
.vtc-flags .flag.norec { background: rgba(198,40,40,.12); color: #c62828; }
.vtc-empty { text-align: center; color: var(--text-muted, #9aa4ad); padding: 30px; }

.vtc-group-row td { background: var(--control-bg, #f2f4f6); font-weight: 600; }
.vtc-group-name { font-size: 13px; } .vtc-group-meta { font-size: 12px; color: var(--text-muted, #6c7680); margin-left: 12px; }

/* Sans pointage */
.vtc-nopointage { margin-top: 16px; }
.vtc-badge-count { background: #f57c00; color: #fff; border-radius: 999px; padding: 1px 8px; font-size: 11px; }
.vtc-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.vtc-chip-np { display: inline-flex; align-items: center; gap: 8px; border: 1px solid var(--border-color, #e2e6ea); background: var(--control-bg, #f7f9fa); border-radius: 9px; padding: 7px 11px; font-size: 12px; cursor: pointer; color: var(--text-color, #1f272e); }
.vtc-chip-np:hover { border-color: var(--gray-400, #b0b8bf); }
.vtc-chip-np.late { border-left: 3px solid #c62828; }
.np-client { color: var(--text-muted, #6c7680); } .np-late { color: #c62828; font-weight: 700; } .np-cm { color: var(--text-muted, #9aa4ad); }

/* Skeletons */
.vtc-skel-card { height: 92px; border-radius: 12px; background: linear-gradient(90deg, var(--control-bg, #eef1f3), var(--border-color, #e4e8eb), var(--control-bg, #eef1f3)); background-size: 200% 100%; animation: vtc-sh 1.2s infinite; }
.vtc-skel-block { height: 300px; border-radius: 12px; margin-top: 12px; background: var(--control-bg, #eef1f3); }
@keyframes vtc-sh { to { background-position: -200% 0; } }
@media (prefers-reduced-motion: reduce) { .vtc-skel-card { animation: none; } }
</style>
