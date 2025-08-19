// vt_internal/public/js/logrocket.js
(function () {
  // --- Détection "dev" front : hôtes/ports locaux et dev mode Frappe
  const host = location.hostname || "";
  const isLocalHost =
    host === "localhost" ||
    host === "127.0.0.1" ||
    host.endsWith(".local") ||
    host.endsWith(".locale"); // ex: vt.locale
  const isDevPort = !!location.port && !["80", "443"].includes(location.port);

  // Certains setups exposent le dev mode côté client via frappe.boot
  const isFrappeDev =
    !!(window.frappe &&
       frappe.boot &&
       (frappe.boot.developer_mode || frappe.boot.is_developer));

  if (isLocalHost || isDevPort || isFrappeDev) {
    // On n’active pas LogRocket en local/dev
    return;
  }

  // --- Chargement du SDK LogRocket (async)
  var script = document.createElement("script");
  script.src = "https://cdn.logrocket.io/LogRocket.min.js";
  script.async = true;
  script.onload = function () {
    if (!window.LogRocket) return;

    // Remplace par ton ID LogRocket: "org/projet"
    const APP_ID = 'erp-next/erp-next';

    // Init avec quelques précautions réseau (éviter login, mots de passe, etc.)
    LogRocket.init(APP_ID, {
      network: {
        requestSanitizer: (req) => {
          // ne pas logger le login ou les endpoints sensibles
          if (req.url.includes("/api/method/login")) return null;
          return req;
        },
        responseSanitizer: (res) => {
          // idem pour certaines réponses
          if (res.url.includes("/api/method/login")) return null;
          return res;
        },
      },
      // Exemple: tagger la release (si utile)
      // release:
      //   (window.frappe &&
      //     frappe.boot &&
      //     `${frappe.boot.versions?.frappe || "frappe"}/${frappe.boot.versions?.erpnext || "erpnext"}`) ||
      //   undefined,
    });

    // Identification utilisateur ERPNext (si dispo)
    try {
      const userId = frappe?.session?.user;                   // souvent l’email
      if (userId) {
        LogRocket.identify(userId, {
          email: userId, // dans ERPNext l'user est souvent l’email
        });
      }
    } catch (e) {
      // silencieux
    }
  };
  document.head.appendChild(script);
})();
