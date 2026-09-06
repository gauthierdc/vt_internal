// Garde-fou scroll mobile Desk : Frappe pose `html { overflow-y: hidden }`
// quand un overlay sidebar s’ouvre, et ne le retire pas toujours (navigation,
// reload, overlay déjà fermé). On restaure le scroll document uniquement
// s’il n’y a plus d’overlay / modal ouvert.

export const DESK_MOBILE_MAX_PX = 768;

export const DESK_OVERLAY_OPEN_SELECTORS = [
	".overlay-sidebar.opened",
	".close-sidebar",
	".modal.show",
	".modal.in",
];

export function isMobileDeskViewport(width) {
	const w = Number(width);
	if (!Number.isFinite(w)) return false;
	return w < DESK_MOBILE_MAX_PX;
}

function firstMatch(root, selector) {
	if (!root) return null;
	if (typeof root.querySelector === "function") {
		try {
			const found = root.querySelector(selector);
			if (found) return found;
		} catch (_e) {
			/* sélecteur invalide */
		}
	}
	if (typeof root.querySelectorAll === "function") {
		try {
			const list = root.querySelectorAll(selector);
			if (list && list.length) return list[0];
		} catch (_e) {
			/* sélecteur invalide */
		}
	}
	return null;
}

function isDisplayed(el) {
	if (!el) return false;
	if (el.hidden) return false;
	const style = el.style || {};
	if (style.display === "none" || style.visibility === "hidden") return false;
	return true;
}

export function isDeskOverlayOpen(root) {
	if (!root) return false;
	const body = root.body;
	if (body && body.classList && typeof body.classList.contains === "function") {
		if (body.classList.contains("modal-open")) return true;
	}
	for (const sel of DESK_OVERLAY_OPEN_SELECTORS) {
		if (firstMatch(root, sel)) return true;
	}
	const workspaceOverlay = firstMatch(root, ".body-sidebar-overlay");
	if (workspaceOverlay && isDisplayed(workspaceOverlay)) return true;
	return false;
}

export function isDocumentOverflowLocked(root) {
	if (!root) return false;
	const nodes = [root.documentElement, root.body];
	return nodes.some((el) => {
		if (!el || !el.style) return false;
		return el.style.overflowY === "hidden" || el.style.overflow === "hidden";
	});
}

/**
 * Pure decision: unlock html/body only on mobile (or force), and only when
 * the list/workspace overlay or a modal is not actually open — unless force
 * (caller just closed the overlay).
 */
export function shouldRestoreDeskPageScroll({
	mobile = true,
	overlayOpen = false,
	overflowLocked = false,
	force = false,
} = {}) {
	if (!overflowLocked) return false;
	if (force) return true;
	if (!mobile) return false;
	if (overlayOpen) return false;
	return true;
}

export function restoreDeskPageScroll(root, { force = false, width } = {}) {
	if (!root) return { restored: false, overlayOpen: false };
	const overlayOpen = isDeskOverlayOpen(root);
	const overflowLocked = isDocumentOverflowLocked(root);
	const mobile = width == null ? true : isMobileDeskViewport(width);
	if (!shouldRestoreDeskPageScroll({ mobile, overlayOpen, overflowLocked, force })) {
		return { restored: false, overlayOpen };
	}
	const clear = (el) => {
		if (!el || !el.style) return;
		if (el.style.overflowY === "hidden") el.style.overflowY = "";
		if (el.style.overflow === "hidden") el.style.overflow = "";
	};
	clear(root.documentElement);
	clear(root.body);
	return { restored: true, overlayOpen };
}

export function installDeskMobileScrollGuard({
	doc,
	pageProto,
	router,
	getWidth,
} = {}) {
	if (!doc) return { installed: false, tick: () => ({ restored: false }) };

	const widthOf = () => (typeof getWidth === "function" ? getWidth() : undefined);

	const tick = (force = false) => restoreDeskPageScroll(doc, { force, width: widthOf() });

	if (pageProto && !pageProto.__vt_mobile_scroll) {
		const origClose = pageProto.close_sidebar;
		if (typeof origClose === "function") {
			pageProto.close_sidebar = function () {
				const result = origClose.apply(this, arguments);
				tick(true);
				return result;
			};
		}
		const origSetup = pageProto.setup_overlay_sidebar;
		if (typeof origSetup === "function") {
			pageProto.setup_overlay_sidebar = function () {
				const result = origSetup.apply(this, arguments);
				const inner = this.close_sidebar;
				this.close_sidebar = function () {
					const out = typeof inner === "function" ? inner.apply(this, arguments) : undefined;
					tick(true);
					return out;
				};
				return result;
			};
		}
		pageProto.__vt_mobile_scroll = true;
	}

	if (router && typeof router.on === "function" && !router.__vt_mobile_scroll) {
		router.on("change", () => {
			setTimeout(() => tick(false), 50);
		});
		router.__vt_mobile_scroll = true;
	}

	tick(false);
	return { installed: true, tick };
}

export function attachDeskMobileScrollHelpers(target) {
	const root =
		target || (typeof frappe !== "undefined" ? (frappe.vt = frappe.vt || {}) : {});
	const dest = (root.desk_mobile_scroll = root.desk_mobile_scroll || {});
	dest.isMobileDeskViewport = isMobileDeskViewport;
	dest.isDeskOverlayOpen = isDeskOverlayOpen;
	dest.isDocumentOverflowLocked = isDocumentOverflowLocked;
	dest.shouldRestoreDeskPageScroll = shouldRestoreDeskPageScroll;
	dest.restoreDeskPageScroll = restoreDeskPageScroll;
	dest.installDeskMobileScrollGuard = installDeskMobileScrollGuard;
	return dest;
}
