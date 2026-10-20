#!/usr/bin/env python3
"""PostePlan IA — PoC Executive MBA Epitech P2026.

Chaîne démontrée :
  saisie / sélection projet → score 0-100 → MySQL → génération BP / note Codir → export.
"""

from __future__ import annotations

import io
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory, Response
from openpyxl import Workbook, load_workbook

import ai_service
import db
from scoring import RATING_FIELDS, apply_ai_ratings, compute_score

import os
ROOT = Path(__file__).resolve().parent
PREFIX = os.environ.get("URL_PREFIX", "").rstrip("/")  # ex. /bp-laposte
app = Flask(__name__, static_folder=str(ROOT / "static"), template_folder=str(ROOT / "templates"))
app.config["APPLICATION_ROOT"] = PREFIX or "/"


def _json(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json(v) for v in value]
    return value


def bundle(projet_id: int) -> dict | None:
    projets = db.q(
        """
        SELECT p.*, po.nom AS porteur_nom, po.prenom AS porteur_prenom,
               po.entite AS porteur_entite, po.fonction AS porteur_fonction,
               po.maturite AS porteur_maturite, po.email AS porteur_email
        FROM projets p
        LEFT JOIN porteurs po ON po.id = p.porteur_id
        WHERE p.id = %s
        """,
        (projet_id,),
    )
    if not projets:
        return None
    p = _json(projets[0])
    hypos = _json(db.q(
        "SELECT * FROM hypotheses_financieres WHERE projet_id = %s ORDER BY annee",
        (projet_id,),
    ))
    for h in hypos:
        h["total_depenses_k"] = round(sum(float(h.get(k) or 0) for k in (
            "postes_salaires_k", "materiel_k", "logiciel_k", "charges_fiscales_k",
            "frais_admin_k", "autres_depenses_k",
        )), 2)
        h["chiffre_affaires_k"] = round(sum(float(h.get(k) or 0) for k in (
            "recette_p1_k", "recette_p2_k", "recette_p3_k",
        )), 2)
    params_rows = _json(db.q(
        "SELECT * FROM parametres_strategiques WHERE projet_id = %s", (projet_id,)
    ))
    risques = _json(db.q(
        "SELECT * FROM risques WHERE projet_id = %s OR projet_id IS NULL ORDER BY projet_id IS NULL, id",
        (projet_id,),
    ))
    opps = _json(db.q(
        "SELECT * FROM opportunites WHERE projet_id = %s OR projet_id IS NULL ORDER BY projet_id IS NULL, id",
        (projet_id,),
    ))
    scenarios = _json(db.q(
        "SELECT * FROM scenarios WHERE projet_id = %s ORDER BY FIELD(type_scenario,'bas','median','haut')",
        (projet_id,),
    ))
    # SQLite n'a pas FIELD() — fallback
    if scenarios is None:
        scenarios = []
    score = compute_score(p)
    return {
        "projet": p,
        "porteur": {
            "nom": p.get("porteur_nom"),
            "prenom": p.get("porteur_prenom"),
            "entite": p.get("porteur_entite"),
            "fonction": p.get("porteur_fonction"),
            "email": p.get("porteur_email"),
            "maturite": p.get("porteur_maturite"),
        },
        "hypotheses": hypos,
        "parametres": params_rows[0] if params_rows else {},
        "risques": risques,
        "opportunites": opps,
        "scenarios": scenarios,
        "score": score,
        "moteur_db": db.ENGINE["name"],
    }


def _adapt_sql(sql: str) -> str:
    if db.ENGINE["name"] == "sqlite":
        sql = sql.replace("%s", "?")
        sql = sql.replace(
            "ORDER BY FIELD(type_scenario,'bas','median','haut')",
            "ORDER BY CASE type_scenario WHEN 'bas' THEN 1 WHEN 'median' THEN 2 ELSE 3 END",
        )
        sql = sql.replace("projet_id IS NULL ORDER BY projet_id IS NULL, id",
                          "projet_id IS NULL ORDER BY (projet_id IS NULL), id")
    return sql


# Monkey-patch db.q/x to adapt placeholders based on engine
_orig_q, _orig_x = db.q, db.x


def q(sql, params=None):
    return _orig_q(_adapt_sql(sql), params)


def x(sql, params=None):
    return _orig_x(_adapt_sql(sql), params)


db.q = q
db.x = x


@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,OPTIONS"
    return resp


@app.route("/")
@app.route(f"{PREFIX}/")
def index():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    base = PREFIX or ""
    html = html.replace('href="/static/', f'href="{base}/static/')
    html = html.replace('src="/static/', f'src="{base}/static/')
    html = html.replace('href="/api/', f'href="{base}/api/')
    html = html.replace("</head>", f'<script>window.BASE="{base}";</script></head>')
    return Response(html, mimetype="text/html")


@app.route("/api/health")
def health():
    n = db.q("SELECT COUNT(*) AS n FROM projets")[0]["n"]
    return jsonify({
        "ok": True,
        "database": db.ENGINE["name"],
        "projets": n,
        "ia": ai_service.preferred_provider(),
        "ia_disponibles": ai_service.configured_providers(),
    })


@app.route("/api/porteurs")
def porteurs():
    return jsonify(_json(db.q("SELECT * FROM porteurs ORDER BY nom")))


@app.route("/api/catalogue/risques")
def cat_risques():
    return jsonify(_json(db.q("SELECT * FROM risques WHERE projet_id IS NULL")))


@app.route("/api/catalogue/opportunites")
def cat_opps():
    return jsonify(_json(db.q("SELECT * FROM opportunites WHERE projet_id IS NULL")))


@app.route("/api/projets")
def liste_projets():
    rows = _json(db.q(
        """
        SELECT p.id, p.code, p.nom, p.typologie, p.branche, p.statut,
               p.investissement_k_eur, p.roi_pct, p.delai_retour_mois,
               p.score_pertinence, p.duree_mois,
               po.prenom AS porteur_prenom, po.nom AS porteur_nom, po.entite AS porteur_entite
        FROM projets p
        LEFT JOIN porteurs po ON po.id = p.porteur_id
        ORDER BY p.id
        """
    ))
    # Recalcule le score à la volée pour rester cohérent
    for r in rows:
        full = db.q("SELECT p.*, po.maturite AS porteur_maturite FROM projets p LEFT JOIN porteurs po ON po.id = p.porteur_id WHERE p.id = %s", (r["id"],))
        if full:
            r["score_pertinence"] = compute_score(_json(full[0]))["score"]
            r["recommandation"] = compute_score(_json(full[0]))["recommandation"]
    return jsonify(rows)


@app.route("/api/projets/<int:pid>")
def get_projet(pid):
    b = bundle(pid)
    if not b:
        return jsonify({"error": "projet introuvable"}), 404
    return jsonify(b)


@app.route("/api/import/excel", methods=["POST"])
def import_excel():
    """Importe des projets depuis un fichier Excel (colonnes : code, nom, typologie, branche, description, investissement_k_eur, ca_annee_1_k, ca_annee_3_k, roi_pct, delai_retour_mois, duree_mois)."""
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "fichier manquant"}), 400
    try:
        wb = load_workbook(f, data_only=True)
        ws = wb.active
        headers = [str(c.value or "").strip().lower() for c in next(ws.iter_rows(min_row=1, max_row=1))]
        created = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            data = dict(zip(headers, row))
            code = str(data.get("code") or "").strip()
            nom = str(data.get("nom") or "").strip()
            if not code or not nom:
                continue
            existing = db.q("SELECT id FROM projets WHERE code = %s", (code,))
            if existing:
                continue
            pid = db.x(
                """INSERT INTO projets (code, nom, typologie, branche, description, duree_mois, statut,
                   investissement_k_eur, ca_annee_1_k, ca_annee_3_k, roi_pct, delai_retour_mois)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (code, nom,
                 str(data.get("typologie") or "innovation"),
                 str(data.get("branche") or "Groupe"),
                 str(data.get("description") or ""),
                 int(data.get("duree_mois") or 18),
                 "brouillon",
                 float(data.get("investissement_k_eur") or 0),
                 float(data.get("ca_annee_1_k") or 0),
                 float(data.get("ca_annee_3_k") or 0),
                 float(data.get("roi_pct") or 0),
                 int(data.get("delai_retour_mois") or 24)),
            )
            if pid:
                created.append({"id": pid, "code": code, "nom": nom})
        return jsonify({"imported": len(created), "projets": created})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/import/modele.xlsx")
def modele_excel():
    """Télécharge un modèle Excel d’import."""
    wb = Workbook()
    ws = wb.active
    ws.title = "projets"
    cols = ["code", "nom", "typologie", "branche", "description", "duree_mois",
            "investissement_k_eur", "ca_annee_1_k", "ca_annee_3_k", "roi_pct", "delai_retour_mois"]
    ws.append(cols)
    ws.append(["BP-EX-09", "Exemple projet", "innovation", "Groupe", "Description courte", 18, 500, 100, 1200, 15, 24])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="modele_projets.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")



@app.route("/api/projets", methods=["POST"])
def create_projet():
    body = request.get_json(force=True, silent=True) or {}
    required = ["code", "nom", "typologie", "branche"]
    missing = [k for k in required if not body.get(k)]
    if missing:
        return jsonify({"error": "champs manquants", "champs": missing}), 400

    def g(key, default=None):
        return body.get(key, default)

    pid = db.x(
        """
        INSERT INTO projets (
          code, nom, typologie, branche, description, porteur_id, date_creation,
          duree_mois, statut, alignement_groupe, impact_branches, complexite_operationnelle,
          maturite_technique, impact_social, impact_environnemental, risque_technique,
          risque_humain, risque_reglementaire, investissement_k_eur, ca_annee_1_k,
          ca_annee_3_k, roi_pct, delai_retour_mois
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            g("code"), g("nom"), g("typologie"), g("branche"), g("description", ""),
            g("porteur_id"), g("date_creation", date.today().isoformat()),
            int(g("duree_mois", 18)), g("statut", "brouillon"),
            int(g("alignement_groupe", 3)), int(g("impact_branches", 3)),
            int(g("complexite_operationnelle", 3)), int(g("maturite_technique", 3)),
            int(g("impact_social", 3)), int(g("impact_environnemental", 3)),
            int(g("risque_technique", 3)), int(g("risque_humain", 3)),
            int(g("risque_reglementaire", 3)),
            float(g("investissement_k_eur", 0)), float(g("ca_annee_1_k", 0)),
            float(g("ca_annee_3_k", 0)), float(g("roi_pct", 0)),
            int(g("delai_retour_mois", 24)),
        ),
    )
    # SQLite lastrowid / MySQL
    if not pid:
        row = db.q("SELECT id FROM projets WHERE code = %s", (g("code"),))
        pid = row[0]["id"] if row else None

    for h in body.get("hypotheses") or []:
        db.x(
            """
            INSERT INTO hypotheses_financieres (
              projet_id, annee, postes_salaires_k, materiel_k, logiciel_k,
              charges_fiscales_k, frais_admin_k, autres_depenses_k, nb_clients,
              recette_p1_k, recette_p2_k, recette_p3_k, marge_brute_pct,
              ebe_k, resultat_exploitation_k, bfr_k, tresorerie_k
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                pid, int(h.get("annee", 1)),
                float(h.get("postes_salaires_k", 0)), float(h.get("materiel_k", 0)),
                float(h.get("logiciel_k", 0)), float(h.get("charges_fiscales_k", 0)),
                float(h.get("frais_admin_k", 0)), float(h.get("autres_depenses_k", 0)),
                int(h.get("nb_clients", 0)),
                float(h.get("recette_p1_k", 0)), float(h.get("recette_p2_k", 0)),
                float(h.get("recette_p3_k", 0)), float(h.get("marge_brute_pct", 0)),
                float(h.get("ebe_k", 0)), float(h.get("resultat_exploitation_k", 0)),
                float(h.get("bfr_k", 0)), float(h.get("tresorerie_k", 0)),
            ),
        )
    if body.get("parametres"):
        pr = body["parametres"]
        db.x(
            """
            INSERT INTO parametres_strategiques
              (projet_id, priorite_groupe, avantage_concurrentiel, opportunite_marche, kpis, dependances)
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (pid, pr.get("priorite_groupe"), pr.get("avantage_concurrentiel"),
             pr.get("opportunite_marche"), pr.get("kpis"), pr.get("dependances")),
        )
    for s in body.get("scenarios") or []:
        db.x(
            """
            INSERT INTO scenarios (projet_id, type_scenario, ca_3ans_k, resultat_3ans_k, roi_pct, hypotheses)
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (pid, s.get("type_scenario"), float(s.get("ca_3ans_k", 0)),
             float(s.get("resultat_3ans_k", 0)), float(s.get("roi_pct", 0)), s.get("hypotheses")),
        )

    b = bundle(pid)
    evaluation, _score = _evaluer_et_sauver(pid, b)
    fresh = bundle(pid)
    fresh["evaluation"] = evaluation
    return jsonify(fresh), 201


def _snapshot(pid: int, source: str = "user", label: str = None):
    """Enregistre l'état complet du projet (données + score) avant une modification."""
    b = bundle(pid)
    if not b:
        return None
    snap = {
        "projet": b["projet"],
        "hypotheses": b.get("hypotheses") or [],
        "parametres": b.get("parametres") or {},
        "scenarios": b.get("scenarios") or [],
        "score": b.get("score") or {},
    }
    vid = db.x(
        "INSERT INTO versions (projet_id, source, label, snapshot_json) VALUES (%s,%s,%s,%s)",
        (pid, source, label or "", json.dumps(snap, ensure_ascii=False, default=str)),
    )
    if not vid:
        row = db.q("SELECT id FROM versions WHERE projet_id = %s ORDER BY id DESC LIMIT 1", (pid,))
        vid = row[0]["id"] if row else None
    return vid


def _restore(pid: int, vid: int):
    """Restaure un projet à partir d'un snapshot."""
    rows = db.q(
        "SELECT snapshot_json FROM versions WHERE id = %s AND projet_id = %s",
        (vid, pid),
    )
    if not rows:
        return None
    snap = json.loads(rows[0]["snapshot_json"])
    p = snap.get("projet") or {}
    fields = [
        "nom", "typologie", "branche", "description", "duree_mois", "statut",
        "alignement_groupe", "impact_branches", "complexite_operationnelle", "maturite_technique",
        "impact_social", "impact_environnemental", "risque_technique", "risque_humain",
        "risque_reglementaire", "investissement_k_eur", "ca_annee_1_k", "ca_annee_3_k",
        "roi_pct", "delai_retour_mois", "score_pertinence",
    ]
    sets = ", ".join(f"{k} = %s" for k in fields)
    db.x(
        f"UPDATE projets SET {sets} WHERE id = %s",
        tuple(p.get(k) for k in fields) + (pid,),
    )
    # Restaure hypothèses
    db.x("DELETE FROM hypotheses_financieres WHERE projet_id = %s", (pid,))
    for h in snap.get("hypotheses") or []:
        db.x(
            """INSERT INTO hypotheses_financieres (
              projet_id, annee, postes_salaires_k, materiel_k, logiciel_k,
              charges_fiscales_k, frais_admin_k, autres_depenses_k, nb_clients,
              recette_p1_k, recette_p2_k, recette_p3_k, marge_brute_pct,
              ebe_k, resultat_exploitation_k, bfr_k, tresorerie_k
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (pid, h.get("annee", 1),
             h.get("postes_salaires_k", 0), h.get("materiel_k", 0), h.get("logiciel_k", 0),
             h.get("charges_fiscales_k", 0), h.get("frais_admin_k", 0), h.get("autres_depenses_k", 0),
             h.get("nb_clients", 0), h.get("recette_p1_k", 0), h.get("recette_p2_k", 0), h.get("recette_p3_k", 0),
             h.get("marge_brute_pct", 0), h.get("ebe_k", 0), h.get("resultat_exploitation_k", 0),
             h.get("bfr_k", 0), h.get("tresorerie_k", 0)),
        )
    # Restaure paramètres
    db.x("DELETE FROM parametres_strategiques WHERE projet_id = %s", (pid,))
    pr = snap.get("parametres") or {}
    if pr:
        db.x(
            """INSERT INTO parametres_strategiques
               (projet_id, priorite_groupe, avantage_concurrentiel, opportunite_marche, kpis, dependances)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (pid, pr.get("priorite_groupe"), pr.get("avantage_concurrentiel"),
             pr.get("opportunite_marche"), pr.get("kpis"), pr.get("dependances")),
        )
    # Restaure scénarios
    db.x("DELETE FROM scenarios WHERE projet_id = %s", (pid,))
    for s in snap.get("scenarios") or []:
        db.x(
            """INSERT INTO scenarios (projet_id, type_scenario, ca_3ans_k, resultat_3ans_k, roi_pct, hypotheses)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (pid, s.get("type_scenario"), s.get("ca_3ans_k", 0),
             s.get("resultat_3ans_k", 0), s.get("roi_pct", 0), s.get("hypotheses")),
        )
    return bundle(pid)


@app.route("/api/projets/<int:pid>", methods=["PUT"])
def update_projet(pid):
    body = request.get_json(force=True, silent=True) or {}
    _snapshot(pid, source="user", label="Avant modification utilisateur")
    allowed = [
        "nom", "typologie", "branche", "description", "porteur_id", "duree_mois", "statut",
        "alignement_groupe", "impact_branches", "complexite_operationnelle", "maturite_technique",
        "impact_social", "impact_environnemental", "risque_technique", "risque_humain",
        "risque_reglementaire", "investissement_k_eur", "ca_annee_1_k", "ca_annee_3_k",
        "roi_pct", "delai_retour_mois",
    ]
    fields, vals = [], []
    for k in allowed:
        if k in body:
            fields.append(f"{k} = %s")
            vals.append(body[k])
    if fields:
        vals.append(pid)
        db.x(f"UPDATE projets SET {', '.join(fields)} WHERE id = %s", tuple(vals))
    b = bundle(pid)
    if not b:
        return jsonify({"error": "projet introuvable"}), 404
    db.x("UPDATE projets SET score_pertinence = %s WHERE id = %s", (b["score"]["score"], pid))
    b = bundle(pid)
    return jsonify(b)


def _evaluer_et_sauver(pid: int, b: dict):
    """L'IA note les dimensions ; le moteur calcule le 0–100 ; on persiste."""
    _snapshot(pid, source="ia", label="Avant évaluation IA")
    evaluation = ai_service.generate("evaluation", b)
    ratings = {k: evaluation.get(k) for k in RATING_FIELDS}
    updated = apply_ai_ratings(b["projet"], ratings)
    sets = ", ".join(f"{k} = %s" for k in RATING_FIELDS)
    db.x(
        f"UPDATE projets SET {sets} WHERE id = %s",
        tuple(updated[k] for k in RATING_FIELDS) + (pid,),
    )
    score = compute_score(updated)
    db.x("UPDATE projets SET score_pertinence = %s WHERE id = %s", (score["score"], pid))
    _save_generation(pid, "evaluation", evaluation)
    return evaluation, score


@app.route("/api/projets/<int:pid>/evaluer", methods=["POST"])
def evaluer(pid):
    b = bundle(pid)
    if not b:
        return jsonify({"error": "projet introuvable"}), 404
    evaluation, _score = _evaluer_et_sauver(pid, b)
    fresh = bundle(pid)
    fresh["evaluation"] = evaluation
    return jsonify(fresh)


@app.route("/api/projets/<int:pid>/score")
def api_score(pid):
    b = bundle(pid)
    if not b:
        return jsonify({"error": "projet introuvable"}), 404
    db.x("UPDATE projets SET score_pertinence = %s WHERE id = %s", (b["score"]["score"], pid))
    return jsonify(b["score"])


def _save_generation(pid: int, kind: str, doc: dict) -> int:
    """Enregistre une génération et renvoie son id (version)."""
    moteur = doc.get("moteur", "fallback")
    gid = db.x(
        "INSERT INTO generations (projet_id, type_doc, moteur, contenu_json) VALUES (%s,%s,%s,%s)",
        (pid, kind, moteur, json.dumps(doc, ensure_ascii=False)),
    )
    if not gid:
        row = db.q(
            "SELECT id FROM generations WHERE projet_id = %s AND type_doc = %s ORDER BY id DESC LIMIT 1",
            (pid, kind),
        )
        gid = row[0]["id"] if row else None
    doc["_generation_id"] = gid
    return gid


@app.route("/api/projets/<int:pid>/versions")
def list_versions(pid):
    rows = _json(db.q(
        "SELECT id, source, label, created_at FROM versions WHERE projet_id = %s ORDER BY id DESC",
        (pid,),
    ))
    return jsonify(rows)


@app.route("/api/projets/<int:pid>/versions/<int:vid>/restore", methods=["POST"])
def restore_version(pid, vid):
    b = _restore(pid, vid)
    if not b:
        return jsonify({"error": "version introuvable"}), 404
    _snapshot(pid, source="system", label=f"Restauré depuis v{vid}")
    return jsonify(b)


@app.route("/api/projets/<int:pid>/generer", methods=["POST"])
def generer(pid):
    b = bundle(pid)
    if not b:
        return jsonify({"error": "projet introuvable"}), 404
    body = request.get_json(force=True, silent=True) or {}
    kind = body.get("type", "business_plan")
    if kind not in ("analyse", "business_plan", "scenarios", "note_codir"):
        return jsonify({"error": "type inconnu"}), 400
    doc = ai_service.generate(kind, b)
    _save_generation(pid, kind, doc)
    return jsonify(doc)


@app.route("/api/projets/<int:pid>/dossier", methods=["POST"])
def dossier_complet(pid):
    """Parcours Codir : évaluation IA du score, puis BP, scénarios, note."""
    b = bundle(pid)
    if not b:
        return jsonify({"error": "projet introuvable"}), 404
    evaluation, _score = _evaluer_et_sauver(pid, b)
    b = bundle(pid)
    out = {"evaluation": evaluation, "score": b["score"], "moteur_db": b["moteur_db"]}
    for kind in ("analyse", "business_plan", "scenarios", "note_codir"):
        doc = ai_service.generate(kind, b)
        _save_generation(pid, kind, doc)
        out[kind] = doc
    return jsonify(out)


@app.route("/api/projets/<int:pid>/chat", methods=["POST"])
def chat(pid):
    b = bundle(pid)
    if not b:
        return jsonify({"error": "projet introuvable"}), 404
    body = request.get_json(force=True, silent=True) or {}
    message = (body.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message vide"}), 400
    doc = ai_service.generate("chat", b, message=message)
    _save_generation(pid, "chat", doc)
    return jsonify(doc)


@app.route("/api/projets/<int:pid>/generations")
def generations(pid):
    rows = _json(db.q(
        "SELECT id, type_doc, moteur, created_at FROM generations WHERE projet_id = %s ORDER BY id DESC",
        (pid,),
    ))
    return jsonify(rows)


@app.route("/api/projets/<int:pid>/generations/<int:gid>")
def generation_detail(pid, gid):
    rows = _json(db.q(
        "SELECT id, type_doc, moteur, contenu_json, created_at FROM generations WHERE id = %s AND projet_id = %s",
        (gid, pid),
    ))
    if not rows:
        return jsonify({"error": "version introuvable"}), 404
    row = rows[0]
    try:
        row["contenu"] = json.loads(row["contenu_json"])
    except (json.JSONDecodeError, TypeError):
        row["contenu"] = {}
    return jsonify(row)


@app.route("/api/projets/<int:pid>/export.txt")
def export_txt(pid):
    b = bundle(pid)
    if not b:
        return jsonify({"error": "projet introuvable"}), 404
    gid = request.args.get("generation_id")
    if gid:
        last = db.q(
            "SELECT contenu_json FROM generations WHERE id = %s AND projet_id = %s AND type_doc = 'note_codir'",
            (gid, pid),
        )
    else:
        last = db.q(
            "SELECT contenu_json FROM generations WHERE projet_id = %s AND type_doc = 'note_codir' ORDER BY id DESC LIMIT 1",
            (pid,),
        )
    note = json.loads(last[0]["contenu_json"]) if last else ai_service.generate("note_codir", b)
    p = b["projet"]
    s = b["score"]
    lines = [
        f"NOTE CODIR — {p['code']} — {p['nom']}",
        f"Émetteur : Direction de l'Innovation — PostePlan IA",
        f"Score de pertinence : {s['score']}/100 — {s['recommandation']}",
        "",
        "ESSENTIEL",
    ]
    for item in note.get("essentiel_en_5_lignes") or []:
        lines.append(f"  • {item}")
    lines += ["", "POUR"]
    for item in note.get("arguments_pour") or []:
        lines.append(f"  + {item}")
    lines += ["", "CONTRE"]
    for item in note.get("arguments_contre") or []:
        lines.append(f"  − {item}")
    lines += [
        "",
        f"Risque principal : {note.get('risque_principal', '')}",
        f"Condition suspensive : {note.get('condition_suspensive', '')}",
        f"Décision proposée : {note.get('decision_proposee', '')}",
        f"Prochaine étape : {note.get('prochaine_etape', '')}",
        "",
        "Dimensions du score :",
    ]
    for dim in (s.get("dimensions") or {}).values():
        lines.append(f"  - {dim['label']}: {dim['value']}/100 (poids {int(dim['weight']*100)} %)")
    text = "\n".join(lines)
    return Response(
        text,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={p['code']}_note_codir.txt"},
    )


def main():
    engine = db.init_db()
    print(f"PostePlan IA prêt — base {engine}")
    # pré-calcule les scores
    for row in db.q("SELECT id FROM projets"):
        b = bundle(row["id"])
        if b:
            db.x("UPDATE projets SET score_pertinence = %s WHERE id = %s",
                 (b["score"]["score"], row["id"]))
    port = int(__import__("os").environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
