<template>
	<div class="vcc-arcs" v-if="arcs.length">
		<button
			v-for="po in arcs"
			:key="po.name"
			class="vcc-arc"
			:data-tip="arcTip(po)"
			@click.stop="$emit('open', po.name)"
		>
			<span class="vcc-arc-name">{{ po.supplier_name }}</span>
			<span v-if="po.schedule_date" class="vcc-arc-date" :class="{ overdue: po.overdue }">{{ fmtDate(po.schedule_date) }}</span>
			<span v-if="!po.ar_valide" class="vcc-arc-warn">{{ __('AR à valider') }}</span>
		</button>
	</div>
	<span v-else class="vcc-muted">—</span>
</template>

<script>
import { fmtDate } from "./helpers.js";

export default {
	name: "ArcList",
	props: { arcs: { type: Array, default: () => [] } },
	emits: ["open"],
	methods: {
		fmtDate,
		arcTip(po) {
			const bits = [po.name, po.supplier_name];
			if (po.schedule_date) bits.push(__("réception prévue") + " " + fmtDate(po.schedule_date));
			if (po.overdue) bits.push(__("en retard"));
			if (!po.ar_valide) bits.push(__("AR à valider"));
			return bits.filter(Boolean).join(" · ");
		},
	},
};
</script>

<style scoped>
.vcc-arcs { display: flex; flex-direction: column; gap: 4px; min-width: 160px; }
.vcc-arc {
	display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
	border: none; background: transparent; padding: 0; margin: 0;
	font: inherit; color: inherit; cursor: pointer; text-align: left;
}
.vcc-arc:hover .vcc-arc-name { text-decoration: underline; }
.vcc-arc-name { color: var(--blue-600, #1565c0); font-weight: 560; }
.vcc-arc-date { color: #555; white-space: nowrap; font-size: 12px; }
.vcc-arc-date.overdue { color: #c62828; font-weight: 700; }
.vcc-arc-warn {
	background: #fff3cd; color: #8a6d3b; font-size: 10px;
	padding: 1px 5px; border-radius: 3px; font-weight: 700;
}
.vcc-muted { color: var(--text-muted, #9aa4ad); }
</style>
