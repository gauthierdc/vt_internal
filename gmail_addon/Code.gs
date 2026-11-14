/**
 * Add-on Gmail : fiche client / fournisseur ERPNext dans le panneau latéral.
 *
 * Propriétés du script (jamais dans le code) :
 *   ERP_API_KEY     clé API de l'utilisateur lecture seule
 *   ERP_API_SECRET  secret API (affiché une seule fois à la génération)
 *   ERP_BASE_URL    optionnel, défaut https://bureau.verretransparence.fr
 *
 * L'URL appelée est GET /api/method/vt_internal.vt_internal.api.gmail.lookup_by_email
 */

var DEFAULT_BASE_URL = 'https://bureau.verretransparence.fr';
var LOOKUP_METHOD = 'vt_internal.vt_internal.api.gmail.lookup_by_email';
var WIDGET_BUDGET = 80;

var STATUS_FR = {
  Draft: 'Brouillon',
  Open: 'Ouvert',
  Replied: 'Répondu',
  Ordered: 'Commandé',
  Lost: 'Perdu',
  Cancelled: 'Annulé',
  Expired: 'Expiré',
  Submitted: 'Validé',
  Stopped: 'Arrêté',
  'To Deliver and Bill': 'À livrer et facturer',
  'To Bill': 'À facturer',
  'To Deliver': 'À livrer',
  Completed: 'Terminé',
  Closed: 'Clôturé',
  'On Hold': 'En attente',
  Overdue: 'En retard',
  Paid: 'Payée',
  'Partly Paid': 'Partiellement payée',
  Unpaid: 'Impayée',
  Return: 'Avoir',
  'Credit Note Issued': 'Avoir émis',
  'To Receive and Bill': 'À réceptionner et facturer',
  'To Receive': 'À réceptionner',
  Delivered: 'Livré',
  Opportunity: 'Opportunité',
  Quotation: 'Devis',
  Converted: 'Converti',
  Interested: 'Intéressé'
};

function onHomepage() {
  var card = CardService.newCardBuilder();
  card.setHeader(
    CardService.newCardHeader().setTitle('Verre Transparence').setSubtitle('Fiche ERP')
  );
  card.addSection(
    CardService.newCardSection().addWidget(
      CardService.newTextParagraph().setText(
        "Ouvrez un e-mail pour afficher la fiche client ou fournisseur correspondant à l'expéditeur."
      )
    )
  );
  return card.build();
}

function onGmailMessage(event) {
  var sender = senderFromEvent_(event);
  if (sender.error) {
    return errorCard_(
      'Expéditeur illisible',
      "Impossible de lire l'adresse de l'expéditeur (" + sender.error + ').'
    );
  }
  if (!sender.email) {
    return errorCard_('Expéditeur introuvable', "Cet e-mail n'a pas d'adresse d'expéditeur exploitable.");
  }

  var config = erpConfig_();
  if (!config.key || !config.secret) {
    return errorCard_(
      'Add-on non configuré',
      'Renseignez ERP_API_KEY et ERP_API_SECRET dans les propriétés du script (Paramètres du projet, Propriétés du script).'
    );
  }

  var result = lookup_(config, sender.email);
  if (result.error) {
    return errorCard_('ERPNext indisponible', result.error);
  }
  return renderCard_(config.base, sender.email, result.data);
}

function senderFromEvent_(event) {
  try {
    if (!event || !event.gmail || !event.gmail.messageId) {
      return { email: '' };
    }
    if (event.gmail.accessToken) {
      GmailApp.setCurrentMessageAccessToken(event.gmail.accessToken);
    }
    var message = GmailApp.getMessageById(event.gmail.messageId);
    if (!message) {
      return { email: '' };
    }
    return { email: extractEmail_(message.getFrom()) };
  } catch (err) {
    return { error: err && err.message ? err.message : 'erreur Gmail' };
  }
}

function extractEmail_(from) {
  if (!from) {
    return '';
  }
  var text = String(from);
  var match = text.match(/<([^>]+)>/);
  return (match ? match[1] : text).trim().toLowerCase();
}

function erpConfig_() {
  var props = PropertiesService.getScriptProperties();
  var base = props.getProperty('ERP_BASE_URL') || DEFAULT_BASE_URL;
  return {
    base: String(base).replace(/\/+$/, ''),
    key: props.getProperty('ERP_API_KEY') || '',
    secret: props.getProperty('ERP_API_SECRET') || ''
  };
}

function lookup_(config, email) {
  var url =
    config.base +
    '/api/method/' +
    LOOKUP_METHOD +
    '?email=' +
    encodeURIComponent(email);
  var response;
  try {
    response = UrlFetchApp.fetch(url, {
      method: 'get',
      muteHttpExceptions: true,
      headers: {
        Authorization: 'token ' + config.key + ':' + config.secret,
        Accept: 'application/json'
      }
    });
  } catch (err) {
    return { error: 'Impossible de joindre ERPNext (' + (err.message || 'réseau') + ').' };
  }

  var code = response.getResponseCode();
  if (code === 401 || code === 403) {
    return {
      error:
        'Accès refusé (' +
        code +
        '). Vérifiez la clé API et les droits de lecture de l\'utilisateur.'
    };
  }
  if (code < 200 || code >= 300) {
    return { error: 'ERPNext a répondu ' + code + '.' };
  }

  var parsed;
  try {
    parsed = JSON.parse(response.getContentText() || '');
  } catch (err) {
    return { error: 'Réponse ERPNext illisible.' };
  }
  var data = parsed && parsed.message !== undefined ? parsed.message : parsed;
  if (!data || !Array.isArray(data.customers) || !Array.isArray(data.suppliers)) {
    return { error: 'Réponse ERPNext inattendue.' };
  }
  return { data: data };
}

function renderCard_(base, email, data) {
  var card = CardService.newCardBuilder();
  card.setHeader(CardService.newCardHeader().setTitle('Verre Transparence').setSubtitle(email));
  var budget = { used: 0, overflow: false };

  var customers = data.customers || [];
  var suppliers = data.suppliers || [];
  var leads = data.leads || [];
  var unlinked = data.unlinked_contacts || [];
  var sawContact =
    unlinked.length > 0 ||
    customers.concat(suppliers).some(function (party) {
      return (party.contacts || []).length > 0;
    });
  var nothing = !customers.length && !suppliers.length && !leads.length && !unlinked.length;

  if (nothing) {
    pushSection_(card, budget, null, emptyWidgets_(base, data, email));
    return card.build();
  }

  if (data.match_type === 'domain') {
    pushSection_(card, budget, null, [
      CardService.newTextParagraph().setText(
        'Pas de fiche pour cette adresse exacte. Correspondances du domaine ' +
          (data.domain || '') +
          '.'
      )
    ]);
  }

  customers.forEach(function (customer) {
    addParty_(card, budget, base, 'Client', customer.customer_name || customer.name, customer, customerWidgets_);
    addDocs_(card, budget, base, 'Devis', customer.quotations);
    addDocs_(card, budget, base, 'Commandes', customer.sales_orders);
    addDocs_(card, budget, base, 'Factures', customer.sales_invoices);
  });

  suppliers.forEach(function (supplier) {
    addParty_(
      card,
      budget,
      base,
      'Fournisseur',
      supplier.supplier_name || supplier.name,
      supplier,
      supplierAggregate_
    );
    addDocs_(card, budget, base, 'Devis fournisseur', supplier.supplier_quotations);
    addDocs_(card, budget, base, 'Commandes fournisseur', supplier.purchase_orders);
    addDocs_(card, budget, base, 'Factures fournisseur', supplier.purchase_invoices);
  });

  leads.forEach(function (lead) {
    var lines = [lead.company_name, statusLabel_({ status: lead.status, docstatus: 1 })]
      .filter(Boolean)
      .join(' · ');
    var widgets = [
      linkedText_(base, lead.lead_name || lead.name, lead.url, lead.name)
    ];
    if (lines) {
      widgets.push(CardService.newDecoratedText().setText(lines).setWrapText(true));
    }
    pushSection_(card, budget, 'Piste', widgets);
  });

  if (unlinked.length) {
    pushSection_(
      card,
      budget,
      'Contact',
      unlinked.map(function (contact) {
        var text = contact.full_name || contact.name;
        if (contact.email) {
          text += ' · ' + contact.email;
        }
        return linkedText_(base, text, contact.url, 'Sans client ni fournisseur');
      })
    );
  }

  if (!customers.length && !suppliers.length) {
    pushSection_(card, budget, 'Créer dans ERPNext', createWidgets_(base, data, email, !sawContact));
  }

  if (budget.overflow || data.truncated) {
    card.addSection(
      CardService.newCardSection().addWidget(
        CardService.newTextParagraph().setText('Affichage limité. Ouvrez la fiche ERPNext pour le détail.')
      )
    );
  }
  return card.build();
}

function addParty_(card, budget, base, header, title, party, aggregateText) {
  var widgets = [linkedText_(base, title, party.url, partyLabel_(party))];
  var meta = [party.customer_group || party.supplier_group, party.territory].filter(Boolean);
  if (meta.length) {
    widgets.push(CardService.newDecoratedText().setTopLabel('Classement').setText(meta.join(' · ')).setWrapText(true));
  }
  var phones = [party.phone, party.mobile].filter(Boolean).join(' · ');
  if (phones) {
    widgets.push(CardService.newDecoratedText().setTopLabel('Téléphone').setText(phones));
  }
  (party.contacts || []).forEach(function (contact) {
    var text = contact.full_name || contact.name;
    if (contact.email) {
      text += ' · ' + contact.email;
    }
    widgets.push(linkedText_(base, text, contact.url, 'Contact'));
  });
  if (party.aggregates) {
    widgets.push(CardService.newTextParagraph().setText(aggregateText(party.aggregates)));
  }
  pushSection_(card, budget, header, widgets);
}

function addDocs_(card, budget, base, header, docs) {
  docs = docs || [];
  if (!docs.length) {
    pushSection_(card, budget, header, [
      CardService.newTextParagraph().setText('Aucun document récent.')
    ]);
    return;
  }
  pushSection_(
    card,
    budget,
    header,
    docs.map(function (doc) {
      var bottom = [formatDate_(doc.date), statusLabel_(doc), doc.company].filter(Boolean).join(' · ');
      if (doc.bill_no) {
        bottom += ' · réf. ' + doc.bill_no;
      }
      return linkedText_(base, (doc.name || '') + ' · ' + formatMoney_(doc.grand_total), doc.url, bottom);
    })
  );
}

function emptyWidgets_(base, data, email) {
  var text = 'Aucun client, fournisseur ou piste pour ' + email + '.';
  if (data.generic_domain && data.domain) {
    text +=
      ' Le domaine ' +
      data.domain +
      " est un webmail ou un fournisseur d'accès : les autres adresses de ce domaine ne sont pas proposées.";
  }
  return [CardService.newTextParagraph().setText(text)].concat(createWidgets_(base, data, email, true));
}

function createWidgets_(base, data, email, includeContact) {
  var create = (data && data.create) || {};
  var quoted = encodeURIComponent(email);
  var fallback = {
    contact: base + '/app/contact/new?email_id=' + quoted,
    customer: base + '/app/customer/new',
    supplier: base + '/app/supplier/new?email_id=' + quoted
  };
  var buttons = CardService.newButtonSet();
  var count = 0;
  function add(label, preferred, local) {
    var safe = safeUrl_(base, preferred) || safeUrl_(base, local);
    if (!safe) {
      return;
    }
    buttons.addButton(CardService.newTextButton().setText(label).setOpenLink(openLink_(safe)));
    count++;
  }
  if (includeContact) {
    add('Créer le contact', create.contact, fallback.contact);
  }
  add('Créer le client', create.customer, fallback.customer);
  add('Créer le fournisseur', create.supplier, fallback.supplier);
  return count ? [buttons] : [];
}

function customerWidgets_(aggregates) {
  return (
    'Impayé : ' +
    formatMoney_(aggregates.outstanding_amount) +
    ' (' +
    (aggregates.unpaid_invoice_count || 0) +
    ' facture' +
    (aggregates.unpaid_invoice_count > 1 ? 's' : '') +
    '). Commandes ouvertes : ' +
    (aggregates.open_order_count || 0) +
    ' (' +
    formatMoney_(aggregates.open_order_total) +
    ').'
  );
}

function supplierAggregate_(aggregates) {
  return (
    'À réceptionner : ' +
    formatMoney_(aggregates.amount_to_receive) +
    '. Commandes ouvertes : ' +
    (aggregates.open_purchase_order_count || 0) +
    ' (' +
    formatMoney_(aggregates.open_purchase_order_total) +
    '). Factures impayées : ' +
    formatMoney_(aggregates.outstanding_amount) +
    ' (' +
    (aggregates.unpaid_invoice_count || 0) +
    ').'
  );
}

function partyLabel_(party) {
  var bits = [];
  if (party.disabled) {
    bits.push('Désactivé');
  }
  if (party.name) {
    bits.push(party.name);
  }
  return bits.join(' · ');
}

function linkedText_(base, text, url, topLabel) {
  var widget = CardService.newDecoratedText().setText(text || '—').setWrapText(true);
  if (topLabel) {
    widget.setTopLabel(topLabel);
  }
  var safe = safeUrl_(base, url);
  if (safe) {
    widget.setOpenLink(openLink_(safe));
  }
  return widget;
}

function pushSection_(card, budget, header, widgets) {
  if (!widgets || !widgets.length) {
    return true;
  }
  if (budget.used + widgets.length > WIDGET_BUDGET) {
    budget.overflow = true;
    return false;
  }
  budget.used += widgets.length;
  var section = CardService.newCardSection();
  if (header) {
    section.setHeader(header);
  }
  widgets.forEach(function (widget) {
    section.addWidget(widget);
  });
  card.addSection(section);
  return true;
}

function openLink_(url) {
  return CardService.newOpenLink()
    .setUrl(url)
    .setOpenAs(CardService.OpenAs.FULL_SIZE)
    .setOnClose(CardService.OnClose.NOTHING);
}

function safeUrl_(base, url) {
  if (!url || typeof url !== 'string') {
    return '';
  }
  var prefix = String(base || DEFAULT_BASE_URL).replace(/\/+$/, '');
  if (url.indexOf(prefix + '/') !== 0) {
    return '';
  }
  return url;
}

function formatMoney_(amount) {
  if (amount === null || amount === undefined || amount === '') {
    return '—';
  }
  var value = Number(amount);
  if (isNaN(value)) {
    return '—';
  }
  var negative = value < 0;
  var fixed = Math.abs(value).toFixed(2).replace('.', ',');
  var parts = fixed.split(',');
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '\u00a0');
  return (negative ? '-' : '') + parts[0] + ',' + parts[1] + ' €';
}

function formatDate_(iso) {
  if (!iso) {
    return '';
  }
  var match = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) {
    return String(iso);
  }
  return match[3] + '/' + match[2] + '/' + match[1];
}

function statusLabel_(doc) {
  if (!doc) {
    return '';
  }
  if (doc.docstatus === 0) {
    return 'Brouillon';
  }
  return STATUS_FR[doc.status] || doc.status || '';
}

function errorCard_(title, message) {
  var card = CardService.newCardBuilder();
  card.setHeader(CardService.newCardHeader().setTitle('Verre Transparence').setSubtitle(title));
  card.addSection(
    CardService.newCardSection().addWidget(CardService.newTextParagraph().setText(message))
  );
  return card.build();
}
