// Enrichit le popup calendrier : liens FDT/VT, Google Maps, description

frappe.after_ajax(() => {
	// Sur mobile, supprime les tooltips hover du calendrier qui clignotent au toucher
	if (window.matchMedia('(hover: none)').matches) {
		document.addEventListener('mouseenter', (e) => {
			if (e.target.closest('.fc-event')) e.stopImmediatePropagation();
		}, true);
	}

	const observer = new MutationObserver((mutations) => {
		for (const mutation of mutations) {
			for (const node of mutation.addedNodes) {
				if (node.nodeType !== 1 || !node.classList?.contains('evp-popover')) continue;
				if (node.dataset.vtEnhanced) continue;
				node.dataset.vtEnhanced = '1';
				vt_enhance_event_popup(node);
			}
		}
	});
	observer.observe(document.body, { childList: true });
});

async function vt_enhance_event_popup(popover_el) {
	try {
		const trigger = document.querySelector(`[aria-describedby="${popover_el.id}"]`);
		if (!trigger?.href) return;

		const event_name = decodeURIComponent(new URL(trigger.href).pathname.split('/').pop());
		if (!event_name) return;

		const doc = await frappe.model.with_doc('Event', event_name);
		if (!doc) return;

		const has_fdt = !!doc.custom_fiche_de_travail;
		const has_vt = !!doc.custom_visite_technique;

		if (!has_fdt && !has_vt) return;

		// Le document de référence pour l'adresse et la description (FDT prioritaire)
		const primary_doctype = has_fdt ? 'Fiche de travail' : 'Visite Technique';
		const primary_name = has_fdt ? doc.custom_fiche_de_travail : doc.custom_visite_technique;

		let address_display = null;
		let linked_description = null;

		try {
			const r = await frappe.db.get_value(primary_doctype, primary_name, ['address', 'description']);
			const data = r?.message || {};

			if (data.description) {
				linked_description = data.description;
			}

			if (data.address) {
				const addr_r = await frappe.db.get_value('Address', data.address,
					['address_line1', 'address_line2', 'city', 'pincode']);
				const addr = addr_r?.message || {};
				const parts = [
					addr.address_line1,
					addr.address_line2,
					addr.pincode && addr.city ? `${addr.pincode} ${addr.city}` : (addr.city || addr.pincode),
				].filter(Boolean);
				if (parts.length > 0) {
					address_display = parts.join(', ');
				}
			}
		} catch (_) {}

		if (!document.contains(popover_el)) return;

		const body = popover_el.querySelector('.evp-scroller');
		if (!body) return;

		// Supprime toute section VT existante pour éviter les doublons
		body.querySelector('.vt-popup-section')?.remove();

		const section = document.createElement('div');
		section.className = 'vt-popup-section';
		section.style.cssText = 'border-top:1px solid var(--border-color);padding-top:10px;margin-top:4px;display:flex;flex-direction:column;gap:6px;';
		// Stoppe mousedown uniquement : empêche le "clic en dehors" du calendrier
		// sans perturber les événements touch sur mobile
		section.addEventListener('mousedown', (e) => e.stopPropagation());

		// Bouton : démarrer la feuille de temps en un clic
		// FDT -> activité "Chantier" liée à la fiche ; VT -> activité "Visite technique"
		const timer_args = has_fdt
			? { action: 'start_construction', activity_type: 'Chantier', fiche_de_travail: doc.custom_fiche_de_travail }
			: { action: 'start_construction', activity_type: 'Visite technique' };
		const timer_label = has_fdt ? '▶️ Démarrer le chrono (chantier)' : '▶️ Démarrer le chrono (visite technique)';
		section.appendChild(vt_make_popup_action_btn(timer_label, 'green', (btn) => {
			btn.style.pointerEvents = 'none';
			btn.style.opacity = '0.6';
			frappe.call({ method: 'timesheet_post_api', args: timer_args })
				.then(() => {
					frappe.show_alert({ message: 'Tâche commencée', indicator: 'green' }, 5);
					vt_close_event_popup(popover_el);
				})
				.catch(() => {
					btn.style.pointerEvents = '';
					btn.style.opacity = '1';
					frappe.show_alert({ message: 'Erreur au démarrage du chrono', indicator: 'red' }, 5);
				});
		}));

		// Bouton Google Maps
		if (address_display) {
			const maps_url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address_display)}`;
			const btn = vt_make_popup_btn(`📍 ${address_display}`, maps_url, 'blue');
			btn.target = '_blank';
			btn.rel = 'noopener noreferrer';
			section.appendChild(btn);
		}

		// Lien vers la Fiche de travail
		if (has_fdt) {
			const fdt_btn = vt_make_popup_btn(
				`🔧 Fiche : ${doc.custom_fiche_de_travail}`,
				frappe.utils.get_form_link('Fiche de travail', doc.custom_fiche_de_travail),
				'green'
			);
			// La section stoppe mousedown, donc le popover ne se ferme pas
			// tout seul via le "clic en dehors" : on le ferme explicitement.
			fdt_btn.addEventListener('click', () => vt_close_event_popup(popover_el));
			section.appendChild(fdt_btn);
		}

		// Lien vers la Visite Technique
		if (has_vt) {
			const vt_btn = vt_make_popup_btn(
				`🔍 Visite : ${doc.custom_visite_technique}`,
				frappe.utils.get_form_link('Visite Technique', doc.custom_visite_technique),
				'orange'
			);
			vt_btn.addEventListener('click', () => vt_close_event_popup(popover_el));
			section.appendChild(vt_btn);
		}

		// Description issue de la FDT ou VT (texte brut pour éviter XSS)
		if (linked_description) {
			const stripped = linked_description.replace(/<[^>]+>/g, '').trim();
			if (stripped) {
				const desc_div = document.createElement('div');
				desc_div.style.cssText = [
					'padding: 8px 10px',
					'background: var(--fg-color)',
					'border-radius: var(--border-radius)',
					'font-size: var(--text-sm)',
					'color: var(--text-color)',
					'border: 1px solid var(--border-color)',
					'max-height: 120px',
					'overflow-y: auto',
				].join(';');
				desc_div.textContent = stripped;
				section.appendChild(desc_div);
			}
		}

		body.appendChild(section);
	} catch (_) {
		// Silencieux
	}
}

// Ferme proprement le popover calendrier.
// On clique le backdrop plutôt que de faire popover_el.remove() : son handler
// natif (EventPopupManager.hideEventPopup) retire À LA FOIS le popover ET le
// backdrop plein écran (.evp-backdrop, position:fixed inset:0) et réinitialise
// l'état interne. Sans ça, le backdrop reste et bloque le scroll de la page.
function vt_close_event_popup(popover_el) {
	const backdrop = document.querySelector('.evp-backdrop');
	if (backdrop) {
		backdrop.click();
	} else {
		popover_el?.remove();
	}
}

function vt_make_popup_action_btn(html, color, onclick) {
	const b = document.createElement('button');
	b.type = 'button';
	b.innerHTML = html;
	b.style.cssText = `
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		padding: 7px 10px;
		border-radius: var(--border-radius);
		font-size: var(--text-sm);
		font-weight: 600;
		cursor: pointer;
		background: var(--${color}-100, #dcfce7);
		color: var(--${color}-700, #15803d);
		border: 1px solid var(--${color}-300, #86efac);
		transition: opacity 0.15s;
	`;
	b.addEventListener('mouseenter', () => b.style.opacity = '0.8');
	b.addEventListener('mouseleave', () => b.style.opacity = '1');
	b.addEventListener('click', (e) => {
		e.preventDefault();
		e.stopPropagation();
		onclick(b);
	});
	return b;
}

function vt_make_popup_btn(html, href, color) {
	const a = document.createElement('a');
	a.innerHTML = html;
	a.href = href;
	a.style.cssText = `
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 5px 10px;
		border-radius: var(--border-radius);
		font-size: var(--text-sm);
		font-weight: 500;
		text-decoration: none;
		background: var(--${color}-100, #eff6ff);
		color: var(--${color}-600, #2563eb);
		border: 1px solid var(--${color}-200, #bfdbfe);
		transition: opacity 0.15s;
	`;
	a.addEventListener('mouseenter', () => a.style.opacity = '0.8');
	a.addEventListener('mouseleave', () => a.style.opacity = '1');
	return a;
}
