<template>
	<tr>
		<td class="vcc-name">
			<a href="#" @click.prevent="openDesignation">{{ row.name }}</a>
		</td>
		<td class="vcc-client" :data-tip="row.customer_name">{{ row.customer_name }}</td>
		<td class="vcc-nowrap">{{ fmtDate(row.delivery_date) || '—' }}</td>
		<td>
			<span class="vcc-pill" :style="statusStyle" :data-tip="__('Statut interne VT (même indicateur que la liste des commandes)')">{{ statusLabel }}</span>
		</td>
		<td>
			<button
				class="vcc-chantier"
				:class="{ empty: !row.custom_construction_status }"
				:data-tip="__('Cliquer pour modifier le statut du chantier')"
				@click.stop="$emit('edit-status', row)"
			>{{ row.custom_construction_status || __('＋ statut') }}</button>
		</td>
		<td>
			<ArcList :arcs="row.pending_arcs || []" @open="(name) => $emit('open-doc', 'Purchase Order', name)" />
		</td>
		<td>
			<EventBadges :events="row.events || []" @open="(name) => $emit('open-doc', 'Event', name)" />
		</td>
		<td class="vcc-ref">{{ row.reference_piece || '—' }}</td>
		<td class="num">{{ fmtMoney(row.remaining_amount) }}</td>
		<td class="num">{{ fmtMoney(row.total) }}</td>
		<td class="num">{{ fmtHours(row.hours_total) }}</td>
		<td class="num">
			<span :class="'vcc-hsolde ' + hoursTone(row.hours_solde)">{{ fmtHours(row.hours_solde) }}</span>
		</td>
		<td class="num">
			<span v-if="row.age != null" :class="'vcc-age ' + ageTone(row.age)">{{ row.age }}</span>
			<span v-else class="vcc-muted">—</span>
		</td>
		<td class="vcc-cm" :data-tip="row.construction_manager">{{ row.construction_manager_name || '—' }}</td>
	</tr>
</template>

<script>
import ArcList from "./ArcList.vue";
import EventBadges from "./EventBadges.vue";
import { salesOrderStatus, ORDER_STATUS_COLORS, fmtMoney, fmtDate, ageTone, hoursTone } from "./helpers.js";

export default {
	name: "OrderRow",
	components: { ArcList, EventBadges },
	props: { row: Object },
	emits: ["open-project", "open-doc", "edit-status"],
	computed: {
		indicator() {
			return salesOrderStatus(this.row) || { label: this.row.status || "—", color: "gray" };
		},
		statusLabel() {
			return this.indicator.label;
		},
		statusStyle() {
			const c = ORDER_STATUS_COLORS[this.indicator.color] || ORDER_STATUS_COLORS.gray;
			return { color: c.color, background: c.bg };
		},
	},
	methods: {
		fmtMoney,
		fmtDate,
		ageTone,
		hoursTone,
		fmtHours(n) {
			if (n == null || n === "") return "—";
			const v = Math.round(Number(n) * 10) / 10;
			return `${v}`.replace(".", ",");
		},
		openDesignation() {
			if (this.row.project) this.$emit("open-project", this.row.project);
			else this.$emit("open-doc", "Sales Order", this.row.name);
		},
	},
};
</script>

<style scoped>
.num { text-align: right; white-space: nowrap; }
.vcc-nowrap { white-space: nowrap; }
.vcc-name a { font-weight: 620; color: var(--blue-600, #1565c0); }
.vcc-client { color: var(--text-muted, #6c7680); max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.vcc-ref { color: var(--text-color, #1f272e); white-space: nowrap; }
.vcc-cm { color: var(--text-muted, #6c7680); max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.vcc-muted { color: var(--text-muted, #9aa4ad); }
.vcc-pill {
	display: inline-block; padding: 2px 9px; border-radius: 999px;
	font-size: 11px; font-weight: 700; white-space: nowrap;
}
.vcc-chantier {
	border: none; background: transparent; padding: 0; margin: 0;
	font: inherit; color: var(--text-color, #1f272e); cursor: pointer;
	text-align: left; white-space: pre-line; max-width: 200px;
}
.vcc-chantier:hover { color: var(--blue-600, #1565c0); }
.vcc-chantier.empty { color: var(--text-muted, #9aa4ad); font-style: italic; }
.vcc-age.ok { color: #2e7d32; font-weight: 600; }
.vcc-age.warn { color: #e65100; font-weight: 600; }
.vcc-age.late { color: #c62828; font-weight: 700; }
.vcc-hsolde.ok { color: #2e7d32; }
.vcc-hsolde.late { color: #c62828; font-weight: 700; }
</style>
