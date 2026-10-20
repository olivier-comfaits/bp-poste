const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const state = {
  projets: [],
  filter: "tous",
  current: null,
  dossier: null,
};

function scoreGauge(score, size = 72, light = false) {
  const s = Math.max(0, Math.min(100, Number(score) || 0));
  const r = (size - 10) / 2;
  const c = 2 * Math.PI * r;
  const dash = (s / 100) * c;
  const color = s >= 75 ? "#1f7a4d" : s >= 60 ? "#b86b00" : s >= 45 ? "#c47a12" : "#9b2335";
  const track = light ? "#ffffff33" : "#ece6d8";
  const text = light ? "#ffcd00" : "#141821";
  return `<svg class="gauge" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" aria-label="Score ${Math.round(s)}">
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${track}" stroke-width="7"/>
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${color}" stroke-width="7"
      stroke-dasharray="${dash} ${c}" stroke-linecap="round" transform="rotate(-90 ${size/2} ${size/2})"/>
    <text x="${size/2}" y="${size/2 + 5}" text-anchor="middle" font-size="${size > 80 ? 20 : 14}" font-weight="650" fill="${text}">${Math.round(s)}</text>
  </svg>`;
}

function miniBars(values, labels, colors) {
  const max = Math.max(...values.map((v) => Math.abs(Number(v) || 0)), 1);
  return `<div class="mini-bars">${values.map((v, i) => {
    const h = Math.max(4, Math.abs(Number(v) || 0) / max * 48);
    return `<div class="mb-col" title="${labels[i]} : ${v}"><div class="mb-bar" style="height:${h}px;background:${colors[i] || "#002b5c"}"></div><span>${labels[i]}</span></div>`;
  }).join("")}</div>`;
}

const euro = (n) => {
  const v = Number(n || 0);
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(v) + " k€";
};

const pillClass = (go) => {
  if (go === "go") return "go";
  if (go === "go_conditions") return "warn";
  if (go === "reviser") return "warn";
  return "stop";
};

async function api(path, opts) {
  const base = window.BASE || "";
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 70000);
  try {
    const res = await fetch(base + path, {
      headers: { "Content-Type": "application/json" },
      signal: ctrl.signal,
      ...opts,
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t || res.status);
    }
    return res.json();
  } catch (err) {
    if (err.name === "AbortError") throw new Error("Délai dépassé (70 s). Réessayez.");
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

function show(name) {
  $$(".view").forEach((v) => v.classList.remove("on"));
  const el = document.getElementById("view-" + name);
  if (el) el.classList.add("on");
  $$("nav button").forEach((b) => b.classList.toggle("on", b.dataset.view === name));
}

document.addEventListener("click", (e) => {
  const btn = e.target.closest("#main-nav [data-view], nav [data-view]");
  if (btn && btn.dataset.view === "nouveau") renderForm();
  if (e.target.closest("#back")) show("portefeuille");
});

async function boot() {
  try {
    const h = await api("/api/health");
    $("#health").textContent = `${h.database} · ${h.projets} projets · IA ${h.ia}`;
    $("#health").classList.add("ok");
  } catch {
    $("#health").textContent = "API indisponible";
  }
  const excelBtn = $("#excel-go");
  if (excelBtn) {
    excelBtn.onclick = async () => {
      const file = $("#excel-file").files[0];
      if (!file) { $("#excel-msg").textContent = "Choisissez un fichier .xlsx"; return; }
      const fd = new FormData();
      fd.append("file", file);
      $("#excel-msg").textContent = "Import…";
      try {
        const res = await fetch((window.BASE || "") + "/api/import/excel", { method: "POST", body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "erreur");
        $("#excel-msg").textContent = `${data.imported} projet(s) importé(s)`;
        await loadProjets();
      } catch (err) {
        $("#excel-msg").textContent = "Erreur : " + err.message;
      }
    };
  }
  await loadProjets();
}

async function loadProjets() {
  try {
    state.projets = await api("/api/projets");
  } catch (err) {
    $("#cards").innerHTML = `<p class="muted">Erreur : ${err.message}</p>`;
    return;
  }
  const types = ["tous", ...new Set(state.projets.map((p) => p.typologie))];
  $("#filters").innerHTML = types
    .map((t) => `<button data-f="${t}" class="${t === state.filter ? "on" : ""}">${t}</button>`)
    .join("");
  $$("#filters button").forEach((b) =>
    b.addEventListener("click", () => {
      state.filter = b.dataset.f;
      loadProjets();
    })
  );
  const list =
    state.filter === "tous"
      ? state.projets
      : state.projets.filter((p) => p.typologie === state.filter);
  $("#cards").innerHTML = list
    .map(
      (p) => `
    <article class="card" data-id="${p.id}">
      <div class="row">
        <span class="code">${p.code}</span>
        <span class="pill">${p.typologie}</span>
      </div>
      <h3>${p.nom}</h3>
      <div class="meta">${p.branche} · ${p.porteur_prenom || ""} ${p.porteur_nom || ""}</div>
      <div class="row card-score">
        <div>${scoreGauge(p.score_pertinence, 64)}</div>
        <div class="meta" style="text-align:right">
          ${euro(p.investissement_k_eur)}<br/>ROI ${p.roi_pct}%
        </div>
      </div>
      <span class="pill ${pillForReco(p.recommandation)}">${p.recommandation || p.statut}</span>
    </article>`
    )
    .join("");
  $$("#cards .card").forEach((c) =>
    c.addEventListener("click", () => openDossier(+c.dataset.id))
  );
}

function pillForReco(r = "") {
  if (/prioritaire/i.test(r)) return "go";
  if (/conditions|Réviser|Reviser/i.test(r)) return "warn";
  if (/NO-GO/i.test(r)) return "stop";
  return "";
}

async function openDossier(id) {
  show("dossier");
  $("#dossier").innerHTML = `<p class="wait">Chargement du dossier #${id}…</p>`;
  const b = await api("/api/projets/" + id);
  state.current = id;
  state.dossier = b;
  renderDossier(b);
  loadVersions(id);
}

function renderDossier(b) {
  const p = b.projet;
  const s = b.score;
  const dims = Object.values(s.dimensions || {});
  $("#dossier").innerHTML = `
    <div class="dossier-head">
      <div>
        <div class="code">${p.code} · ${p.typologie} · ${p.branche} · ${p.statut}</div>
        <h1>${p.nom}</h1>
        <p>${p.description || ""}</p>
        <div class="meta" style="color:#cdd6e4">
          Porteur : ${b.porteur.prenom || ""} ${b.porteur.nom || ""} · ${b.porteur.entite || ""}
          · maturité ${b.porteur.maturite || "–"}/5
        </div>
      </div>
      <div class="score-panel">
        ${scoreGauge(s.score, 100, true)}
        <div class="pill ${pillClass(s.go)}" style="margin-top:8px;display:inline-block">${s.recommandation}</div>
      </div>
    </div>

    <ol class="parcours">
      <li>Saisie des informations clés</li>
      <li>Score de pertinence calculé par l’IA</li>
      <li>Business plan généré</li>
      <li>Scénarios bas / médian / haut</li>
      <li>Note de synthèse Codir</li>
      <li>Téléchargement de la synthèse</li>
    </ol>
    <div class="actions">
      <button class="btn gold" id="btn-dossier">Tout enchaîner (parcours Codir)</button>
      <button class="btn" id="btn-evaluer">1. Score IA</button>
      <button class="btn" id="btn-analyse">2. Analyse</button>
      <button class="btn" id="btn-bp">3. Business plan</button>
      <button class="btn" id="btn-scen">4. Scénarios</button>
      <button class="btn" id="btn-note">5. Note Codir</button>
      <a class="btn ghost" href="${window.BASE || ""}/api/projets/${p.id}/export.txt">Télécharger la synthèse</a>
    </div>
    <p class="muted">Chaque bouton numéroté exécute un seul prompt. « Tout enchaîner » les lance dans l’ordre.</p>
    <p class="wait" id="status"></p>

    <div class="panel" style="margin-top:12px; border-left: 4px solid var(--gold);" id="versions-panel">
      <h2>Historique des versions</h2>
      <p class="muted">Chaque modification (utilisateur ou IA) crée une version. Vous pouvez revenir en arrière.</p>
      <div id="versions-list"><p class="muted">Chargement…</p></div>
    </div>

    <div class="layout">
      <div>
        <div class="panel">
          <h2>Dimensions du score</h2>
          <div class="bars">
            ${dims.map((d) => {
              const color = d.value >= 75 ? "#1f7a4d" : d.value >= 60 ? "#b86b00" : d.value >= 45 ? "#c47a12" : "#9b2335";
              return `
              <div class="bar-row">
                <span>${d.label}</span>
                <div class="track"><span style="width:${d.value}%;background:${color}"></span></div>
                <span class="num">${Math.round(d.value)}</span>
              </div>`;
            }).join("")}
          </div>
          <p class="hint">${s.formule}</p>
          <p class="muted">Ces notes ne sont pas saisies par le porteur. Elles sont attribuées par l’IA à partir du dossier, puis pondérées.</p>
        </div>
        <div class="panel" style="margin-top:12px">
          <h2>Hypothèses financières (k€)</h2>
          ${renderFinance(b.hypotheses)}
        </div>
        <div class="panel" style="margin-top:12px">
          <h2>Scénarios stockés</h2>
          ${renderScenarios(b.scenarios)}
        </div>
      </div>
      <div>
        <div class="panel">
          <h2>Paramètres stratégiques</h2>
          ${renderParams(b.parametres)}
        </div>
        <div class="panel" style="margin-top:12px">
          <h2>Risques du dossier</h2>
          <ul>${(b.risques || [])
            .filter((r) => r.projet_id)
            .map((r) => `<li><strong>${r.libelle}</strong> — ${r.categorie} (P${r.probabilite}/I${r.impact})</li>`)
            .join("") || "<li class='muted'>Aucun risque spécifique.</li>"}</ul>
        </div>
        <div class="panel" style="margin-top:12px">
          <h2>Modifier le descriptif</h2>
          <p class="muted">Édition directe par le manager. Une version est créée avant chaque enregistrement.</p>
          <div style="display:grid;gap:8px">
            <label>Nom <input id="edit-nom" value="${esc(p.nom || "")}" style="width:100%" /></label>
            <label>Description <textarea id="edit-desc" rows="4" style="width:100%">${esc(p.description || "")}</textarea></label>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <label>Investissement (k€) <input id="edit-inv" type="number" value="${p.investissement_k_eur ?? 0}" /></label>
              <label>ROI % <input id="edit-roi" type="number" value="${p.roi_pct ?? 0}" /></label>
              <label>CA an 3 (k€) <input id="edit-ca3" type="number" value="${p.ca_annee_3_k ?? 0}" /></label>
            </div>
            <button class="btn" id="btn-save">Enregistrer les modifications</button>
          </div>
        </div>
        <div class="panel" style="margin-top:12px">
          <h2>Dialogue d’ajustement</h2>
          <div class="chat">
            <input id="chat-in" placeholder="Ex. que se passe-t-il si le ROI tombe à 8 % ?" />
            <button class="btn" id="chat-go">Envoyer</button>
          </div>
          <div id="chat-out"></div>
        </div>
      </div>
    </div>

    <div class="panel" style="margin-top:16px" id="livrables">
      <h2>Livrables générés</h2>
      <p class="muted">Le parcours Codir évalue le score, rédige le business plan, propose les scénarios et produit la note téléchargeable.</p>
    </div>
  `;

  const setBusy = (msg) => ($("#status").textContent = msg || "");
  const run = async (path, payload) => {
    setBusy("Génération en cours…");
    try {
      const doc = await api(path, { method: "POST", body: JSON.stringify(payload || {}) });
      setBusy("Terminé (" + (doc.moteur || doc.analyse?.moteur || "ok") + ").");
      return doc;
    } catch (err) {
      setBusy("Erreur : " + err.message);
      throw err;
    }
  };

  $("#btn-dossier").onclick = async () => {
    const doc = await run(`/api/projets/${p.id}/dossier`, {});
    if (doc.score) state.dossier.score = doc.score;
    renderLivrables(doc);
    loadVersions(p.id);
  };
  $("#btn-evaluer").onclick = async () => {
    setBusy("Évaluation IA du score…");
    const fresh = await api(`/api/projets/${p.id}/evaluer`, { method: "POST", body: "{}" });
    renderDossier(fresh);
    loadVersions(p.id);
    $("#status").textContent = `Score recalculé : ${fresh.score.score}/100 (${fresh.evaluation?.moteur || "ok"}).`;
  };
  $("#btn-analyse").onclick = async () => {
    const doc = await run(`/api/projets/${p.id}/generer`, { type: "analyse" });
    renderLivrables({ analyse: doc });
  };
  $("#btn-bp").onclick = async () => {
    const doc = await run(`/api/projets/${p.id}/generer`, { type: "business_plan" });
    renderLivrables({ business_plan: doc });
  };
  $("#btn-scen").onclick = async () => {
    const doc = await run(`/api/projets/${p.id}/generer`, { type: "scenarios" });
    renderLivrables({ scenarios: doc });
  };
  $("#btn-note").onclick = async () => {
    const doc = await run(`/api/projets/${p.id}/generer`, { type: "note_codir" });
    renderLivrables({ note_codir: doc });
  };
  $("#chat-go").onclick = sendChat;
  $("#chat-in").addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendChat();
  });
  const saveBtn = $("#btn-save");
  if (saveBtn) {
    saveBtn.onclick = async () => {
      setBusy("Enregistrement…");
      try {
        const body = {
          nom: $("#edit-nom").value,
          description: $("#edit-desc").value,
          investissement_k_eur: Number($("#edit-inv").value) || 0,
          roi_pct: Number($("#edit-roi").value) || 0,
          ca_annee_3_k: Number($("#edit-ca3").value) || 0,
        };
        const fresh = await api(`/api/projets/${p.id}`, { method: "PUT", body: JSON.stringify(body) });
        state.dossier = fresh;
        renderDossier(fresh);
        loadVersions(p.id);
        $("#status").textContent = "Modifications enregistrées. Une version a été créée.";
      } catch (err) {
        setBusy("Erreur : " + err.message);
      }
    };
  }
}

async function loadVersions(pid) {
  const box = $("#versions-list");
  if (!box) return;
  try {
    const rows = await api(`/api/projets/${pid}/versions`);
    if (!rows.length) {
      box.innerHTML = `<p class="muted">Aucune version pour l’instant. Une version est créée avant chaque modification.</p>`;
      return;
    }
    box.innerHTML = `<table class="data"><thead><tr><th>Version</th><th>Source</th><th>Description</th><th>Date</th><th></th></tr></thead><tbody>
      ${rows.map((r) => `<tr>
        <td class="num">v${r.id}</td>
        <td>${r.source === "ia" ? "IA" : r.source === "user" ? "Utilisateur" : "Système"}</td>
        <td>${r.label || ""}</td>
        <td>${(r.created_at || "").replace("T", " ").slice(0, 16)}</td>
        <td><button class="btn ghost" data-vid="${r.id}">Restaurer</button></td>
      </tr>`).join("")}
    </tbody></table>`;
    $$("button[data-vid]", box).forEach((btn) => {
      btn.onclick = async () => {
        if (!confirm("Restaurer cette version ? L’état actuel sera conservé comme nouvelle version.")) return;
        const fresh = await api(`/api/projets/${pid}/versions/${btn.dataset.vid}/restore`, { method: "POST", body: "{}" });
        renderDossier(fresh);
        loadVersions(pid);
        $("#status").textContent = `Version v${btn.dataset.vid} restaurée.`;
      };
    });
  } catch (err) {
    box.innerHTML = `<p class="muted">Impossible de charger l’historique.</p>`;
  }
}

async function sendChat() {
  const input = $("#chat-in");
  const msg = input.value.trim();
  if (!msg) return;
  input.value = "";
  $("#chat-out").innerHTML = `<p class="wait">…</p>`;
  try {
    const doc = await api(`/api/projets/${state.current}/chat`, {
      method: "POST",
      body: JSON.stringify({ message: msg }),
    });
    const props = (doc.propositions || [])
      .map((p) => {
        if (p.type === "montant" || p.champ && p.champ !== "description") {
          return `<li><strong>${esc(p.champ)}</strong> → ${esc(p.valeur_suggeree || "–")}<br/><span class="muted">${esc(p.effet_attendu || "")}</span></li>`;
        }
        return `<li><strong>À ajouter à la description</strong> : ${esc(p.extrait_a_ajouter || "")}<br/><span class="muted">${esc(p.effet_attendu || "")}</span></li>`;
      })
      .join("");
    const text = doc.reponse || doc.analyse || "";
    const impact = doc.impact_score || doc.impact_attendu || "";
    $("#chat-out").innerHTML = `<div class="bubble">${esc(text)}${props ? `<ul>${props}</ul>` : ""}<div class="muted">${esc(impact)} · ${esc((doc.limites || [])[0] || doc.moteur || "")}</div></div>`;
  } catch (err) {
    $("#chat-out").innerHTML = `<div class="bubble">${esc(err.message)}</div>`;
  }
}

function renderFinance(rows) {
  if (!rows || !rows.length) return "<p class='muted'>Pas d’hypothèses.</p>";
  const depenses = rows.map((r) => Number(r.total_depenses_k) || 0);
  const recettes = rows.map((r) => Number(r.chiffre_affaires_k) || 0);
  const labels = rows.map((r) => "N+" + r.annee);
  const chart = miniBars(
    [...depenses, ...recettes],
    [...labels.map((l) => l + " D"), ...labels.map((l) => l + " R")],
    [...depenses.map(() => "#9b2335"), ...recettes.map(() => "#1f7a4d")]
  );
  const keys = [
    ["annee", "Année"],
    ["total_depenses_k", "Dépenses"],
    ["chiffre_affaires_k", "Recettes"],
    ["ebe_k", "EBE"],
    ["resultat_exploitation_k", "REX"],
    ["tresorerie_k", "Trésorerie"],
  ];
  return `${chart}
    <table class="data"><thead><tr>${keys.map((k) => `<th>${k[1]}</th>`).join("")}</tr></thead><tbody>
    ${rows.map((r) => `<tr>${keys.map(([k]) => `<td class="${k === "annee" ? "" : "num"}">${k === "annee" ? "N+" + r[k] : euro(r[k])}</td>`).join("")}</tr>`).join("")}
  </tbody></table>`;
}

function renderScenarios(rows) {
  if (!rows || !rows.length) return "<p class='muted'>Pas de scénarios.</p>";
  const order = ["bas", "median", "haut"];
  const sorted = [...rows].sort((a, b) => order.indexOf(a.type_scenario) - order.indexOf(b.type_scenario));
  const ca = sorted.map((r) => Number(r.ca_3ans_k) || 0);
  const labels = sorted.map((r) => r.type_scenario);
  const colors = ["#9b2335", "#b86b00", "#1f7a4d"];
  const chart = miniBars(ca, labels, colors);
  return `${chart}
    <table class="data"><thead><tr><th>Scénario</th><th>CA 3 ans</th><th>Résultat 3 ans</th><th>ROI</th></tr></thead><tbody>
    ${sorted.map((r) => `<tr>
          <td>${r.type_scenario}</td>
          <td class="num">${euro(r.ca_3ans_k)}</td>
          <td class="num">${euro(r.resultat_3ans_k)}</td>
          <td class="num">${r.roi_pct} %</td>
        </tr><tr><td colspan="4" class="muted">${esc(r.hypotheses || "")}</td></tr>`).join("")}
  </tbody></table>`;
}

function renderParams(pr) {
  if (!pr || !pr.priorite_groupe) return "<p class='muted'>Aucun paramètre.</p>";
  return `
    <p><strong>Priorité Groupe.</strong> ${esc(pr.priorite_groupe)}</p>
    <p><strong>Avantage.</strong> ${esc(pr.avantage_concurrentiel || "")}</p>
    <p><strong>Marché.</strong> ${esc(pr.opportunite_marche || "")}</p>
    <p><strong>KPI.</strong> ${esc(pr.kpis || "")}</p>
    <p><strong>Dépendances.</strong> ${esc(pr.dependances || "")}</p>`;
}

function renderLivrables(doc) {
  const root = $("#livrables");
  const first = doc.evaluation ? "eval" : doc.analyse ? "analyse" : doc.business_plan ? "bp" : "note";
  let html = `<div class="tabs">
    ${doc.evaluation ? `<button data-t="eval" class="${first === "eval" ? "on" : ""}">Score IA</button>` : ""}
    ${doc.analyse ? `<button data-t="analyse" class="${first === "analyse" ? "on" : ""}">Analyse</button>` : ""}
    ${doc.business_plan ? `<button data-t="bp">Business plan</button>` : ""}
    ${doc.scenarios ? `<button data-t="sc">Scénarios IA</button>` : ""}
    ${doc.note_codir ? `<button data-t="note">Note Codir</button>` : ""}
  </div>`;
  if (doc.evaluation) html += `<div class="pane" id="pane-eval" ${first === "eval" ? "" : "hidden"}>${renderEvaluation(doc.evaluation)}</div>`;
  if (doc.analyse) html += `<div class="pane" id="pane-analyse" ${first === "analyse" ? "" : "hidden"}>${renderAnalyse(doc.analyse)}</div>`;
  if (doc.business_plan) html += `<div class="pane" id="pane-bp" hidden>${renderBP(doc.business_plan)}</div>`;
  if (doc.scenarios) html += `<div class="pane" id="pane-sc" hidden>${renderScenIA(doc.scenarios)}</div>`;
  if (doc.note_codir) html += `<div class="pane" id="pane-note" hidden>${renderNote(doc.note_codir)}</div>`;
  root.innerHTML = html;
  $$(".tabs button", root).forEach((b) => {
    b.onclick = () => {
      $$(".tabs button", root).forEach((x) => x.classList.remove("on"));
      b.classList.add("on");
      const map = { eval: "pane-eval", analyse: "pane-analyse", bp: "pane-bp", sc: "pane-sc", note: "pane-note" };
      $$(".pane", root).forEach((p) => (p.hidden = p.id !== map[b.dataset.t]));
    };
  });
}

function renderEvaluation(ev) {
  if (!ev) return "";
  const keys = [
    ["alignement_groupe", "Alignement Groupe"],
    ["impact_branches", "Impact branches"],
    ["complexite_operationnelle", "Complexité"],
    ["maturite_technique", "Maturité technique"],
    ["impact_social", "Impact social"],
    ["impact_environnemental", "Impact environnemental"],
    ["risque_technique", "Risque technique"],
    ["risque_humain", "Risque humain"],
    ["risque_reglementaire", "Risque réglementaire"],
  ];
  const just = ev.justifications || {};
  return `<p class="muted">Notes IA 1–5 · moteur ${esc(ev.moteur || "")}. Le 0–100 est calculé ensuite.</p>
    <ul>${keys.map(([k, lab]) => `<li><strong>${lab} : ${ev[k] ?? "–"}/5.</strong> ${esc(just[k] || "")}</li>`).join("")}</ul>`;
}

function renderAnalyse(a) {
  return `
    <p class="muted">Moteur ${a.moteur || "n.d."}</p>
    <div class="layout">
      <div>
        <h3>Forces</h3>
        <ul>${(a.forces || []).map((f) => `<li><strong>${esc(f.titre)}</strong> — ${esc(f.preuve)}</li>`).join("")}</ul>
        <h3>Faiblesses</h3>
        <ul>${(a.faiblesses || []).map((f) => `<li><strong>${esc(f.titre)}</strong> — ${esc(f.preuve)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>Risques clés</h3>
        <ul>${(a.risques_cles || []).map((r) => `<li>${esc(r.libelle)} (criticité ${r.criticite}) — ${esc(r.mitigation || "")}</li>`).join("")}</ul>
        <h3>Vigilance Codir</h3>
        <ul>${(a.points_de_vigilance_codir || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
      </div>
    </div>`;
}

function renderBP(bp) {
  const s = bp.sections || {};
  const block = (title, body) => `<div class="bp-sec"><h3>${title}</h3>${body}</div>`;
  const list = (arr) => `<ul>${(arr || []).map((x) => `<li>${esc(typeof x === "string" ? x : JSON.stringify(x))}</li>`).join("")}</ul>`;
  return `
    ${block("1. Résumé exécutif", `<p>${esc(s.resume_executif?.texte || "")}</p><span class="pill">${esc(s.resume_executif?.go_suggere || "")}</span>`)}
    ${block("2. Description", `<p>${esc(s.description_projet?.contexte || "")}</p>${list(s.description_projet?.objectifs)}`)}
    ${block("3. Analyse stratégique", `<p>${esc(s.analyse_strategique?.alignement || "")}</p><p>${esc(s.analyse_strategique?.avantage || "")}</p>`)}
    ${block("4. Marché", `<p>${esc(s.analyse_marche?.cible || "")}</p>`)}
    ${block("5. Concurrentiel", list(s.analyse_concurrentielle?.facteurs_differenciants))}
    ${block("6. Modèle économique", `<p>${esc(s.modele_economique?.logique_de_valeur || "")}</p>`)}
    ${block("7. Hypothèses", `<p>${esc(s.hypotheses_financieres?.commentaire || "")}</p>`)}
    ${block("8. Scénarios", `<p>${esc(s.scenarios?.commentaire_transversal || "")}</p>`)}
    ${block("9. Plan d’action", list(s.plan_action?.jalons_90_jours) + list(s.plan_action?.jalons_12_mois))}
    ${block("10. Synthèse Codir", `<p><strong>${esc(s.synthese_codir?.en_une_phrase || "")}</strong></p>`)}
  `;
}

function renderScenIA(sc) {
  return (sc.scenarios || [])
    .map(
      (s) => `<div class="bp-sec"><h3>Scénario ${esc(s.type_scenario)} · p=${esc(s.probabilite_qualitative || "")}</h3>
        <p>${esc(s.narratif || "")}</p>${(s.conditions || []).map((c) => `<div class="muted">${esc(c)}</div>`).join("")}</div>`
    )
    .join("") + `<p class="hint">Référence Codir : ${esc(sc.scenario_de_reference_codir || "median")} — ${esc(sc.justification_reference || "")}</p>`;
}

function renderNote(n) {
  return `
    <div class="note">
      <div class="muted">${esc(n.en_tete?.objet || "")} · ${esc(n.en_tete?.classification || "")}</div>
      <h3>Essentiel</h3>
      <ul>${(n.essentiel_en_5_lignes || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
      <h3>Pour</h3>
      <ul>${(n.arguments_pour || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
      <h3>Contre</h3>
      <ul>${(n.arguments_contre || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
      <p><strong>Risque principal.</strong> ${esc(n.risque_principal || "")}</p>
      <p><strong>Condition suspensive.</strong> ${esc(n.condition_suspensive || "")}</p>
      <p><strong>Décision proposée.</strong> ${esc(n.decision_proposee || "")}</p>
      <p><strong>Prochaine étape.</strong> ${esc(n.prochaine_etape || "")}</p>
    </div>`;
}

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&")
    .replaceAll("<", "<")
    .replaceAll(">", ">");
}

function renderForm() {
  $("#form-projet").innerHTML = `
    <div class="form-grid">
      <label>Code<input name="code" required placeholder="BP-XXX-09" /></label>
      <label>Nom<input name="nom" required placeholder="Nom du projet" /></label>
      <label>Typologie
        <select name="typologie">
          <option>innovation</option><option>RH</option><option>digital</option>
          <option>logistique</option><option>territorial</option><option>RSE</option><option>client</option>
        </select>
      </label>
      <label>Branche
        <select name="branche">
          <option>Groupe</option><option>Courrier</option><option>Colis</option>
          <option>Réseau</option><option>Numérique</option><option>Banque</option>
        </select>
      </label>
      <label>Porteur (id)<input name="porteur_id" type="number" value="8" /></label>
      <label>Durée (mois)<input name="duree_mois" type="number" value="18" /></label>
      <label>Investissement k€<input name="investissement_k_eur" type="number" value="750" /></label>
      <label>CA année 1 k€<input name="ca_annee_1_k" type="number" value="120" /></label>
      <label>CA année 3 k€<input name="ca_annee_3_k" type="number" value="1800" /></label>
      <label>ROI estimé %<input name="roi_pct" type="number" step="0.1" value="15" /></label>
      <label>Délai de retour (mois)<input name="delai_retour_mois" type="number" value="24" /></label>
    </div>
    <label>Description du projet<textarea name="description" placeholder="Contexte, objectif, périmètre, valeur attendue…"></textarea></label>
    <label>Alignement / priorité Groupe perçue<textarea name="priorite_groupe" placeholder="En quoi le projet sert une priorité Groupe ?"></textarea></label>
    <label>Avantage et opportunité de marché<textarea name="opportunite_marche" placeholder="Cible, alternative interne, différenciation…"></textarea></label>
    <button class="btn gold" type="submit">Enregistrer — l’IA calcule le score</button>
    <p class="hint" id="form-msg"></p>
  `;
  $("#form-projet").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    ["porteur_id","duree_mois","delai_retour_mois"].forEach((k) => (body[k] = Number(body[k])));
    ["investissement_k_eur","ca_annee_1_k","ca_annee_3_k","roi_pct"].forEach(
      (k) => (body[k] = Number(body[k]))
    );
    body.parametres = {
      priorite_groupe: body.priorite_groupe || "",
      opportunite_marche: body.opportunite_marche || "",
    };
    delete body.priorite_groupe;
    delete body.opportunite_marche;
    body.hypotheses = [1, 2, 3].map((annee) => ({
      annee,
      postes_salaires_k: Math.round(body.investissement_k_eur * (annee === 1 ? 0.35 : 0.2)),
      logiciel_k: Math.round(body.investissement_k_eur * 0.08),
      recette_p1_k: Math.round((body.ca_annee_1_k || 0) * annee * 0.7),
      recette_p2_k: Math.round((body.ca_annee_1_k || 0) * annee * 0.2),
    }));
    body.scenarios = [
      { type_scenario: "bas", ca_3ans_k: body.ca_annee_3_k * 0.45, resultat_3ans_k: -body.investissement_k_eur * 0.2, roi_pct: Math.max(body.roi_pct - 10, -5), hypotheses: "Adoption basse." },
      { type_scenario: "median", ca_3ans_k: body.ca_annee_3_k, resultat_3ans_k: body.ca_annee_3_k * 0.1 - body.investissement_k_eur * 0.3, roi_pct: body.roi_pct, hypotheses: "Hypothèses porteur." },
      { type_scenario: "haut", ca_3ans_k: body.ca_annee_3_k * 1.5, resultat_3ans_k: body.ca_annee_3_k * 0.25, roi_pct: body.roi_pct + 10, hypotheses: "Adoption haute." },
    ];
    $("#form-msg").textContent = "Enregistrement…";
    try {
      const created = await api("/api/projets", { method: "POST", body: JSON.stringify(body) });
      $("#form-msg").textContent = `Créé · score ${created.score.score}/100`;
      await loadProjets();
      openDossier(created.projet.id);
    } catch (err) {
      $("#form-msg").textContent = "Erreur : " + err.message;
    }
  };
}

boot();
