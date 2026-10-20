(() => {
"use strict";
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const money = (l) => "$" + Number(l.price).toLocaleString("fr-FR") + (l.deal === "location" ? " / mois" : "");
const I = {
  search: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>',
  heart: '<svg viewBox="0 0 32 32"><path d="M16 28C7 22 2 16.5 2 11a7 7 0 0 1 14-2 7 7 0 0 1 14 2c0 5.500-5 11-14 17z"/></svg>',
  star: '<svg class="star" viewBox="0 0 24 24"><path d="m12 2 3 7 7.500.6-5.700 5 1.800 7.400L12 18l-6.600 4 1.800-7.400-5.700-5L9 9z"/></svg>',
  check: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m4 12 5 5L20 6"/></svg>',
  filter: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/></svg>',
  burger: '<svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.500" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>',
};
const CATS = [
  ["", "Tout", '<path d="M4 11 12 4l8 7M6 10v10h12V10"/>'],
  ["maison", "Maisons", '<path d="M3 12 12 4l9 8M5 10.500V20h5v-5h4v5h5v-9.500"/>'],
  ["appartement", "Appartements", '<path d="M5 21V4h14v17M9 8h2M13 8h2M9 12h2M13 12h2M10 21v-4h4v4"/>'],
  ["villa", "Villas", '<path d="M2 21h20M4 21V10l8-6 8 6v11M9 21v-6h6v6M8 11h2M14 11h2"/>'],
  ["studio", "Studios", '<path d="M4 8h16v12H4zM4 8l8-5 8 5M10 20v-6h4v6"/>'],
  ["terrain", "Terrains", '<path d="M3 20h18M5 20l5-9 3 5 2-3 4 7M16 6a2 2 0 1 0 .1 0"/>'],
];

const state = { user: null, meta: null, f: {} };
const FILTER_KEYS = ["city", "commune", "deal", "ptype", "max_price", "min_price", "bedrooms", "furnished", "sort", "q"];

async function api(path, opts = {}) {
  const o = { method: "GET", headers: { "X-Ndaku": "1" }, ...opts };
  if (opts.json) { o.method = o.method === "GET" ? "POST" : o.method; o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(opts.json); }
  const r = await fetch(path, o);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(data.error || "Erreur"), { status: r.status, data });
  return data;
}
let tt;
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(tt); tt = setTimeout(() => t.classList.remove("show"), 3200); }
const when = ts => new Date(ts * 1000).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" });

/* ------------------------------------------------------------------ modal */
function modal(title, html, cls = "") {
  closeModal();
  const ov = document.createElement("div");
  ov.className = "ov";
  ov.innerHTML = `<div class="mdl ${cls}" role="dialog" aria-modal="true" aria-label="${esc(title)}"><header><button class="x" data-act="close" aria-label="Fermer">✕</button>${esc(title)}</header><div class="bd">${html}</div></div>`;
  ov.addEventListener("mousedown", e => { if (e.target === ov) closeModal(); });
  $("#modal-root").append(ov);
  const first = ov.querySelector("input,select,textarea,button:not(.x)"); first && first.focus();
  return ov;
}
const closeModal = () => { $("#modal-root").innerHTML = ""; };
document.addEventListener("keydown", e => { if (e.key === "Escape") { closeModal(); closePop(); } });

/* ----------------------------------------------------------------- header */
function opts(list, sel, all) { return (all ? `<option value="">${all}</option>` : "") + list.map(x => `<option ${x === sel ? "selected" : ""}>${esc(x)}</option>`).join(""); }
function renderHeader() {
  const f = state.f, u = state.user, cities = Object.keys(state.meta.cities);
  const communes = f.city ? state.meta.cities[f.city] : [];
  $("#hdr").innerHTML = `
    <a class="logo" href="#/" aria-label="Ndaku, accueil"><img src="/logo.svg" alt=""><span>ndaku</span></a>
    <form class="search" id="searchForm" role="search">
      <div class="seg"><label for="s-city">Où</label><select id="s-city"><option value="">Toutes les villes</option>${opts(cities, f.city)}</select></div>
      <div class="seg"><label for="s-com">Quartier</label><select id="s-com" ${f.city ? "" : "disabled"}>${opts(communes, f.commune, "Tous")}</select></div>
      <div class="seg"><label for="s-deal">Offre</label><select id="s-deal"><option value="">Louer ou acheter</option><option value="location" ${f.deal === "location" ? "selected" : ""}>Louer</option><option value="vente" ${f.deal === "vente" ? "selected" : ""}>Acheter</option></select></div>
      <div class="seg"><label for="s-max">Budget max ($)</label><input id="s-max" type="number" min="0" inputmode="numeric" placeholder="Illimité" value="${esc(f.max_price || "")}"></div>
      <button class="go" aria-label="Rechercher">${I.search}</button>
    </form>
    <div class="nav">
      ${!u || u.role === "host" ? `<a class="link host-cta" href="${u ? "#/new" : "#/host"}" data-need="host">Mettre ma maison sur Ndaku</a>` : ""}
      <button class="menu-btn" id="menuBtn" aria-haspopup="true" aria-label="Menu du compte">${I.burger}<span class="avatar ${u ? "on" : ""}">${u ? esc(u.name[0].toUpperCase()) : "👤"}</span></button>
    </div>`;
  $("#s-city").onchange = e => { state.f = { ...state.f, city: e.target.value, commune: "" }; renderHeader(); };
  $("#searchForm").onsubmit = e => {
    e.preventDefault();
    state.f = { ...state.f, city: $("#s-city").value, commune: $("#s-com").value, deal: $("#s-deal").value, max_price: $("#s-max").value };
    go("#/" + qs(state.f));
  };
  $("#menuBtn").onclick = e => { e.stopPropagation(); togglePop(); };
}
function closePop() { const p = $(".pop"); p && p.remove(); }
function togglePop() {
  if ($(".pop")) return closePop();
  const u = state.user;
  const p = document.createElement("div");
  p.className = "pop";
  p.innerHTML = u ? `<div class="who">${esc(u.name)} · ${u.role === "host" ? "Hôte" : u.role === "admin" ? "Admin" : "Client"}${u.verified ? " · ✓ vérifié" : ""}</div>
      ${u.role === "host" ? `<a href="#/host">Mes annonces</a><a href="#/new">Publier une annonce</a>` : ""}
      ${u.role === "client" ? `<a href="#/favorites">Favoris</a><a href="#/messages">Mes demandes de visite</a>` : ""}
      ${u.role === "admin" ? `<a href="#/admin">Modération</a>` : ""}<hr><button data-act="logout">Se déconnecter</button>`
    : `<button data-act="login">Se connecter</button><button data-act="signup">S'inscrire</button><hr><button data-act="signup-host">Devenir hôte</button>`;
  document.body.append(p);
}
document.addEventListener("click", closePop);

/* ------------------------------------------------------------------- auth */
function authModal(mode = "login", role = "client") {
  const reg = mode === "signup";
  const m = modal(reg ? "Inscription" : "Connexion", `
    <div class="tabs"><button class="${reg ? "" : "on"}" data-act="login">Connexion</button><button class="${reg ? "on" : ""}" data-act="signup">Inscription</button></div>
    <h2>Bienvenue sur Ndaku</h2>
    <form id="authForm" novalidate>
      ${reg ? `<div class="seg-pick"><label><input type="radio" name="role" value="client" ${role === "client" ? "checked" : ""}><b>Client</b><span>Je cherche à louer ou acheter</span></label>
        <label><input type="radio" name="role" value="host" ${role === "host" ? "checked" : ""}><b>Hôte</b><span>Je propose un bien</span></label></div>
        <div class="field"><label for="a-name">Nom complet</label><input id="a-name" name="name" autocomplete="name" required></div>` : ""}
      <div class="field"><label for="a-mail">E-mail</label><input id="a-mail" name="email" type="email" autocomplete="email" required></div>
      ${reg ? `<div class="field"><label for="a-tel">Téléphone (optionnel)</label><input id="a-tel" name="phone" type="tel" autocomplete="tel"></div>` : ""}
      <div class="field"><label for="a-pw">Mot de passe</label><input id="a-pw" name="password" type="password" autocomplete="${reg ? "new" : "current"}-password" required>${reg ? '<span class="hint">8 caractères min., une majuscule et un chiffre.</span>' : ""}</div>
      <div class="err" id="authErr" role="alert"></div>
      <button class="btn block">${reg ? "Créer mon compte" : "Continuer"}</button>
    </form>`);
  m.querySelector("#authForm").onsubmit = async e => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(e.target));
    try {
      const r = await api(reg ? "/api/register" : "/api/login", { json: d });
      state.user = r.user; closeModal(); renderHeader(); route(); toast(`Bienvenue ${r.user.name} !`);
    } catch (err) { $("#authErr").textContent = err.message; }
  };
}

/* ---------------------------------------------------------------- routing */
const qs = f => { const p = new URLSearchParams(); for (const k of FILTER_KEYS) if (f[k]) p.set(k, f[k]); const s = p.toString(); return s ? "?" + s : ""; };
const go = h => { if (location.hash === h) route(); else location.hash = h; };
function parse() {
  const [path, q] = (location.hash.slice(1) || "/").split("?");
  return { path, params: Object.fromEntries(new URLSearchParams(q || "")) };
}
async function route() {
  closePop(); window.scrollTo(0, 0);
  const { path, params } = parse();
  const view = $("#view");
  $("#cats").style.display = path === "/" ? "" : "none";
  try {
    if (path === "/") { state.f = Object.fromEntries(FILTER_KEYS.filter(k => params[k]).map(k => [k, params[k]])); renderHeader(); renderCats(); return await home(); }
    renderHeader();
    let m;
    if ((m = path.match(/^\/listing\/(\d+)$/))) return await detail(+m[1]);
    if (path === "/host") return await dashboard();
    if (path === "/new") return await newListing();
    if (path === "/favorites") return await favorites();
    if (path === "/messages") return await messages();
    if (path === "/admin") return await admin();
    view.innerHTML = `<div class="wrap empty"><h3>Page introuvable</h3><a class="btn" href="#/">Retour à l'accueil</a></div>`;
  } catch (e) {
    if (e.status === 401) { view.innerHTML = `<div class="wrap empty"><h3>Connexion requise</h3><p>Connectez-vous pour continuer.</p><button class="btn" data-act="login">Se connecter</button></div>`; }
    else view.innerHTML = `<div class="wrap empty"><h3>${esc(e.message)}</h3><a class="btn" href="#/">Retour à l'accueil</a></div>`;
  }
}

/* ------------------------------------------------------------------- home */
function renderCats() {
  $("#cats").innerHTML = CATS.map(([v, l, svg]) => `<button class="cat ${(state.f.ptype || "") === v ? "on" : ""}" data-cat="${v}"><svg viewBox="0 0 24 24">${svg}</svg>${l}</button>`).join("")
    + `<button class="filter-btn" data-act="filters">${I.filter} Filtres</button>`;
}
function cardHtml(l, top) {
  const loc = l.commune === l.city ? l.city : `${l.commune}, ${l.city}`;
  return `<a class="card" href="#/listing/${l.id}">
    <div class="ph">${l.cover ? `<img loading="lazy" src="/uploads/${esc(l.cover)}" alt="${esc(l.title)}">` : ""}
      <button class="heart ${l.favorite ? "on" : ""}" data-fav="${l.id}" aria-label="Ajouter aux favoris" aria-pressed="${l.favorite}">${I.heart}</button>
      ${top ? '<span class="badge">Coup de cœur</span>' : `<span class="badge deal">${l.deal === "location" ? "À louer" : "À vendre"}</span>`}</div>
    <div class="row"><b>${esc(loc)}</b><span class="rt">${l.rating ? I.star + Number(l.rating).toFixed(1) : "Nouveau"}</span></div>
    <div class="m">${esc(l.title)}</div>
    <div class="m">${l.ptype === "terrain" ? "Terrain" : cap(l.ptype) + " · " + l.bedrooms + " ch."} · ${l.surface} m²</div>
    <div class="price"><b>${money(l)}</b></div></a>`;
}
const cap = s => s[0].toUpperCase() + s.slice(1);
async function home() {
  const view = $("#view"), f = state.f;
  view.innerHTML = `<div class="wrap"><h2 class="sec-title" id="ht"></h2><p class="sec-sub" id="hs"></p><div class="grid">${'<div><div class="skeleton"></div></div>'.repeat(8)}</div></div>`;
  const r = await api("/api/listings" + qs(f).replace(/^$/, "?"));
  const filtered = FILTER_KEYS.some(k => f[k] && k !== "sort");
  const where = f.commune ? `${f.commune}, ${f.city}` : f.city || "toute la RDC";
  view.innerHTML = `<div class="wrap"><h2 class="sec-title">${filtered ? `${r.total} bien${r.total > 1 ? "s" : ""} à ${esc(where)}` : "Les meilleures maisons du moment"}</h2>
    <p class="sec-sub">${f.sort && f.sort !== "top" ? "" : "Classées par avis vérifiés, favoris et fiabilité de l'hôte."}</p>
    ${r.items.length ? `<div class="grid">${r.items.map((l, i) => cardHtml(l, !filtered && i < 3 && l.rating >= 4)).join("")}</div>`
      : `<div class="empty"><h3>Aucun résultat</h3><p>Essayez d'élargir votre recherche.</p><a class="btn ghost" href="#/">Réinitialiser</a></div>`}</div>`;
}
function filtersModal() {
  const f = state.f;
  const m = modal("Filtres", `<form id="ff">
    <div class="field"><label>Trier par</label><select name="sort"><option value="">Meilleurs d'abord</option>
      ${[["new", "Plus récents"], ["price_asc", "Prix croissant"], ["price_desc", "Prix décroissant"]].map(([v, l]) => `<option value="${v}" ${f.sort === v ? "selected" : ""}>${l}</option>`).join("")}</select></div>
    <div class="cols"><div class="field"><label>Prix min ($)</label><input name="min_price" type="number" min="0" value="${esc(f.min_price || "")}"></div>
    <div class="field"><label>Prix max ($)</label><input name="max_price" type="number" min="0" value="${esc(f.max_price || "")}"></div></div>
    <div class="field"><label>Chambres (minimum)</label><select name="bedrooms"><option value="">Indifférent</option>${[1, 2, 3, 4, 5].map(n => `<option ${+f.bedrooms === n ? "selected" : ""}>${n}</option>`).join("")}</select></div>
    <div class="field"><label>Mot-clé</label><input name="q" value="${esc(f.q || "")}" placeholder="piscine, jardin, avenue…"></div>
    <label class="chk" style="margin-bottom:20px"><input type="checkbox" name="furnished" value="1" ${f.furnished ? "checked" : ""}> Meublé uniquement</label>
    <div class="row-actions"><button type="button" class="btn ghost" data-act="reset">Effacer</button><button class="btn">Afficher les biens</button></div></form>`);
  m.querySelector("#ff").onsubmit = e => { e.preventDefault(); const d = Object.fromEntries(new FormData(e.target)); closeModal(); go("#/" + qs({ ...state.f, sort: "", min_price: "", max_price: "", bedrooms: "", q: "", furnished: "", ...d })); };
}

/* ----------------------------------------------------------------- detail */
async function detail(id) {
  const l = await api("/api/listings/" + id), u = state.user, view = $("#view");
  const imgs = l.images, n = Math.min(imgs.length, 5);
  const isOwner = u && u.id === l.host.id;
  view.innerHTML = `<div class="wrap dt">
    ${l.status !== "active" ? `<div class="notice warn" style="margin-top:16px">Statut : <b>${l.status}</b> — cette annonce n'est visible que par vous${l.status === "pending" ? " (en cours de vérification par la modération)" : ""}.</div>` : ""}
    ${l.risk_reasons?.length ? `<div class="risk"><b>Signaux anti-fraude (score ${l.risk_score})</b><ul>${l.risk_reasons.map(r => `<li>${esc(r)}</li>`).join("")}</ul></div>` : ""}
    <h1>${esc(l.title)}</h1>
    <div class="meta"><span class="rt">${l.rating ? I.star + " <b style='color:var(--ink)'>" + Number(l.rating).toFixed(1) + "</b> · " + l.reviews_count + " avis" : "Pas encore d'avis"}</span>
      <span>· ${esc(l.commune)}, ${esc(l.city)}</span><span style="margin-left:auto"><button class="btn ghost sm" data-fav="${l.id}" aria-pressed="${l.favorite}">${l.favorite ? "♥ Enregistré" : "♡ Enregistrer"}</button></span></div>
    <div class="gal n${n}" data-act="lightbox">${imgs.slice(0, 5).map((s, i) => `<img src="/uploads/${esc(s)}" alt="Photo ${i + 1} : ${esc(l.title)}" data-i="${i}">`).join("")}</div>
    <div class="dt-body"><div>
      <div class="block-sec"><div class="hostrow"><span class="avatar on">${esc(l.host.name[0])}</span><div><h2 style="margin:0;font-size:18px">${cap(l.ptype)} ${l.deal === "location" ? "à louer" : "à vendre"} · hôte : ${esc(l.host.name)}</h2>
        ${l.host.verified ? `<span class="verif">${I.check} Hôte vérifié par Ndaku</span>` : '<span class="unverif">Hôte non encore vérifié : ne payez rien avant la visite.</span>'}</div></div>
        <div class="specs" style="margin-top:14px"><span>${l.bedrooms} chambre${l.bedrooms > 1 ? "s" : ""}</span><span>· ${l.bathrooms} salle${l.bathrooms > 1 ? "s" : ""} de bain</span><span>· ${l.surface} m²</span>${l.furnished ? "<span>· Meublé</span>" : ""}</div></div>
      <div class="block-sec"><h2>À propos de ce bien</h2><div class="desc">${esc(l.description)}</div><p class="hint">Adresse : ${esc(l.address)}, ${esc(l.commune)}</p></div>
      ${l.amenities.length ? `<div class="block-sec"><h2>Équipements</h2><div class="am-grid">${l.amenities.map(a => `<div>${I.check} ${esc(a)}</div>`).join("")}</div></div>` : ""}
      <div class="block-sec"><h2>${l.reviews_count ? `${I.star} ${Number(l.rating).toFixed(1)} · ${l.reviews_count} avis vérifiés` : "Avis"}</h2>
        ${l.reviews.map(r => `<div class="rev"><div class="who">${esc(r.name)} <span class="stars">${"★".repeat(r.rating)}${"☆".repeat(5 - r.rating)}</span></div><time>${when(r.created_at)}</time><div>${esc(r.comment)}</div></div>`).join("") || '<p class="hint">Aucun avis pour le moment.</p>'}
        ${l.can_review ? `<form id="revForm"><div class="field"><label>Votre note</label><select name="rating">${[5, 4, 3, 2, 1].map(n => `<option value="${n}">${"★".repeat(n)}</option>`).join("")}</select></div><div class="field"><label>Votre avis</label><textarea name="comment" minlength="10" required style="min-height:80px"></textarea></div><button class="btn sm">Publier l'avis</button></form>` : '<p class="hint">Seuls les clients ayant contacté l\'hôte via Ndaku peuvent laisser un avis.</p>'}</div>
    </div>
    <aside><div class="panel"><div class="big">${money(l).replace(" / mois", "")}${l.deal === "location" ? " <small>/ mois</small>" : ""}</div>
      ${isOwner || (u && u.role === "admin") ? `<p class="hint" style="margin-top:12px">Vous gérez cette annonce.</p>${isOwner && l.status === "active" ? `<button class="btn ghost block" data-close="${l.id}">Marquer comme ${l.deal === "location" ? "loué" : "vendu"}</button>` : ""}`
        : `<form id="inqForm" style="margin-top:16px"><div class="field"><label>Date de visite souhaitée</label><input type="date" name="preferred_date" min="${new Date().toISOString().slice(0, 10)}"></div>
        <div class="field"><label>Message à l'hôte</label><textarea name="message" required minlength="10" style="min-height:90px">Bonjour, ce bien est-il toujours disponible ? Je souhaiterais le visiter.</textarea></div>
        <button class="btn block">Demander une visite</button></form>`}
      <div class="safe"><b>🛡 Restez protégé</b><br>Ne versez jamais d'argent avant d'avoir visité. Toute annonce est contrôlée (photos uniques, adresse unique).</div>
      ${!isOwner && u ? `<p style="text-align:center;margin:14px 0 0"><button class="btn sm ghost" data-report="${l.id}">⚑ Signaler cette annonce</button></p>` : ""}</div></aside></div></div>`;
  window.__imgs = imgs;
  const rf = $("#revForm"), inq = $("#inqForm");
  if (rf) rf.onsubmit = async e => { e.preventDefault(); try { await api(`/api/listings/${id}/reviews`, { json: Object.fromEntries(new FormData(rf)) }); toast("Merci pour votre avis !"); detail(id); } catch (x) { toast(x.message); } };
  if (inq) inq.onsubmit = async e => {
    e.preventDefault();
    if (!u) return authModal("signup", "client");
    try { await api(`/api/listings/${id}/inquiries`, { json: Object.fromEntries(new FormData(inq)) }); toast("Demande envoyée à l'hôte ✓"); detail(id); } catch (x) { toast(x.message); }
  };
}
function lightbox(i) {
  const imgs = window.__imgs; if (!imgs) return;
  let k = +i || 0;
  const m = modal(`Photo ${k + 1} / ${imgs.length}`, `<img src="/uploads/${esc(imgs[k])}" alt="">`, "lightbox");
  m.querySelector(".mdl").style.cursor = "pointer";
  m.querySelector(".mdl").onclick = e => { if (e.target.closest(".x")) return; k = (k + 1) % imgs.length; m.querySelector("img").src = "/uploads/" + imgs[k]; m.querySelector("header").lastChild.textContent = `Photo ${k + 1} / ${imgs.length}`; };
}

/* -------------------------------------------------------- favoris/messages */
async function favorites() {
  const r = await api("/api/favorites");
  $("#view").innerHTML = `<div class="wrap page"><h1>Mes favoris</h1>${r.items.length ? `<div class="grid">${r.items.map(l => cardHtml(l)).join("")}</div>` : '<div class="empty"><h3>Aucun favori</h3><p>Touchez le cœur d\'une annonce pour la retrouver ici.</p><a class="btn" href="#/">Explorer</a></div>'}</div>`;
}
async function messages() {
  const r = await api("/api/my/inquiries"), host = state.user?.role === "host";
  $("#view").innerHTML = `<div class="wrap page"><h1>${host ? "Demandes de visite reçues" : "Mes demandes de visite"}</h1>
    ${r.items.length ? `<div class="table-wrap"><table class="tbl"><thead><tr><th>Annonce</th><th>${host ? "Client" : "Hôte"}</th><th>Message</th><th>Visite</th><th>Date</th></tr></thead><tbody>${r.items.map(q => `<tr><td><a href="#/listing/${q.listing_id}">${esc(q.title)}</a></td><td>${esc(q.who)}${q.who_phone ? `<br><span class="hint">${esc(q.who_phone)}</span>` : ""}</td><td>${esc(q.message)}</td><td>${esc(q.preferred_date || "—")}</td><td>${when(q.created_at)}</td></tr>`).join("")}</tbody></table></div>` : '<div class="empty"><h3>Rien pour le moment</h3></div>'}</div>`;
}

/* -------------------------------------------------------------- dashboard */
async function dashboard() {
  const u = state.user;
  if (!u) { $("#view").innerHTML = `<div class="wrap empty"><h3>Devenez hôte sur Ndaku</h3><p>Publiez vos maisons à louer ou à vendre en quelques minutes.</p><button class="btn" data-act="signup-host">Créer un compte hôte</button></div>`; return; }
  if (u.role !== "host") throw Object.assign(new Error("Espace réservé aux hôtes."), { status: 403 });
  const [r, q] = await Promise.all([api("/api/my/listings"), api("/api/my/inquiries")]);
  $("#view").innerHTML = `<div class="wrap page"><div class="row-actions" style="justify-content:space-between;margin-bottom:12px"><h1 style="margin:0">Mes annonces</h1><a class="btn" href="#/new">+ Nouvelle annonce</a></div>
    ${u.verified ? "" : '<div class="notice warn">Votre compte n\'est pas encore vérifié : vos annonces peuvent être revues manuellement avant publication.</div>'}
    ${r.items.length ? `<div class="table-wrap"><table class="tbl"><thead><tr><th></th><th>Annonce</th><th>Prix</th><th>Statut</th><th>Demandes</th><th></th></tr></thead><tbody>
      ${r.items.map(l => `<tr><td>${l.cover ? `<img class="thumb" src="/uploads/${esc(l.cover)}" alt="">` : ""}</td><td><a href="#/listing/${l.id}"><b>${esc(l.title)}</b></a><br><span class="hint">${esc(l.commune)}, ${esc(l.city)}</span>${l.status === "pending" ? `<br><span class="hint">En vérification : ${esc(l.risk_reasons.join(" · "))}</span>` : ""}</td>
        <td>${money(l)}</td><td><span class="pill ${l.status}">${{ active: "En ligne", pending: "En vérification", rejected: "Rejetée", closed: l.deal === "location" ? "Loué" : "Vendu" }[l.status]}</span></td><td>${l.inquiries}</td>
        <td>${l.status === "rejected" ? "" : `<button class="btn danger sm" data-del="${l.id}">Supprimer</button>`}</td></tr>`).join("")}</tbody></table></div>` : '<div class="empty"><h3>Aucune annonce</h3><p>Publiez votre première maison.</p><a class="btn" href="#/new">Publier</a></div>'}
    <h2 style="margin-top:40px">Dernières demandes de visite</h2>
    ${q.items.length ? `<div class="table-wrap"><table class="tbl"><tbody>${q.items.slice(0, 8).map(x => `<tr><td>${esc(x.who)}</td><td>${esc(x.title)}</td><td>${esc(x.message)}</td><td>${esc(x.preferred_date || "")}</td></tr>`).join("")}</tbody></table></div>` : '<p class="hint">Aucune demande.</p>'}</div>`;
}

let files = [];
async function newListing() {
  const u = state.user;
  if (!u) throw Object.assign(new Error("Connexion requise"), { status: 401 });
  if (u.role !== "host") throw Object.assign(new Error("Seuls les hôtes peuvent publier des annonces."), { status: 403 });
  files = [];
  const M = state.meta;
  $("#view").innerHTML = `<div class="wrap page"><form class="form" id="nf" novalidate><h1>Publier un bien</h1>
    <div class="seg-pick"><label><input type="radio" name="deal" value="location" checked><b>Location</b><span>Prix par mois</span></label><label><input type="radio" name="deal" value="vente"><b>Vente</b><span>Prix de vente total</span></label></div>
    <div class="field"><label for="n-title">Titre</label><input id="n-title" name="title" maxlength="120" required placeholder="Ex. Villa 4 chambres avec jardin à Ngaliema"></div>
    <div class="cols"><div class="field"><label>Type de bien</label><select name="ptype">${M.ptypes.map(p => `<option value="${p}">${cap(p)}</option>`).join("")}</select></div>
    <div class="field"><label id="pl">Loyer mensuel (USD)</label><input name="price" type="number" min="1" required></div></div>
    <div class="cols"><div class="field"><label>Ville</label><select name="city" id="n-city">${opts(Object.keys(M.cities))}</select></div>
    <div class="field"><label>Commune / quartier</label><select name="commune" id="n-com"></select></div></div>
    <div class="field"><label>Adresse précise</label><input name="address" required maxlength="160" placeholder="Avenue, numéro, repère"><span class="hint">Une adresse ne peut être publiée que par un seul hôte.</span></div>
    <div class="cols3"><div class="field"><label>Chambres</label><input name="bedrooms" type="number" min="0" max="20" value="2" required></div>
    <div class="field"><label>Salles de bain</label><input name="bathrooms" type="number" min="0" max="20" value="1" required></div>
    <div class="field"><label>Surface (m²)</label><input name="surface" type="number" min="9" required></div></div>
    <div class="field"><label>Description</label><textarea name="description" required minlength="60" placeholder="Décrivez le bien, le quartier, l'état, les conditions (60 caractères minimum)."></textarea>
      <span class="hint">Pas de numéro de téléphone, e-mail ni lien : les échanges se font sur Ndaku pour votre sécurité.</span></div>
    <label class="chk" style="margin-bottom:14px"><input type="checkbox" name="furnished" value="1"> Meublé</label>
    <div class="field"><span class="lbl">Équipements</span><div class="tags">${M.amenities.map(a => `<label class="tag"><input type="checkbox" name="amenities" value="${esc(a)}">${esc(a)}</label>`).join("")}</div></div>
    <div class="field"><span class="lbl">Photos (${M.min_images} à ${M.max_images}) — uniques, prises par vous</span>
      <label class="drop" id="drop" for="n-files">Glissez vos photos ici ou <u>parcourez</u><br><span class="hint">JPEG, PNG ou WebP · min. 480×320 · chaque photo est comparée à toutes les annonces existantes</span></label>
      <input id="n-files" type="file" accept="image/jpeg,image/png,image/webp" multiple hidden><div class="previews" id="pvs"></div></div>
    <div class="err" id="nerr" role="alert"></div><button class="btn" id="nsub">Publier l'annonce</button></form></div>`;
  const city = $("#n-city"), com = $("#n-com"), fill = () => { com.innerHTML = opts(M.cities[city.value]); };
  fill(); city.onchange = fill;
  $("#nf").addEventListener("change", e => { if (e.target.name === "deal") $("#pl").textContent = e.target.value === "vente" ? "Prix de vente (USD)" : "Loyer mensuel (USD)"; if (e.target.closest(".tag")) e.target.closest(".tag").classList.toggle("on", e.target.checked); });
  const add = list => { for (const f of list) if (f.type.startsWith("image/") && files.length < M.max_images && !files.some(x => x.name === f.name && x.size === f.size)) files.push(f); drawPv(); };
  $("#n-files").onchange = e => { add([...e.target.files]); e.target.value = ""; };
  const drop = $("#drop");
  ["dragover", "dragenter"].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", e => add([...e.dataTransfer.files]));
  $("#pvs").onclick = e => { const b = e.target.closest("[data-rm]"); if (b) { files.splice(+b.dataset.rm, 1); drawPv(); } };
  $("#nf").onsubmit = async e => {
    e.preventDefault();
    const err = $("#nerr"); err.textContent = ""; drawPv();
    if (files.length < M.min_images) { err.textContent = `Ajoutez au moins ${M.min_images} photos.`; return; }
    const fd = new FormData(e.target); files.forEach(f => fd.append("images", f));
    const btn = $("#nsub"); btn.disabled = true; btn.textContent = "Contrôle anti-fraude en cours…";
    try {
      const r = await api("/api/listings", { method: "POST", body: fd });
      toast(r.status === "active" ? "Annonce publiée ✓" : "Annonce reçue : vérification par la modération");
      go("#/host");
    } catch (x) {
      err.textContent = x.message;
      if (x.data?.problems) {
        drawPv(Object.fromEntries(x.data.problems.map(p => [p.file, p.reason])));
        err.textContent += " Remplacez les photos signalées en rouge.";
      }
      btn.disabled = false; btn.textContent = "Publier l'annonce";
    }
  };
}
function drawPv(bad = {}) {
  $("#pvs").innerHTML = files.map((f, i) => `<div class="pv ${bad[f.name] ? "bad" : ""} ${i === 0 ? "first" : ""}"><img src="${URL.createObjectURL(f)}" alt=""><button type="button" data-rm="${i}" aria-label="Retirer">✕</button>${bad[f.name] ? `<div class="why">${esc(bad[f.name])}</div>` : ""}</div>`).join("");
}

/* ------------------------------------------------------------------ admin */
async function admin() {
  const r = await api("/api/admin/queue");
  $("#view").innerHTML = `<div class="wrap page"><h1>Modération (${r.items.length} en attente)</h1>
    ${r.items.map(l => `<div class="block-sec"><div class="row-actions" style="align-items:flex-start;justify-content:space-between"><div style="display:flex;gap:14px">${l.cover ? `<img class="thumb" src="/uploads/${esc(l.cover)}" alt="">` : ""}<div><a href="#/listing/${l.id}"><b>${esc(l.title)}</b></a><br><span class="hint">Hôte : ${esc(l.host)} ${l.host_verified ? "✓" : ""} · ${money(l)} · ${esc(l.commune)}</span>
      <div class="risk" style="margin-top:8px"><b>Risque ${l.risk_score}</b><ul style="margin:4px 0 0">${l.risk_reasons.map(x => `<li>${esc(x)}</li>`).join("")}${l.reports.map(x => `<li>Signalement : ${esc(x)}</li>`).join("")}</ul></div></div></div>
      <div class="row-actions"><button class="btn sm" data-decide="approve" data-id="${l.id}">Approuver</button><button class="btn danger sm" data-decide="reject" data-id="${l.id}">Rejeter</button></div></div></div>`).join("") || '<div class="empty"><h3>File vide 🎉</h3></div>'}</div>`;
}

/* ----------------------------------------------------------------- events */
document.addEventListener("click", async e => {
  const t = e.target;
  const act = t.closest("[data-act]")?.dataset.act;
  if (act === "login") return authModal("login");
  if (act === "signup") return authModal("signup", "client");
  if (act === "signup-host") return authModal("signup", "host");
  if (act === "close") return closeModal();
  if (act === "filters") return filtersModal();
  if (act === "reset") { closeModal(); return go("#/"); }
  if (act === "lightbox") return lightbox(t.dataset.i);
  if (act === "logout") { await api("/api/logout", { method: "POST" }); state.user = null; renderHeader(); go("#/"); return toast("À bientôt !"); }
  const cat = t.closest("[data-cat]");
  if (cat) return go("#/" + qs({ ...state.f, ptype: cat.dataset.cat }));
  const fav = t.closest("[data-fav]");
  if (fav) {
    e.preventDefault(); e.stopPropagation();
    if (!state.user) return authModal("login");
    try {
      const r = await api(`/api/listings/${fav.dataset.fav}/favorite`, { method: "POST" });
      fav.classList.toggle("on", r.favorite); fav.setAttribute("aria-pressed", r.favorite);
      if (fav.matches(".btn")) fav.textContent = r.favorite ? "♥ Enregistré" : "♡ Enregistrer";
      if (parse().path === "/favorites" && !r.favorite) route();
    } catch (x) { toast(x.message); }
    return;
  }
  const del = t.closest("[data-del]");
  if (del && confirm("Supprimer cette annonce ? Ses photos seront libérées.")) { try { await api("/api/listings/" + del.dataset.del, { method: "DELETE" }); route(); } catch (x) { toast(x.message); } return; }
  const cl = t.closest("[data-close]");
  if (cl) { try { await api("/api/listings/" + cl.dataset.close, { method: "PATCH", json: { status: "closed" } }); toast("Annonce clôturée"); route(); } catch (x) { toast(x.message); } return; }
  const rep = t.closest("[data-report]");
  if (rep) { const why = prompt("Pourquoi signalez-vous cette annonce ? (fausses photos, prix trompeur, arnaque…)"); if (why) { try { await api(`/api/listings/${rep.dataset.report}/report`, { json: { reason: why } }); toast("Signalement envoyé, merci."); } catch (x) { toast(x.message); } } return; }
  const dec = t.closest("[data-decide]");
  if (dec) { try { await api(`/api/admin/listings/${dec.dataset.id}/decision`, { json: { action: dec.dataset.decide } }); route(); } catch (x) { toast(x.message); } return; }
  if (t.closest("[data-need]") && !state.user) { e.preventDefault(); authModal("signup", "host"); }
});
window.addEventListener("hashchange", route);

(async () => {
  [state.meta, { user: state.user }] = await Promise.all([api("/api/meta"), api("/api/me")]);
  route();
})();
})();
