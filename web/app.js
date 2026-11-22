const byId = id => document.getElementById(id);
const views = {
  start: ["Odkrywaj i zgłaszaj innowacje", "Szukasz rozwiązania dla swojej instytucji albo rozwijasz własny projekt? Zacznij tutaj."],
  discovery: ["Szukaj projektu", "Przeglądaj rozwiązania, sprawdzaj ich dowody i szukaj możliwości wdrożenia."],
  add: ["Dodaj projekt", "Cieszymy się, że chcesz podzielić się swoją pracą! Ten formularz jest dla projektów, które już działają: mają prototyp, wyniki testów albo pierwsze wdrożenie. Jeśli na razie masz pomysł, daj mu jeszcze chwilę i wróć, gdy zrobi pierwsze kroki. Chętnie go wtedy poznamy."],
};
const publicPreview = document.body.hasAttribute("data-public-preview");
function accessibleView(name) {
  return Object.hasOwn(views, name) && !(publicPreview && name === "add") ? name : "start";
}
let view = accessibleView(location.hash.slice(1));
let revision = 0;
let detailRevision = 0;
let detailTrigger;

function element(tag, value, parent) {
  const node = document.createElement(tag);
  node.textContent = value;
  parent?.append(node);
  return node;
}

async function api(path, body, signal) {
  const profile = byId("actor").value;
  const headers = {"Content-Type": "application/json"};
  if (profile) headers["X-Demo-Token"] = profile + "-demo";
  const response = await fetch("/api/" + path, {
    headers, signal,
    ...(body === undefined ? {} : {method: "POST", body: JSON.stringify(body)}),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Sprawdź dane formularza.");
  return data;
}

function actionButton(label, parent, handler) {
  const node = element("button", label, parent);
  node.type = "button";
  node.onclick = () => handler(node);
  return node;
}

function detailButton(item, parent) {
  const node = actionButton("Zobacz kartę", parent, trigger => showDetail(item, trigger));
  node.setAttribute("aria-label", "Zobacz kartę: " + item.title);
  node.className = "secondary";
}

function card(item, parent, featured = false) {
  const article = element("article", "", parent);
  article.className = featured ? "card featured-card" : "card";
  element("p", item.published === 0 ? "Niepubliczna" : "Opublikowana", article).className = "label";
  element("h3", item.title, article);
  element("p", item.summary, article);
  element("p", [item.stage, ...item.tags].join(" · "), article).className = "tags";
  element("p", item.assessment["wdrożenie"], article).className = "muted";
  detailButton(item, article);
  return article;
}

function addList(section, heading, values, fallback) {
  element("h3", heading, section);
  if (!values.length) {
    element("p", fallback, section);
    return;
  }
  const list = element("ul", "", section);
  values.forEach(value => element("li", value, list));
}

async function showDetail(item, trigger) {
  const current = ++detailRevision;
  const dialog = byId("detail");
  const content = byId("detail-content");
  const title = element("h2", item.title);
  title.id = "detail-title";
  content.replaceChildren(title);
  if (!dialog.open) {
    detailTrigger = trigger;
    dialog.showModal();
  }
  try {
    if (!("published" in item)) item = await api("innovations/" + encodeURIComponent(item.id));
    if (current !== detailRevision) return;
    element("p", [item.published === 0 ? "Niepubliczna" : "Opublikowana", "Etap: " + item.stage, item.source_status].join(" · "), content).className = "tags";
    element("h3", "Problem i rozwiązanie", content);
    element("p", item.summary, content);
    if (item.details) {
      element("h3", "Szczegóły niepubliczne", content);
      element("p", item.details, content);
    }
    if (item.source) {
      element("h3", "Źródło i status weryfikacji", content);
      const source = element("a", item.source, content);
      source.href = item.source;
      element("p", item.source_status, content);
      if (item.provenance === "bielik" && !item.demo) {
        element("p", "Bielik zasugerował opis, tagi i etap na podstawie publicznego materiału.", content);
      }
    }
    element("h3", "Podstawa oceny", content);
    const criteria = element("div", "", content);
    criteria.className = "criteria";
    item.assessment.criteria.forEach(criterion => {
      const entry = element("section", "", criteria);
      element("h4", criterion.label, entry);
      element("strong", criterion.result, entry);
      element("p", criterion.reason, entry);
      element("p", "Podstawa: " + criterion.evidence, entry);
    });
    const next = element("section", "", content);
    next.className = "next-step";
    element("h3", "Następny krok", next);
    element("p", item.assessment["następny krok"], next);
    element("p", "Adresat: " + item.assessment.recipient, next);
    if (item.assessment.metric) element("p", "Miernik pilotażu: " + item.assessment.metric, next);
    addList(content, "Twórcy i wdrażający", item.links.map(link =>
      [link.name, link.role, link.confirmed ? "potwierdzono rolę" : "oczekuje na potwierdzenie"].join(" · ")
    ), "Brak powiązanych profili.");
    element("p", "ID karty: " + item.id, content).className = "muted identifier";
    if (item.similar) {
      element("h3", "Podobne rozwiązania", content);
      if (!item.similar.length) element("p", "Brak dopasowań w opublikowanym katalogu.", content);
      item.similar.forEach(other => {
        const row = element("div", "", content);
        actionButton(other.title, row, () => showDetail(other)).className = "text-button";
        element("p", other.reasons.join(" · "), row).className = "muted";
      });
    }
    dialog.scrollTop = 0;
  } catch (error) {
    if (current === detailRevision) element("p", error.message, content).setAttribute("role", "alert");
  }
}

byId("detail").addEventListener("close", () => {
  detailRevision++;
  detailTrigger?.focus();
});

async function act(action, node) {
  const started = revision;
  if (node) node.disabled = true;
  try {
    await action();
    if (started === revision) {
      const focused = document.activeElement === node || document.activeElement === document.body;
      await render("Zapisano.");
      if (focused && started + 1 === revision && node && !node.isConnected) byId("status").focus();
    }
  } catch (error) {
    if (started === revision) byId("status").textContent = error.message;
  } finally {
    if (node) node.disabled = false;
  }
}

function renderReview(items, needs, pilots, profile) {
  if (!items.length) element("p", "Brak kart przypisanych do profilu.", byId("queue"));
  items.forEach(item => {
    const article = card(item, byId("queue"));
    item.links.forEach(link => {
      element("p", link.name + " · " + link.role + " · " +
        (link.confirmed ? "potwierdzono" : "oczekuje"), article);
      if (!link.confirmed && link.profile === profile) {
        actionButton("Potwierdź rolę: " + link.role, article, node => act(
          () => api("innovations/" + item.id + "/links/" + encodeURIComponent(link.role), {}), node
        ));
      }
    });
    if (!item.published && item.owner === profile) {
      if (item.links.some(link => !link.confirmed)) {
        element("p", "Publikacja możliwa po potwierdzeniu przypisanych ról.", article);
      } else {
        actionButton("Opublikuj kartę", article, node =>
          act(() => api("innovations/" + item.id + "/publish", {}), node));
      }
    }
  });
  if (!needs.length) element("p", "Brak potrzeb w tym profilu.", byId("matches"));
  needs.forEach(need => {
    const article = element("article", "", byId("matches"));
    element("h3", need.title, article);
    if (need.description) element("p", need.description, article);
    if (!need.matches.length) element("p", "Brak dopasowań w opublikowanym katalogu.", article);
    need.matches.forEach(item => {
      const match = element("section", "", article);
      match.className = "match";
      element("h4", item.title, match);
      const list = element("ul", "", match);
      item.reasons.forEach(reason => element("li", reason, list));
      detailButton(item, match);
      const saved = pilots.find(record => record.need === need.id && record.innovation === item.id);
      if (saved) {
        element("p", "Zainteresowanie zapisane · " + saved.recipient_name, match);
      } else if (item.pilot_recipient) {
        element("p", "Odbiorca: " + item.pilot_recipient.name, match);
        actionButton("Zgłoś zainteresowanie pilotażem", match, node =>
          act(() => api("needs/" + need.id + "/pilots/" + item.id, {}), node));
      } else {
        element("p", "Oczekuje na potwierdzonego partnera pilotażu.", match);
      }
    });
  });
  if (!pilots.length) element("p", "Brak zgłoszeń pilotażu.", byId("pilots"));
  pilots.forEach(pilot => {
    const article = element("article", "", byId("pilots"));
    element("p", pilot.recipient === profile ? "Otrzymane zgłoszenie" : "Wysłane zgłoszenie", article).className = "label";
    element("h3", pilot.innovation_title, article);
    element("p", pilot.need_title, article);
    element("p", pilot.requester_name + " → " + pilot.recipient_name, article);
  });
}

let catalogFilters;
let catalogQuery = new URLSearchParams();
let catalogPage = 1;

function checkbox(group, name, value, text = value) {
  const label = element("label", "", group);
  label.className = "check";
  const control = document.createElement("input");
  control.type = "checkbox";
  control.name = name;
  control.value = value;
  label.append(control, document.createTextNode(text));
  return control;
}

function filterGroup(container, title, expanded = false) {
  const group = element("details", "", container);
  group.className = "filter-group";
  group.open = expanded;
  element("summary", title, group);
  const content = element("div", "", group);
  content.className = "facet-options";
  return content;
}

function buildFilters(options) {
  const container = byId("filter-options");
  container.replaceChildren();
  const categories = filterGroup(container, "Kategorie", true);
  Object.entries(options.categories).forEach(([name, children]) => {
    const branch = element("details", "", categories);
    branch.className = "category-branch";
    const summary = element("summary", "", branch);
    const parent = checkbox(summary, "category", name);
    const childGroup = element("div", "", branch);
    childGroup.className = "facet-options subcategories";
    const inputs = children.map(child => checkbox(childGroup, "subcategory", child));
    const refreshParent = () => {
      const active = inputs.some(input => input.checked);
      parent.indeterminate = active && !inputs.every(input => input.checked);
      if (active) parent.checked = true;
    };
    parent.addEventListener("change", () => {
      if (parent.checked) branch.open = true;
      else inputs.forEach(input => { input.checked = false; });
      parent.indeterminate = false;
    });
    inputs.forEach(input => input.addEventListener("change", refreshParent));
  });
  const technology = filterGroup(container, "Technologia");
  options.technologies.forEach(value => checkbox(technology, "technology", value));
  const place = filterGroup(container, "Miejsce zastosowania");
  options.places.forEach(value => checkbox(place, "place", value));
  const trl = filterGroup(container, "TRL");
  if (!options.trl_available) element("p", "Baza czeka na uzupełnienie poziomów TRL.", trl).className = "muted";
  Array.from({length: 9}, (_, i) => i + 1).forEach(value => checkbox(trl, "trl", value, "TRL " + value));
  checkbox(trl, "trl", "unknown", "Brak danych");
  const deployment = filterGroup(container, "Wdrożenie");
  Object.entries(deploymentLabels).forEach(([value, label]) => checkbox(deployment, "deployment", value, label));
}

const deploymentLabels = {
  yes: "Wdrożenie udokumentowane w źródle",
  in_progress: "Pilotaż lub wdrażanie opisane w źródle",
  potential: "Potencjał wdrożenia",
  no: "Potwierdzony brak wdrożenia",
  unknown: "Brak danych o wdrożeniu",
};

function sourceLink(content, label, url) {
  if (!url) return;
  try {
    const target = new URL(url);
    if (!["https:", "http:"].includes(target.protocol)) return;
    const paragraph = element("p", "", content);
    const link = element("a", label, paragraph);
    link.href = target.href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  } catch {
    // The source URL can be absent or invalid in legacy records.
  }
}

function describeProject(content, project, preview = false) {
  if (project.summary) {
    const description = element("p", project.summary, content);
    description.className = preview ? "catalog-excerpt" : "catalog-description";
  }
  if (project.business_details && (!preview || !project.summary)) {
    const details = element("p", project.business_details, content);
    details.className = preview ? "catalog-excerpt" : "catalog-business";
  }
  if (!project.summary && !project.business_details) {
    element("p", "Sprawdź informacje na stronie projektu.", content).className = "muted";
  }
  sourceLink(content, project.page_specific ? "Otwórz stronę projektu" : "Otwórz wykaz projektów",
    project.page_url);
}

function maturityLabel(project) {
  if (!project.trl_min) return "TRL nieustalony";
  const range = project.trl_min === project.trl_max
    ? project.trl_min : project.trl_min + "–" + project.trl_max;
  const basis = {
    declared: "deklaracja źródła",
    estimate: "szacunek z opisu",
    profile: "orientacyjny zakres z profilu projektu",
  };
  return "TRL " + range + " · " + (basis[project.trl_basis] || "szacunek");
}

function showRelated(content, record) {
  ++detailRevision;
  const title = element("h2", "Podobne projekty");
  title.id = "detail-title";
  content.replaceChildren(title);
  const back = actionButton("Wróć do projektu", content, button => showCatalogDetail(record, button));
  back.className = "secondary";
  back.focus();
  element("p", record.title, content).className = "muted";
  if (!record.related.length) {
    element("p", "Brak podobnych pozycji w tej grupie.", content);
    return;
  }
  const list = element("ul", "", content);
  record.related.forEach(other => {
    const row = element("li", "", list);
    if (other.id) {
      actionButton(other.title, row, button => showCatalogDetail(other, button)).className = "text-button";
    } else {
      sourceLink(row, other.title + " · " + other.kind, other.url);
    }
  });
  byId("detail").scrollTop = 0;
}

async function showCatalogDetail(item, trigger) {
  const current = ++detailRevision;
  const dialog = byId("detail");
  const content = byId("detail-content");
  const title = element("h2", item.title);
  title.id = "detail-title";
  content.replaceChildren(title);
  if (!dialog.open) {
    detailTrigger = trigger;
    dialog.showModal();
  }
  try {
    const record = await api("catalog/" + item.id);
    if (current !== detailRevision) return;
    const similar = actionButton("Pokaż podobne (" + record.related.length + ")", content,
      () => showRelated(content, record));
    similar.className = "catalog-related-button";
    describeProject(content, record);
    element("h3", "Klasyfikacja", content);
    element("p", [record.category, ...record.facets.subcategory].filter(Boolean).join(" · ") || "Kategoria nieustalona", content);
    if (record.classification_status === "do sprawdzenia") {
      element("p", "Przypisanie kategorii na podstawie reguł.", content).className = "muted";
    }
    if (record.facets.technology.length) addList(content, "Technologie", record.facets.technology, "");
    if (record.facets.place.length) addList(content, "Miejsca zastosowania", record.facets.place, "");
    if (record.places_evidence.length) {
      addList(content, "Miejsca testowania ze źródła", record.places_evidence.map(place => place.fragment), "");
    }
    element("h3", "Gotowość i wdrożenie", content);
    element("p", maturityLabel(record), content);
    if (record.trl_basis !== "profile" && record.trl_evidence) element("blockquote", record.trl_evidence, content);
    element("p", deploymentLabels[record.deployment || "unknown"], content);
    if (record.deployment_note) element("p", record.deployment_note, content);
    if (record.review_sources?.length) {
      element("h3", "Materiały o testach i wdrożeniu", content);
      record.review_sources.forEach(source => sourceLink(content, source.label, source.url));
    }
    if (record.organizations.length) {
      addList(content, "Organizacje wskazane w źródle",
        record.organizations.map(org => [org.nazwa, org.rola].filter(Boolean).join(" · ")), "");
    }
    dialog.scrollTop = 0;
  } catch (error) {
    if (current === detailRevision) element("p", error.message, content).setAttribute("role", "alert");
  }
}

const filterLabels = {
  category: "Kategorie", technology: "Technologia", place: "Miejsce zastosowania",
  trl: "TRL", deployment: "Wdrożenie",
};

function updateFilterAvailability(available) {
  byId("filter-options").querySelectorAll("input").forEach(input => {
    input.disabled = !input.checked && !available[input.name].includes(input.value);
    input.parentElement.title = input.disabled ? "Brak projektów pasujących do tego połączenia" : "";
  });
}

function projectCard(result, item) {
  const card = element("article", "", result);
  card.className = "card catalog-card";
  element("p", item.category || item.source, card).className = "label";
  element("h3", item.title, card);
  element("p", maturityLabel(item), card).className = "muted";
  describeProject(card, item, true);
  const button = actionButton("Zobacz projekt", card, trigger => showCatalogDetail(item, trigger));
  button.className = "secondary";
  button.setAttribute("aria-label", "Zobacz projekt: " + item.title);
}

async function renderAlternatives(result, query, current, signal) {
  const groups = Object.keys(filterLabels).map(name => {
    const names = name === "category" ? [name, "subcategory"] : [name];
    const params = new URLSearchParams({page_size: 3});
    names.forEach(key => query.getAll(key).forEach(value => params.append(key, value)));
    return [name, params];
  }).filter(([, params]) => [...params.keys()].length > 1);
  if (groups.length < 2) return;
  const suggestions = await Promise.all(groups.map(async ([name, params]) =>
    [name, await api("catalog?" + params, undefined, signal)]));
  if (current !== revision) return;
  const matching = suggestions.filter(([, data]) => data.total);
  if (!matching.length) return;
  element("p", "Poniżej propozycje dla poszczególnych filtrów.", result);
  for (const [name, data] of matching) {
    const section = element("section", "", result);
    section.className = "catalog-alternatives";
    element("h3", filterLabels[name] + " (" + data.total.toLocaleString("pl-PL") + ")", section);
    const list = element("div", "", section);
    list.className = "grid";
    data.items.forEach(item => projectCard(list, item));
  }
}

async function renderCatalog(current, signal) {
  if (!catalogFilters) catalogFilters = await api("catalog/filters", undefined, signal);
  if (current !== revision) return;
  if (!byId("filter-options").children.length) buildFilters(catalogFilters);
  const query = new URLSearchParams(catalogQuery);
  query.set("page", catalogPage);
  query.set("availability", "true");
  const result = byId("catalog");
  result.replaceChildren();
  byId("catalog-count").textContent = "";
  byId("catalog-pagination").hidden = true;
  const data = await api("catalog?" + query, undefined, signal);
  if (current !== revision) return;
  byId("catalog-count").textContent = "Wyniki: " + data.total.toLocaleString("pl-PL");
  updateFilterAvailability(data.available);
  if (!data.items.length) element("p", "Nie udało się znaleźć projektów spełniających wszystkie wybrane filtry naraz.", result);
  data.items.forEach(item => projectCard(result, item));
  const pages = Math.ceil(data.total / data.page_size);
  byId("catalog-pagination").hidden = pages <= 1;
  byId("catalog-prev").disabled = data.page <= 1;
  byId("catalog-next").disabled = data.page >= pages;
  byId("catalog-page").textContent = "Strona " + data.page + " z " + pages;
  if (!data.total) await renderAlternatives(result, query, current, signal);
}

async function render(message = "") {
  const current = ++revision;
  const [heading, intro] = views[view];
  byId("heading").textContent = heading;
  byId("intro").textContent = intro;
  byId("status").textContent = message || "Wczytywanie…";
  byId("search-loader").hidden = view !== "discovery";
  Object.keys(views).forEach(name => { byId(name).hidden = name !== view; });
  document.querySelectorAll("[data-view]").forEach(node => {
    if (node.dataset.view === view) node.setAttribute("aria-current", "page");
    else node.removeAttribute("aria-current");
  });
  try {
    if (view === "discovery") {
      await renderCatalog(current, AbortSignal.timeout(9800));
      if (current !== revision) return;
    } else if (view === "review") {
      const profile = byId("actor").value;
      byId("workspace").hidden = !profile;
      byId("choose-profile").hidden = Boolean(profile);
      byId("need-form").hidden = !["gmina", "miasto", "szkola"].includes(profile);
      ["queue", "matches", "pilots"].forEach(id => byId(id).replaceChildren());
      if (profile) {
        const data = await Promise.all([api("review"), api("needs"), api("pilots")]);
        if (current !== revision) return;
        renderReview(...data, profile);
      }
    }
    byId("status").textContent = message;
  } catch (error) {
    if (current === revision) {
      byId("status").textContent = error.name === "TimeoutError"
        ? "Serwer nie odpowiedział w ciągu 10 sekund. Spróbuj ponownie lub zawęź wyszukiwanie filtrem."
        : error.message || "Nie udało się pobrać danych.";
    }
  } finally {
    if (current === revision) byId("search-loader").hidden = true;
  }
}

function go(name) {
  view = accessibleView(name);
  history.replaceState(null, "", "#" + view);
  render();
  byId("heading").focus();
}
document.querySelectorAll("[data-view]").forEach(node => { node.onclick = () => go(node.dataset.view); });
document.querySelectorAll("[data-go]").forEach(node => { node.onclick = () => go(node.dataset.go); });
byId("actor").onchange = () => {
  for (const id of ["submission", "need"]) {
    const form = byId(id);
    form.reset();
    form.closest("details").open = false;
  }
  render();
};
function applyCatalogFilters() {
  catalogQuery = new URLSearchParams(new FormData(byId("filter")));
  catalogPage = 1;
  render();
}
byId("filter").onsubmit = event => {
  event.preventDefault();
  applyCatalogFilters();
};
byId("filter-options").onchange = applyCatalogFilters;
byId("filter").onreset = () => {
  catalogQuery = new URLSearchParams();
  catalogPage = 1;
  byId("filter-options").querySelectorAll("input").forEach(input => { input.indeterminate = false; });
  render();
};
byId("catalog-prev").onclick = () => { catalogPage--; render(); };
byId("catalog-next").onclick = () => { catalogPage++; render(); };
for (const [id, endpoint] of [["submission", "submissions"], ["need", "needs"]]) {
  byId(id).onsubmit = event => {
    event.preventDefault();
    const form = event.currentTarget;
    const body = Object.fromEntries(new FormData(form));
    for (const field of ["tags", "condition_tags", "available_conditions"]) {
      if (field in body) body[field] = body[field].split(",").map(value => value.trim()).filter(Boolean);
    }
    const profile = byId("actor").value;
    act(async () => {
      await api(endpoint, body);
      if (byId("actor").value === profile) form.reset();
    }, event.submitter);
  };
}
// --- Dodaj projekt ---
const MIN_TRL = 3;
const MAX_FILES = 5;
const MAX_FILE_BYTES = 8 * 1024 * 1024;
let projectFiles = [];

function formatSize(bytes) {
  return bytes < 1024 * 1024 ? Math.max(1, Math.round(bytes / 1024)) + " KB" : (bytes / 1024 / 1024).toFixed(1) + " MB";
}

function projectError(message) {
  const node = byId("project-error");
  node.textContent = message;
  node.hidden = !message;
}

function renderFiles() {
  const list = byId("file-list");
  list.replaceChildren();
  projectFiles.forEach((file, index) => {
    const row = element("li", "", list);
    element("span", file.name + " · " + formatSize(file.size), row);
    const remove = actionButton("Usuń", row, () => {
      projectFiles.splice(index, 1);
      renderFiles();
      byId("files").focus();
    });
    remove.className = "secondary";
    remove.setAttribute("aria-label", "Usuń plik " + file.name);
  });
}

function addFiles(files) {
  const problems = [];
  for (const file of files) {
    if (projectFiles.length >= MAX_FILES) { problems.push("Można dołączyć maksymalnie " + MAX_FILES + " plików."); break; }
    if (file.size > MAX_FILE_BYTES) { problems.push(file.name + " jest większy niż 8 MB."); continue; }
    if (projectFiles.some(other => other.name === file.name && other.size === file.size)) continue;
    projectFiles.push(file);
  }
  renderFiles();
  projectError(problems.join(" "));
}

function updateTrl() {
  const value = Number(byId("trl").value);
  const note = byId("trl-note");
  const submit = byId("project-submit");
  note.replaceChildren();
  note.hidden = !value;
  submit.disabled = Boolean(value) && value < MIN_TRL;
  if (!value) return;
  const tooLow = value < MIN_TRL;
  note.className = "trl-note " + (tooLow ? "warn" : "ok");
  element("span", tooLow ? "🌱" : "✓", note).className = "note-icon";
  const text = element("div", "", note);
  if (tooLow) {
    element("strong", "Jeszcze chwila pracy!", text);
    element("span", "Twój pomysł zapowiada się ciekawie, ale przyjmujemy projekty od poziomu TRL 3, czyli od eksperymentalnego potwierdzenia koncepcji. Dopracuj go jeszcze trochę, sprawdź w pierwszym eksperymencie i wróć do nas. Na pewno się uda, trzymamy kciuki!", text);
  } else {
    element("strong", "Świetnie, projekt spełnia próg dojrzałości.", text);
    element("span", "Na tym etapie możesz go zgłosić do oceny przez zespół PCI.", text);
  }
}

function readBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
    reader.onerror = () => reject(new Error("Nie udało się odczytać pliku " + file.name + "."));
    reader.readAsDataURL(file);
  });
}

function validateProject(form) {
  const field = name => form.elements[name];
  for (const [name, message] of [
    ["first_name", "Podaj imię."], ["last_name", "Podaj nazwisko."],
    ["title", "Podaj tytuł projektu."], ["description", "Opisz projekt."],
    ["repository", "Dodaj link do repozytorium GIT, artykułu lub innego potwierdzenia."],
    ["trl", "Wybierz stopień TRL."], ["area", "Wybierz obszar oddziaływania."], ["scope", "Wybierz zasięg oddziaływania."],
  ]) {
    if (!field(name).value.trim()) return [field(name), message];
  }
  if (!field("phone").value.trim() && !field("email").value.trim()) return [field("phone"), "Podaj telefon lub adres e-mail, abyśmy mogli się skontaktować."];
  if (phoneProblem(field("phone").value)) return [field("phone"), phoneProblem(field("phone").value)];
  if (field("email").value.trim() && !field("email").checkValidity()) return [field("email"), "Adres e-mail wygląda na niepełny. Sprawdź go, proszę."];
  if (!/^https?:\/\/\S+$/.test(field("repository").value.trim())) return [field("repository"), "Link powinien zaczynać się od http:// lub https://."];
  if (Number(field("trl").value) < MIN_TRL) return [field("trl"), "Projekty przyjmujemy od poziomu TRL 3. Jeszcze chwila pracy!"];
  return null;
}

const dropzone = byId("dropzone");
["dragenter", "dragover"].forEach(type => dropzone.addEventListener(type, event => {
  event.preventDefault();
  dropzone.classList.add("dragging");
}));
["dragleave", "drop"].forEach(type => dropzone.addEventListener(type, event => {
  event.preventDefault();
  dropzone.classList.remove("dragging");
}));
dropzone.addEventListener("drop", event => addFiles([...event.dataTransfer.files]));
byId("files").onchange = event => { addFiles([...event.target.files]); event.target.value = ""; };
byId("trl").onchange = updateTrl;

function phoneProblem(value) {
  const phone = value.trim();
  if (!phone) return "";
  if (/[^\d\s()+-]/.test(phone)) return "Numer telefonu może zawierać tylko cyfry, spacje, nawiasy, myślniki i znak +.";
  if (phone.replace(/\D/g, "").length < 7) return "Numer telefonu wygląda na za krótki.";
  return "";
}

function checkPhone(final) {
  const input = byId("project").elements.phone;
  const note = byId("phone-error");
  let problem = phoneProblem(input.value);
  if (!final && problem && !/[^\d\s()+-]/.test(input.value)) problem = "";
  note.textContent = problem;
  note.hidden = !problem;
  if (problem) input.setAttribute("aria-invalid", "true");
  else input.removeAttribute("aria-invalid");
}
byId("project").elements.phone.addEventListener("input", () => checkPhone(false));
byId("project").elements.phone.addEventListener("blur", () => checkPhone(true));

byId("project").onsubmit = async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const problem = validateProject(form);
  if (problem) {
    projectError(problem[1]);
    problem[0].focus();
    return;
  }
  projectError("");
  const submit = byId("project-submit");
  submit.disabled = true;
  submit.textContent = "Wysyłanie…";
  try {
    const body = Object.fromEntries(new FormData(form));
    body.trl = Number(body.trl);
    body.files = await Promise.all(projectFiles.map(async file => ({
      name: file.name, content_type: file.type || "application/octet-stream", data: await readBase64(file),
    })));
    const response = await fetch("/api/projects", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Sprawdź dane formularza.");
    byId("project-done-text").textContent = "Projekt „" + body.title + "” trafił do kolejki oceny jako karta na etapie: " + data.stage + ". Numer zgłoszenia: " + data.id + ".";
    form.hidden = true;
    byId("project-done").hidden = false;
    byId("project-done").focus();
  } catch (error) {
    projectError(error.message);
  } finally {
    submit.textContent = "Wyślij zgłoszenie";
    updateTrl();
  }
};

byId("project-again").onclick = () => {
  const form = byId("project");
  form.reset();
  projectFiles = [];
  renderFiles();
  updateTrl();
  projectError("");
  checkPhone(false);
  byId("project-done").hidden = true;
  form.hidden = false;
  form.elements.first_name.focus();
};

render();
