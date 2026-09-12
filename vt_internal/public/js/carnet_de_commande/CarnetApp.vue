<template>
	<div class="vcc-root" :class="{ 'vcc-busy': store.loading && data }" @mousemove="onTipMove" @mouseleave="tipShow = false">
		<div v-if="store.loading" class="vcc-loadbar"><div class="bar"></div></div>
		<div v-if="tipShow" class="vcc-tooltip" :style="{ left: tipX + 'px', top: tipY + 'px' }">{{ tipText }}</div>

		<div class="vcc-intro">
			<div class="vcc-intro-sub">
				{{ __('Order book') }} · {{ __('planification') }} · {{ __('multi-responsables') }} · {{ __('société') }} · {{ __('centre de coût') }}
			</div>
			<span class="vcc-refreshing" :class="{ show: store.loading }">{{ __('actualisation…') }}</span>
		</div>

		<div class="vcc-globalfilters" v-if="data">
			<div class="vcc-ms">
				<button class="vcc-ms-btn" :class="{ on: selectedCM.length }" @click="cmOpen = !cmOpen">
					👷 {{ conducteurLabel }} <span class="caret">▾</span>
				</button>
				<template v-if="cmOpen">
					<div class="vcc-ms-backdrop" @click="cmOpen = false"></div>
					<div class="vcc-ms-pop">
						<label class="vcc-ms-opt all" @click="clearCM">{{ __('Tous les responsables') }}</label>
						<label class="vcc-ms-opt" v-for="c in data.meta.conducteurs" :key="c.value">
							<input type="checkbox" :value="c.value" v-model="selectedCM" @change="applyCM" />
							{{ c.label }}
						</label>
						<div v-if="!data.meta.conducteurs.length" class="vcc-ms-empty">{{ __('Aucun responsable défini') }}</div>
					</div>
				</template>
			</div>

			<DropSelect
				icon="🏢"
				:model-value="store.filters.company || ''"
				:all-label="__('Toutes les sociétés')"
				:options="companyOptions"
				@update:model-value="(v) => { store.filters.company = v || null; store.reload(); }"
			/>
			<DropSelect
				v-if="costCenterOptions.length"
				icon="🏦"
				:model-value="store.filters.cost_center || ''"
				:all-label="__('Tous les centres de coût')"
				:options="costCenterOptions"
				@update:model-value="(v) => { store.filters.cost_center = v || null; store.reload(); }"
			/>
			<button v-if="hasGlobalFilters" class="vcc-clearall" @click="clearGlobal">
				✕ {{ __('Réinitialiser') }}
			</button>
		</div>

		<template v-if="store.loading && !store.data">
			<div class="vcc-kpis">
				<div class="vcc-skel-card" v-for="n in 5" :key="n"></div>
			</div>
			<div class="vcc-skel-block"></div>
		</template>

		<div v-else-if="store.error" class="vcc-error">{{ store.error }}</div>

		<template v-else-if="data">
			<div class="vcc-kpis">
				<div class="vcc-kpi" v-for="k in kpiCards" :key="k.key">
					<div class="vcc-kpi-label">{{ k.label }}</div>
					<div class="vcc-kpi-value" :style="{ color: k.color }">{{ k.value }}</div>
					<div class="vcc-kpi-sub">{{ k.sub }}</div>
				</div>
			</div>

			<div class="vcc-toolbar">
				<input class="vcc-search" v-model="search" :placeholder="__('Rechercher une commande, un client, une référence…')" />
				<DropSelect
					icon="🏷️"
					v-model="facetStatus"
					:all-label="__('Tous les statuts')"
					:options="statusOptions"
				/>
				<div class="vcc-seg">
					<button :class="{ active: facChantier === '' }" @click="facChantier = ''">{{ __('Chantier') }}</button>
					<button :class="{ active: facChantier === 'set' }" @click="facChantier = 'set'">{{ __('Statut renseigné') }}</button>
					<button :class="{ active: facChantier === 'empty' }" @click="facChantier = 'empty'">{{ __('Sans statut') }}</button>
				</div>
				<div class="vcc-flux-filter">
					<button
						v-for="ft in eventTypes" :key="ft.key"
						class="flux-toggle" :class="[ft.key, { off: !eventFilter[ft.key] }]"
						@click="eventFilter[ft.key] = !eventFilter[ft.key]"
					>{{ ft.icon }} {{ ft.label }}</button>
				</div>
				<label class="vcc-check"><input type="checkbox" v-model="onlyArc" /> {{ __('ARC en cours seulement') }}</label>
				<label class="vcc-check"><input type="checkbox" v-model="onlyOverdueArc" /> {{ __('Réception en retard') }}</label>
				<label class="vcc-check"><input type="checkbox" v-model="groupByCM" /> {{ __('Grouper par responsable') }}</label>
				<span class="vcc-count">{{ filtered.length }} / {{ data.rows.length }} {{ __('commandes') }}</span>
			</div>

			<div class="vcc-card vcc-table-wrap">
				<table class="vcc-table">
					<thead>
						<tr>
							<th @click="sortBy('name')" class="sortable">{{ __('Désignation') }} <SortIc :dir="sortDir" :on="sortKey === 'name'" /></th>
							<th @click="sortBy('customer_name')" class="sortable">{{ __('Client') }} <SortIc :dir="sortDir" :on="sortKey === 'customer_name'" /></th>
							<th @click="sortBy('status')" class="sortable">{{ __('Statut') }} <SortIc :dir="sortDir" :on="sortKey === 'status'" /></th>
							<th @click="sortBy('custom_construction_status')" class="sortable">{{ __('Statut du chantier') }} <SortIc :dir="sortDir" :on="sortKey === 'custom_construction_status'" /></th>
							<th @click="sortBy('nb_arcs')" class="sortable" :data-tip="__('Commandes fournisseur soumises, non entièrement reçues. Date = réception prévue. Rouge = en retard.')">{{ __('ARC en cours et date de réception') }} <SortIc :dir="sortDir" :on="sortKey === 'nb_arcs'" /></th>
							<th @click="sortBy('nb_events')" class="sortable" :data-tip="__('VT (visite technique) · Pose (fiche de travail) · autres événements. Les dates passées sont estompées.')">{{ __('Événements') }} <SortIc :dir="sortDir" :on="sortKey === 'nb_events'" /></th>
							<th @click="sortBy('reference_piece')" class="sortable">{{ __('Référence') }} <SortIc :dir="sortDir" :on="sortKey === 'reference_piece'" /></th>
							<th @click="sortBy('remaining_amount')" class="sortable num">{{ __('Reste à facturer') }} <SortIc :dir="sortDir" :on="sortKey === 'remaining_amount'" /></th>
							<th @click="sortBy('total')" class="sortable num">{{ __('Total HT') }} <SortIc :dir="sortDir" :on="sortKey === 'total'" /></th>
							<th @click="sortBy('delivery_date')" class="sortable">{{ __('Date de livraison') }} <SortIc :dir="sortDir" :on="sortKey === 'delivery_date'" /></th>
							<th @click="sortBy('hours_total')" class="sortable num">{{ __("h total") }} <SortIc :dir="sortDir" :on="sortKey === 'hours_total'" /></th>
							<th @click="sortBy('hours_solde')" class="sortable num">{{ __("h solde") }} <SortIc :dir="sortDir" :on="sortKey === 'hours_solde'" /></th>
							<th @click="sortBy('age')" class="sortable num">{{ __('Age') }} <SortIc :dir="sortDir" :on="sortKey === 'age'" /></th>
							<th @click="sortBy('construction_manager_name')" class="sortable">{{ __('Responsable') }} <SortIc :dir="sortDir" :on="sortKey === 'construction_manager_name'" /></th>
						</tr>
					</thead>
					<template v-if="groupByCM">
						<tbody v-for="g in grouped" :key="g.name">
							<tr class="vcc-group-row">
								<td colspan="14">
									<span class="vcc-group-name">👷 {{ g.name }}</span>
									<span class="vcc-group-meta">{{ g.rows.length }} {{ __('commandes') }} · {{ fmtCompact(g.reste) }}</span>
								</td>
							</tr>
							<OrderRow
								v-for="row in g.rows" :key="row.name" :row="row"
								@open-project="store.openProject"
								@open-doc="openDoc"
								@edit-status="editConstructionStatus"
							/>
						</tbody>
					</template>
					<tbody v-else>
						<OrderRow
							v-for="row in filtered" :key="row.name" :row="row"
							@open-project="store.openProject"
							@open-doc="openDoc"
							@edit-status="editConstructionStatus"
						/>
						<tr v-if="!filtered.length"><td colspan="14" class="vcc-empty">{{ __('Aucune commande') }}</td></tr>
					</tbody>
					<tfoot v-if="filtered.length">
						<tr class="vcc-total-row">
							<td>{{ __('Total') }}</td>
							<td>{{ totals.count }} {{ __('commandes') }}</td>
							<td></td>
							<td></td>
							<td>{{ totals.arcs }} {{ __('ARC') }}</td>
							<td>{{ totals.events }} {{ __('évt.') }}</td>
							<td></td>
							<td class="num">{{ fmtMoney(totals.reste) }}</td>
							<td class="num">{{ fmtMoney(totals.total) }}</td>
							<td></td>
							<td class="num">{{ Math.round(totals.hTotal) }}</td>
							<td class="num">{{ Math.round(totals.hSolde) }}</td>
							<td></td>
							<td></td>
						</tr>
					</tfoot>
				</table>
			</div>

			<div class="vcc-legend">
				<span class="vcc-leg vt">🔍 {{ __('Visite technique') }}</span>
				<span class="vcc-leg ft">📋 {{ __('Pose') }}</span>
				<span class="vcc-leg ev">📅 {{ __('Autre événement') }}</span>
				<span class="vcc-leg overdue">{{ __('Date rouge') }} = {{ __('réception prévue dépassée') }}</span>
				<span class="vcc-leg">{{ __('Client') }} = {{ __('vrai nom (jamais le code comptable)') }}</span>
			</div>
		</template>
	</div>
</template>

<script>
import { h } from "vue";
import OrderRow from "./OrderRow.vue";
import DropSelect from "./DropSelect.vue";
import { fmtMoney, fmtCompact } from "./helpers.js";

const SortIc = (props) =>
	h("span", { class: "vcc-sortic" + (props.on ? " on" : "") }, props.on ? (props.dir === 1 ? "▲" : "▼") : "⇅");
SortIc.props = ["dir", "on"];

export default {
	name: "CarnetApp",
	components: { SortIc, OrderRow, DropSelect },
	props: { store: Object },
	data() {
		return {
			search: "",
			facetStatus: "",
			facChantier: "",
			onlyArc: false,
			onlyOverdueArc: false,
			groupByCM: false,
			eventFilter: { vt: true, ft: true, event: true },
			eventTypes: [
				{ key: "vt", icon: "🔍", label: __("VT") },
				{ key: "ft", icon: "📋", label: __("Pose") },
				{ key: "event", icon: "📅", label: __("Autres") },
			],
			cmOpen: false,
			selectedCM: [...(this.store.filters.conducteurs || [])],
			tipShow: false, tipText: "", tipX: 0, tipY: 0,
			sortKey: "delivery_date",
			sortDir: 1,
		};
	},
	computed: {
		data() { return this.store.data; },
		companyOptions() {
			return (this.data.meta.companies || []).map((c) =>
				typeof c === "string" ? { value: c, label: c } : { value: c.value || c, label: c.label || c.value || c }
			);
		},
		costCenterOptions() {
			return this.data.meta.cost_centers || [];
		},
		statusOptions() {
			return this.data.meta.so_statuses || [];
		},
		conducteurLabel() {
			const n = this.selectedCM.length;
			return n === 0 ? __("Tous les responsables") : n === 1 ? this.cmName(this.selectedCM[0]) : `${n} ${__("responsables")}`;
		},
		hasGlobalFilters() {
			return this.selectedCM.length || this.store.filters.company || this.store.filters.cost_center || this.store.filters.status;
		},
		kpiCards() {
			const s = this.data.summary || {};
			return [
				{ key: "n", label: __("Commandes"), value: String(s.nb_orders || 0), sub: __("Carnet ouvert"), color: "#1976d2" },
				{ key: "raf", label: __("Reste à facturer"), value: fmtCompact(s.remaining_ht), sub: __("HT"), color: "#2e7d32" },
				{ key: "h", label: __("Heures"), value: Math.round(s.hours_solde || 0) + "h", sub: __("solde / {0}h total", [Math.round(s.hours_total || 0)]), color: "#6a3fb0" },
				{ key: "arc", label: __("ARC en cours"), value: String(s.nb_arcs || 0), sub: __("réceptions attendues"), color: "#1565c0" },
				{ key: "ev", label: __("Événements"), value: String(s.nb_events || 0), sub: __("VT / pose / autres"), color: "#00838f" },
			];
		},
		filtered() {
			let rows = (this.data.rows || []).slice();
			const q = this.search.trim().toLowerCase();
			if (q) {
				rows = rows.filter((r) =>
					[r.name, r.customer_name, r.reference_piece, r.construction_manager_name, r.custom_construction_status, r.project]
						.join(" ")
						.toLowerCase()
						.includes(q)
				);
			}
			if (this.facetStatus) rows = rows.filter((r) => r.status === this.facetStatus);
			if (this.facChantier === "set") rows = rows.filter((r) => (r.custom_construction_status || "").trim());
			if (this.facChantier === "empty") rows = rows.filter((r) => !(r.custom_construction_status || "").trim());
			if (this.onlyArc) rows = rows.filter((r) => (r.pending_arcs || []).length);
			if (this.onlyOverdueArc) rows = rows.filter((r) => (r.pending_arcs || []).some((a) => a.overdue));
			const ef = this.eventFilter;
			if (!Object.values(ef).every(Boolean)) {
				rows = rows.filter((r) => (r.events || []).some((e) => ef[e.kind]));
			}
			const key = this.sortKey;
			const dir = this.sortDir;
			rows.sort((a, b) => {
				const va = this.sortValue(a, key);
				const vb = this.sortValue(b, key);
				if (typeof va === "string" && typeof vb === "string") return va.localeCompare(vb, "fr") * dir;
				if (va == null && vb == null) return 0;
				if (va == null) return 1;
				if (vb == null) return -1;
				return ((va || 0) - (vb || 0)) * dir;
			});
			return rows;
		},
		totals() {
			const r = this.filtered;
			const sum = (fn) => r.reduce((s, row) => s + (fn(row) || 0), 0);
			return {
				count: r.length,
				reste: sum((row) => row.remaining_amount),
				total: sum((row) => row.total),
				hTotal: sum((row) => row.hours_total),
				hSolde: sum((row) => row.hours_solde),
				arcs: sum((row) => (row.pending_arcs || []).length),
				events: sum((row) => (row.events || []).length),
			};
		},
		grouped() {
			const map = {};
			this.filtered.forEach((row) => {
				const name = row.construction_manager_name || __("Sans responsable");
				(map[name] = map[name] || []).push(row);
			});
			return Object.keys(map).sort((a, b) => a.localeCompare(b, "fr")).map((name) => ({
				name,
				rows: map[name],
				reste: map[name].reduce((s, row) => s + (row.remaining_amount || 0), 0),
			}));
		},
	},
	methods: {
		fmtMoney,
		fmtCompact,
		sortValue(row, key) {
			if (key === "nb_arcs") return (row.pending_arcs || []).length;
			if (key === "nb_events") return (row.events || []).length;
			return row[key];
		},
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
		clearGlobal() {
			this.selectedCM = [];
			this.store.filters.conducteurs = [];
			this.store.filters.company = null;
			this.store.filters.cost_center = null;
			this.store.filters.status = null;
			this.store.reload();
		},
		openDoc(dt, name) {
			this.store.openDoc(dt, name);
		},
		editConstructionStatus(row) {
			const d = new frappe.ui.Dialog({
				title: __("Modifier le statut construction") + " · " + row.name,
				fields: [
					{
						fieldname: "status",
						fieldtype: "Small Text",
						label: __("Statut construction"),
						default: row.custom_construction_status || "",
					},
				],
				primary_action_label: __("Enregistrer"),
				primary_action: (values) => {
					frappe.call({
						method: "frappe.client.set_value",
						args: {
							doctype: "Sales Order",
							name: row.name,
							fieldname: "custom_construction_status",
							value: values.status || "",
						},
						callback: () => {
							frappe.show_alert({ message: __("Statut mis à jour"), indicator: "green" });
							row.custom_construction_status = (values.status || "").trim();
							d.hide();
						},
					});
				},
			});
			d.show();
		},
		sortBy(key) {
			if (this.sortKey === key) this.sortDir *= -1;
			else {
				this.sortKey = key;
				this.sortDir = ["name", "customer_name", "status", "custom_construction_status", "reference_piece", "construction_manager_name", "delivery_date"].includes(key) ? 1 : -1;
			}
		},
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
	},
};
</script>

<style scoped>
.vcc-root { padding: 4px 2px 40px; font-family: var(--font-stack, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif); color: var(--text-color, #1f272e); }
.vcc-error { padding: 40px; text-align: center; color: var(--red-500, #c62828); }
.vcc-intro { display: flex; align-items: baseline; gap: 12px; margin: 2px 2px 14px; flex-wrap: wrap; }
.vcc-intro-sub { font-size: 13px; color: var(--text-muted, #6c7680); }
.vcc-refreshing { font-size: 12px; color: var(--blue-500, #1976d2); opacity: 0; margin-left: auto; display: inline-flex; align-items: center; gap: 4px; }
.vcc-refreshing.show { opacity: 1; }
.vcc-refreshing::before { content: ""; width: 11px; height: 11px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; display: inline-block; animation: vcc-spin .7s linear infinite; }
@keyframes vcc-spin { to { transform: rotate(360deg); } }

.vcc-loadbar { position: sticky; top: 0; height: 3px; background: var(--control-bg, #eef1f3); overflow: hidden; border-radius: 3px; z-index: 30; margin-bottom: 6px; }
.vcc-loadbar .bar { position: absolute; height: 100%; width: 35%; background: var(--blue-500, #1976d2); border-radius: 3px; animation: vcc-slide 1.1s ease-in-out infinite; }
@keyframes vcc-slide { 0% { left: -35%; } 60% { left: 100%; } 100% { left: 100%; } }
.vcc-busy .vcc-kpis, .vcc-busy .vcc-table-wrap { opacity: .5; pointer-events: none; }

.vcc-tooltip {
	position: fixed; z-index: 9999; max-width: 320px; pointer-events: none;
	background: #1f272e; color: #fff; padding: 8px 11px; border-radius: 8px;
	font-size: 12px; line-height: 1.45; box-shadow: 0 6px 24px rgba(0,0,0,.28);
}

.vcc-globalfilters { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin: 0 2px 16px; }
.vcc-ms { position: relative; }
.vcc-ms-btn { display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; border: 1px solid var(--border-color, #e2e6ea); border-radius: 8px; background: var(--control-bg, #fff); color: var(--text-color, #1f272e); font-size: 13px; cursor: pointer; }
.vcc-ms-btn.on { border-color: var(--blue-400, #64b5f6); color: var(--blue-600, #1565c0); font-weight: 560; }
.vcc-ms-btn .caret { color: var(--text-muted, #9aa4ad); font-size: 10px; }
.vcc-ms-backdrop { position: fixed; inset: 0; z-index: 20; }
.vcc-ms-pop { position: absolute; top: calc(100% + 4px); left: 0; z-index: 21; min-width: 240px; max-height: 320px; overflow-y: auto; background: var(--card-bg, #fff); border: 1px solid var(--border-color, #e2e6ea); border-radius: 10px; box-shadow: 0 8px 30px rgba(0,0,0,.16); padding: 6px; }
.vcc-ms-opt { display: flex; align-items: center; gap: 8px; padding: 7px 10px; border-radius: 7px; font-size: 13px; cursor: pointer; }
.vcc-ms-opt:hover { background: var(--control-bg, #f4f5f6); }
.vcc-ms-opt.all { color: var(--blue-600, #1565c0); font-weight: 560; border-bottom: 1px solid var(--border-color, #eef1f3); border-radius: 0; margin-bottom: 4px; }
.vcc-ms-empty { padding: 12px; font-size: 12px; color: var(--text-muted, #9aa4ad); text-align: center; }
.vcc-clearall { padding: 7px 12px; border: 1px dashed var(--border-color, #e2e6ea); border-radius: 8px; background: transparent; color: var(--text-muted, #6c7680); font-size: 13px; cursor: pointer; }

.vcc-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 16px; }
.vcc-kpi { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #e2e6ea); border-radius: 12px; padding: 14px 16px; text-align: center; }
.vcc-kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--text-muted, #6c7680); font-weight: 600; }
.vcc-kpi-value { font-size: 32px; font-weight: 720; margin: 6px 0 2px; line-height: 1.1; }
.vcc-kpi-sub { font-size: 11px; color: var(--text-muted, #9aa4ad); }

.vcc-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-bottom: 10px; }
.vcc-search { flex: 1; min-width: 200px; padding: 7px 12px; border: 1px solid var(--border-color, #e2e6ea); border-radius: 8px; background: var(--control-bg, #fff); color: var(--text-color, #1f272e); font-size: 13px; }
.vcc-seg { display: inline-flex; gap: 3px; background: var(--control-bg, #eef1f3); padding: 3px; border-radius: 9px; }
.vcc-seg button { border: none; background: transparent; padding: 5px 12px; border-radius: 7px; font-size: 13px; font-weight: 540; color: var(--text-muted, #6c7680); cursor: pointer; }
.vcc-seg button.active { background: var(--card-bg, #fff); color: var(--blue-600, #1565c0); box-shadow: 0 1px 3px rgba(0,0,0,.12); }
.vcc-check { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-muted, #6c7680); cursor: pointer; }
.vcc-count { font-size: 12px; color: var(--text-muted, #9aa4ad); margin-left: auto; }
.vcc-flux-filter { display: inline-flex; gap: 5px; flex-wrap: wrap; }
.flux-toggle { display: inline-flex; align-items: center; gap: 4px; padding: 5px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; cursor: pointer; border: 1px solid transparent; }
.flux-toggle.vt { background: rgba(0,131,143,.14); color: #00838f; }
.flux-toggle.ft { background: rgba(92,107,192,.16); color: #4f5bd5; }
.flux-toggle.event { background: rgba(84,110,122,.14); color: #546e7a; }
.flux-toggle.off { background: transparent; color: var(--text-muted, #9aa4ad); border-color: var(--border-color, #e2e6ea); text-decoration: line-through; }

.vcc-card { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #e2e6ea); border-radius: 12px; }
.vcc-table-wrap { padding: 0; overflow-x: auto; }
.vcc-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.vcc-table th { text-align: left; padding: 11px 12px; font-size: 11px; text-transform: uppercase; letter-spacing: .03em; color: var(--text-muted, #6c7680); border-bottom: 1px solid var(--border-color, #e2e6ea); white-space: nowrap; position: sticky; top: 0; background: var(--card-bg, #fff); z-index: 1; }
.vcc-table th.sortable { cursor: pointer; user-select: none; }
.vcc-table th.num, .vcc-table td.num { text-align: right; }
.vcc-sortic { opacity: .35; font-size: 10px; } .vcc-sortic.on { opacity: 1; color: var(--blue-500, #1976d2); }
.vcc-table :deep(td) { padding: 9px 12px; border-bottom: 1px solid var(--border-color, #f0f2f4); vertical-align: middle; }
.vcc-table :deep(tbody tr:hover td) { background: var(--control-bg, #f7f9fa); }
.vcc-empty { text-align: center; color: var(--text-muted, #9aa4ad); padding: 30px; }
.vcc-group-row td { background: var(--control-bg, #f2f4f6); font-weight: 600; }
.vcc-group-name { font-size: 13px; } .vcc-group-meta { font-size: 12px; color: var(--text-muted, #6c7680); margin-left: 12px; }
.vcc-total-row td { position: sticky; bottom: 0; background: var(--card-bg, #fff); border-top: 2px solid var(--border-color, #d1d8dd); font-weight: 680; font-size: 13px; padding: 10px 12px; }

.vcc-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; font-size: 12px; color: var(--text-muted, #6c7680); align-items: center; }
.vcc-leg { display: inline-flex; align-items: center; gap: 5px; }
.vcc-leg.overdue { color: #c62828; }

.vcc-skel-card { height: 92px; border-radius: 12px; background: linear-gradient(90deg, var(--control-bg, #eef1f3), var(--border-color, #e4e8eb), var(--control-bg, #eef1f3)); background-size: 200% 100%; animation: vcc-sh 1.2s infinite; }
.vcc-skel-block { height: 300px; border-radius: 12px; margin-top: 12px; background: var(--control-bg, #eef1f3); }
@keyframes vcc-sh { to { background-position: -200% 0; } }
</style>
