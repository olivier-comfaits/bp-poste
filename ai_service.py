"""Couche IA : Grok (xAI) ou Claude, sinon moteur déterministe.

Sélection :
  LLM_PROVIDER=grok|claude|auto   (défaut : auto)
  XAI_API_KEY + XAI_MODEL         (défaut modèle : grok-4.6)
  ANTHROPIC_API_KEY + ANTHROPIC_MODEL (défaut : claude-sonnet-4-6)

En mode auto : Grok si clé xAI, sinon Claude si clé Anthropic, sinon fallback.
Le fallback assemble un livrable structuré uniquement à partir de MySQL.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

SYSTEM_PROMPT = (
    "Tu es un analyste senior rattaché à la Direction de l'Innovation du Groupe La Poste, "
    "entreprise à mission. Tu produis des livrables destinés à un comité de direction : "
    "précis, sobres, actionnables. N'invente aucune donnée chiffrée absente de l'entrée. "
    "Réponds UNIQUEMENT par un JSON valide UTF-8, sans markdown."
)


def _k(n) -> str:
    try:
        return f"{float(n):,.0f}".replace(",", " ").replace(".", ",")
    except (TypeError, ValueError):
        return "n.d."


def payload_from_bundle(bundle: dict) -> dict:
    p = bundle["projet"]
    return {
        "projet": {
            "code": p.get("code"),
            "nom": p.get("nom"),
            "typologie": p.get("typologie"),
            "branche": p.get("branche"),
            "description": p.get("description"),
            "duree_mois": p.get("duree_mois"),
            "investissement_k_eur": float(p.get("investissement_k_eur") or 0),
            "roi_pct": float(p.get("roi_pct") or 0),
            "delai_retour_mois": p.get("delai_retour_mois"),
            "ca_annee_1_k": float(p.get("ca_annee_1_k") or 0),
            "ca_annee_3_k": float(p.get("ca_annee_3_k") or 0),
            "statut": p.get("statut"),
            "score": (bundle.get("score") or {}).get("score"),
            "recommandation": (bundle.get("score") or {}).get("recommandation"),
        },
        "porteur": bundle.get("porteur"),
        "dimensions_score": (bundle.get("score") or {}).get("dimensions"),
        "hypotheses": bundle.get("hypotheses") or [],
        "scenarios": bundle.get("scenarios") or [],
        "risques": bundle.get("risques") or [],
        "opportunites": bundle.get("opportunites") or [],
        "parametres_strategiques": bundle.get("parametres") or {},
    }


def _decision_from_score(score: float | None) -> str:
    s = float(score or 0)
    if s >= 75:
        return "GO"
    if s >= 60:
        return "GO sous conditions"
    if s >= 45:
        return "Réviser avant arbitrage"
    return "NO-GO ou report"


def fallback_analyse(b: dict) -> dict:
    p = b["projet"]
    risques = sorted(
        b.get("risques") or [],
        key=lambda r: int(r.get("probabilite") or 3) * int(r.get("impact") or 3),
        reverse=True,
    )
    opps = b.get("opportunites") or []
    params = b.get("parametres") or {}
    score = (b.get("score") or {}).get("score")
    dims = (b.get("score") or {}).get("dimensions") or {}

    def dim(key):
        return (dims.get(key) or {}).get("value")

    forces = [
        {
            "titre": f"Alignement Groupe ({dim('alignement_strategique')}/100)",
            "preuve": params.get("priorite_groupe") or p.get("description", "")[:220],
            "portee": "longue",
        },
        {
            "titre": "Porteur identifié et rattaché à une entité métier",
            "preuve": "{prenom} {nom} — {entite} (maturité {maturite}/5)".format(
                **{k: (b.get("porteur") or {}).get(k, "?") for k in ("prenom", "nom", "entite", "maturite")}
            ),
            "portee": "courte",
        },
    ]
    if float(p.get("roi_pct") or 0) >= 15:
        forces.append({
            "titre": f"ROI cible de {p.get('roi_pct')} %",
            "preuve": f"Retour estimé à {p.get('delai_retour_mois')} mois pour { _k(p.get('investissement_k_eur')) } k€ investis.",
            "portee": "moyenne",
        })
    if float(dim("impact_social_env") or 0) >= 60:
        forces.append({
            "titre": "Contribution mission / RSE",
            "preuve": f"Score social-environnemental {dim('impact_social_env')}/100, cohérent avec l'entreprise à mission.",
            "portee": "longue",
        })

    faiblesses = []
    if float(dim("rentabilite") or 0) < 50:
        faiblesses.append({
            "titre": "Équation économique encore fragile",
            "preuve": f"Dimension rentabilité à {dim('rentabilite')}/100 — CA an 3 = { _k(p.get('ca_annee_3_k')) } k€.",
            "gravite": "haute",
        })
    if int(p.get("risque_technique") or 3) >= 4:
        faiblesses.append({
            "titre": "Risque technique élevé",
            "preuve": "La maturité ou l'intégration SI reste un point dur (note risque technique ≥ 4/5).",
            "gravite": "haute",
        })
    if int(p.get("complexite_operationnelle") or 3) >= 4:
        faiblesses.append({
            "titre": "Complexité de déploiement",
            "preuve": f"Durée {p.get('duree_mois')} mois, plusieurs branches potentiellement impactées.",
            "gravite": "moyenne",
        })
    if not faiblesses:
        faiblesses.append({
            "titre": "Dépendance à la qualité des données d'entrée",
            "preuve": "Le score et le récit IA ne valent que ce que valent les hypothèses saisies.",
            "gravite": "moyenne",
        })

    risques_cles = []
    for r in risques[:5]:
        crit = int(r.get("probabilite") or 3) * int(r.get("impact") or 3)
        risques_cles.append({
            "libelle": r.get("libelle"),
            "categorie": r.get("categorie"),
            "criticite": crit,
            "effet": f"Probabilité {r.get('probabilite')}/5 × impact {r.get('impact')}/5.",
            "mitigation": r.get("mitigation") or "À préciser avec le porteur.",
        })

    return {
        "type": "analyse",
        "moteur": "fallback",
        "forces": forces[:5],
        "faiblesses": faiblesses[:5],
        "risques_cles": risques_cles,
        "opportunites_cles": [
            {"libelle": o.get("libelle"), "levier": o.get("description")}
            for o in opps[:4]
        ],
        "points_de_vigilance_codir": [
            f"Score de pertinence : {score}/100 — {(b.get('score') or {}).get('recommandation')}.",
            params.get("dependances") or "Dépendances SI et métier à confirmer avant engagement.",
        ],
        "limites": [
            "Diagnostic produit par le moteur de repli (pas d'appel LLM). Les montants sont ceux de MySQL."
        ],
    }


def fallback_business_plan(b: dict) -> dict:
    p = b["projet"]
    params = b.get("parametres") or {}
    score = (b.get("score") or {}).get("score")
    reco = (b.get("score") or {}).get("recommandation")
    decision = _decision_from_score(score)
    porteur = b.get("porteur") or {}
    hypos = b.get("hypotheses") or []

    ca_lines = ", ".join(
        f"N+{h.get('annee')} recettes { _k(float(h.get('recette_p1_k') or 0)+float(h.get('recette_p2_k') or 0)+float(h.get('recette_p3_k') or 0)) } k€"
        for h in hypos
    ) or "hypothèses financières à compléter"

    sections = {
        "resume_executif": {
            "texte": (
                f"{p.get('nom')} ({p.get('code')}) est un projet {p.get('typologie')} porté par "
                f"{porteur.get('prenom', '')} {porteur.get('nom', '')} ({porteur.get('entite', '')}), "
                f"rattaché à la branche {p.get('branche')}. Investissement demandé : "
                f"{_k(p.get('investissement_k_eur'))} k€ sur {p.get('duree_mois')} mois. "
                f"ROI cible {p.get('roi_pct')} %, délai de retour {p.get('delai_retour_mois')} mois. "
                f"Score de pertinence {score}/100 — lecture : {reco}."
            ),
            "go_suggere": decision,
            "score": score,
        },
        "description_projet": {
            "contexte": p.get("description") or "",
            "objectifs": [
                "Disposer d'un dossier d'arbitrage comparable aux autres projets du portefeuille.",
                "Sécuriser faisabilité, rentabilité, alignement et risques avant engagement Codir.",
                "Poser un plan d'action 90 jours / 12 mois exécutable par le porteur.",
            ],
            "perimetre": f"Conception, pilote et première industrialisation sur {p.get('duree_mois')} mois.",
            "hors_perimetre": "Refonte SI transverse non cadrée, recrutement de masse, changement de modèle social.",
        },
        "analyse_strategique": {
            "alignement": params.get("priorite_groupe") or "Alignement à préciser avec la stratégie Groupe.",
            "avantage": params.get("avantage_concurrentiel") or "Avantage à documenter.",
            "dependances": params.get("dependances") or "Dépendances à inventorier.",
        },
        "analyse_marche": {
            "cible": params.get("opportunite_marche") or "Cible à préciser.",
            "taille_utile": f"CA année 1 {_k(p.get('ca_annee_1_k'))} k€ / année 3 {_k(p.get('ca_annee_3_k'))} k€ (données porteur).",
            "tendances": [
                "Digitalisation des parcours internes et clients du Groupe.",
                "Pression RSE et entreprise à mission sur tout nouvel investissement.",
                "Besoin Codir de dossiers comparables (score unique, scénarios, note d'une page).",
            ],
        },
        "analyse_concurrentielle": {
            "alternatives_internes": [
                "Ne rien faire : coût d'opportunité et dispersion des PoC.",
                "Étendre un outil existant sans couche IA ni score unique.",
            ],
            "alternatives_externes": [
                "Progiciel éditeur (coût de licence, faible spécificité La Poste).",
                "Prestation conseil one-shot sans capitalisation data.",
            ],
            "facteurs_differenciants": [
                params.get("avantage_concurrentiel") or "Ancrage métier La Poste.",
                "Traçabilité des hypothèses dans MySQL et score explicable.",
            ],
        },
        "modele_economique": {
            "logique_de_valeur": (
                "Création de valeur par gains internes (productivité, recrutements évités, km, CO2) "
                "et/ou recettes externes selon la typologie. Les recettes du modèle sont celles saisies "
                f"par le porteur ({ca_lines})."
            ),
            "sources_recettes": [
                "Valorisation de gains internes (si projet transverse).",
                "Recettes produits / services (si offre externe ou intra-groupe).",
                "Aides publiques éventuelles (non intégrées tant que non sécurisées).",
            ],
            "structure_couts": [
                "Masse salariale projet (build puis run).",
                "Logiciels / tokens IA / hébergement.",
                "Matériel, frais admin, fiscalité.",
            ],
        },
        "hypotheses_financieres": {
            "commentaire": (
                f"Les 3 années sont chargées en base. Investissement total "
                f"{_k(p.get('investissement_k_eur'))} k€. "
                "Aucun montant n'a été extrapolé hors base."
            ),
            "points_d_attention": [
                "Sensibilité forte au rythme d'adoption (scénario bas vs haut).",
                "BFR et trésorerie d'amorçage à provisionner dès N+1.",
                "Les aides et subventions ne doivent entrer qu'une fois contractualisées.",
            ],
        },
        "scenarios": {
            "commentaire_transversal": (
                "Trois scénarios (bas / médian / haut) sont stockés en base. "
                "Le scénario médian est la référence d'arbitrage Codir."
            )
        },
        "plan_action": {
            "jalons_90_jours": [
                "Geler le périmètre et les hypothèses v1 avec le sponsor.",
                "AIPD / revue juridique si données personnelles ou activité régulée.",
                "Pilote sur un périmètre restreint + revue score à J+60.",
            ],
            "jalons_12_mois": [
                "Industrialisation du flux principal et bascule run.",
                "Mesure des KPI (voir paramètres stratégiques) et révision du score.",
                "Décision d'extension ou d'arrêt au vu du scénario réalisé.",
            ],
            "gouvernance": "Sponsor N-1 métier, product owner, DSI, finance, et point Codir à chaque porte.",
        },
        "synthese_codir": {
            "en_une_phrase": (
                f"{p.get('nom')} — score {score}/100 — {decision} — "
                f"{_k(p.get('investissement_k_eur'))} k€ / {p.get('duree_mois')} mois."
            ),
            "decision_demandee": decision,
        },
    }
    return {
        "type": "business_plan",
        "moteur": "fallback",
        "sections": sections,
        "limites": ["Business plan assemblé par le moteur de repli à partir de MySQL."],
    }


def fallback_scenarios(b: dict) -> dict:
    out = []
    mapping_prob = {"bas": "faible", "median": "haute", "haut": "moyenne"}
    for s in b.get("scenarios") or []:
        t = s.get("type_scenario")
        out.append({
            "type_scenario": t,
            "narratif": s.get("hypotheses") or "",
            "conditions": [
                f"CA cumulé 3 ans : {_k(s.get('ca_3ans_k'))} k€",
                f"Résultat 3 ans : {_k(s.get('resultat_3ans_k'))} k€",
                f"ROI scénario : {s.get('roi_pct')} %",
            ],
            "signaux_d_alerte": [
                "Écart d'adoption supérieur à 20 points vs. médian.",
                "Dérive de l'investissement supérieure à 15 %.",
            ],
            "probabilite_qualitative": mapping_prob.get(t, "moyenne"),
        })
    return {
        "type": "scenarios",
        "moteur": "fallback",
        "scenarios": out,
        "scenario_de_reference_codir": "median",
        "justification_reference": "Le médian reflète les hypothèses du porteur sans option haute ni stress sévère.",
        "limites": ["Commentaire déterministe — montants non recalculés."],
    }


def fallback_note_codir(b: dict) -> dict:
    p = b["projet"]
    score = (b.get("score") or {}).get("score")
    reco = (b.get("score") or {}).get("recommandation")
    decision = _decision_from_score(score)
    params = b.get("parametres") or {}
    risques = sorted(
        b.get("risques") or [],
        key=lambda r: int(r.get("probabilite") or 3) * int(r.get("impact") or 3),
        reverse=True,
    )
    risque_principal = risques[0]["libelle"] if risques else "Risque principal à documenter."
    dims = (b.get("score") or {}).get("dimensions") or {}

    pour = [
        params.get("priorite_groupe") or "Alignement stratégique Groupe.",
        f"ROI cible {p.get('roi_pct')} % pour un délai de retour de {p.get('delai_retour_mois')} mois.",
        params.get("avantage_concurrentiel") or "Différenciation interne documentée.",
    ]
    contre = [
        f"Investissement de {_k(p.get('investissement_k_eur'))} k€ à arbitrer contre d'autres dossiers.",
        risque_principal,
        "Sensibilité du résultat au scénario bas (voir fiche scénarios).",
    ]
    return {
        "type": "note_codir",
        "moteur": "fallback",
        "en_tete": {
            "objet": f"Arbitrage {p.get('code')} — {p.get('nom')}",
            "emetteur": "Direction de l'Innovation — PostePlan IA",
            "destinataire": "Comité de direction",
            "classification": "Usage interne",
        },
        "essentiel_en_5_lignes": [
            f"Projet {p.get('typologie')} / branche {p.get('branche')}, durée {p.get('duree_mois')} mois.",
            f"Investissement {_k(p.get('investissement_k_eur'))} k€ — CA an 3 {_k(p.get('ca_annee_3_k'))} k€.",
            f"Score de pertinence {score}/100 (rentabilité {(dims.get('rentabilite') or {}).get('value')}, "
            f"alignement {(dims.get('alignement_strategique') or {}).get('value')}).",
            f"Lecture recommandée : {reco}.",
            f"Risque principal : {risque_principal}",
        ],
        "score": {"valeur": score, "lecture": reco},
        "investissement": {
            "montant_k_eur": float(p.get("investissement_k_eur") or 0),
            "duree_mois": p.get("duree_mois"),
            "delai_retour_mois": p.get("delai_retour_mois"),
        },
        "arguments_pour": pour,
        "arguments_contre": contre,
        "risque_principal": risque_principal,
        "condition_suspensive": "Validation des hypothèses N+1 par la finance de branche et revue juridique si données perso / activité régulée.",
        "decision_proposee": decision,
        "prochaine_etape": "Point porte à 90 jours : pilote, score recalculé, go / no-go d'industrialisation.",
        "limites": ["Note assemblée par le moteur de repli. Aucun chiffre hors base MySQL."],
    }


def fallback_chat(b: dict, message: str) -> dict:
    p = b["projet"]
    score = (b.get("score") or {}).get("score")
    msg = (message or "").strip()
    return {
        "type": "chat",
        "moteur": "fallback",
        "reponse": (
            f"Demande prise en compte pour {p.get('code')} — {p.get('nom')} "
            f"(score actuel {score}/100). "
            f"Reformulation : « {msg[:280]} ». "
            "Je ne modifie aucun montant non saisi. "
            "Pour faire bouger le score, ajustez ROI, délai de retour, risques ou impacts dans le formulaire, "
            "puis relancez le calcul."
        ),
        "ajustements_suggerees": [],
        "impact_score": "incertain",
        "questions_de_clarification": [
            "Quel champ quantititatif voulez-vous réviser (ROI, investissement, risque technique) ?",
            "S'agit-il d'un ajustement de scénario (bas / médian / haut) ou du projet de référence ?",
        ],
        "limites": ["Dialogue de repli : pas d'appel LLM. Aucune donnée inventée."],
    }


def fallback_evaluation(b: dict) -> dict:
    """Notes 1–5 déduites du dossier. Le porteur ne les saisit pas."""
    p = b.get("projet") or {}
    typ = (p.get("typologie") or "").lower()
    desc = ((p.get("description") or "") + " " + json.dumps(b.get("parametres") or {}, ensure_ascii=False)).lower()
    inv = float(p.get("investissement_k_eur") or 0)
    duree = int(p.get("duree_mois") or 18)
    roi = float(p.get("roi_pct") or 0)

    def clip(n):
        return max(1, min(5, int(n)))

    alignement = 5 if typ in ("rh", "rse", "territorial") else 4 if typ in ("innovation", "digital") else 3
    if any(w in desc for w in ("mission", "groupe", "service universel", "marque employeur")):
        alignement = clip(alignement + 1)
    impact_branches = 5 if typ in ("digital", "client") else 4 if typ in ("logistique", "rh") else 3
    complexite = 5 if inv >= 3500 or duree >= 30 else 4 if inv >= 1500 else 3 if inv >= 700 else 2
    maturite = 4 if typ in ("rh", "innovation", "digital") else 3
    social = 5 if typ in ("rh", "territorial") else 4 if typ in ("rse", "innovation") else 2
    environnement = 5 if typ == "rse" else 4 if typ == "logistique" else 2
    if any(w in desc for w in ("co2", "carbone", "vélo", "zfe", "décarbon")):
        environnement = 5
    risque_tech = 5 if typ == "client" else 4 if typ in ("logistique", "digital") else 2
    risque_hum = 4 if typ in ("digital", "rh") else 3
    risque_reg = 5 if typ in ("innovation",) and "banque" in (p.get("branche") or "").lower() else 4 if typ == "rh" else 2
    if roi >= 20:
        maturite = clip(maturite + 1)

    justifications = {
        "alignement_groupe": f"Typologie {typ or 'n.d.'} rapprochée des priorités Groupe (mission, branches, innovation).",
        "impact_branches": "Lecture du périmètre et de la branche porteuse.",
        "complexite_operationnelle": f"Investissement {_k(inv)} k€ sur {duree} mois.",
        "maturite_technique": "Maturité estimée d'après la nature du projet et le dossier saisi.",
        "impact_social": "Contribution emploi, inclusion ou territoire déduite du libellé et de la typologie.",
        "impact_environnemental": "Contribution carbone / flotte / last-mile déduite du dossier.",
        "risque_technique": "Intégration SI et nouveauté technologique estimées.",
        "risque_humain": "Conduite du changement et adoption métier estimées.",
        "risque_reglementaire": "RGPD / régulation de branche estimées.",
    }
    return {
        "type": "evaluation",
        "moteur": "fallback",
        "alignement_groupe": clip(alignement),
        "impact_branches": clip(impact_branches),
        "complexite_operationnelle": clip(complexite),
        "maturite_technique": clip(maturite),
        "impact_social": clip(social),
        "impact_environnemental": clip(environnement),
        "risque_technique": clip(risque_tech),
        "risque_humain": clip(risque_hum),
        "risque_reglementaire": clip(risque_reg),
        "justifications": justifications,
        "limites": [
            "Notes produites par le moteur d'évaluation (LLM ou repli). "
            "Le porteur n'a pas saisi ces notes. Le score 0–100 est calculé ensuite par pondération."
        ],
    }


FALLBACKS = {
    "analyse": fallback_analyse,
    "business_plan": fallback_business_plan,
    "scenarios": fallback_scenarios,
    "note_codir": fallback_note_codir,
    "evaluation": fallback_evaluation,
}


def _strip_fences(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return text.strip()


def _parse_llm_json(text: str, moteur: str) -> dict | None:
    try:
        parsed = json.loads(_strip_fences(text))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    parsed["moteur"] = moteur
    return parsed


def configured_providers() -> list[str]:
    found = []
    if os.environ.get("XAI_API_KEY"):
        found.append("grok")
    if os.environ.get("ANTHROPIC_API_KEY"):
        found.append("claude")
    return found


def preferred_provider() -> str:
    choice = (os.environ.get("LLM_PROVIDER") or "auto").strip().lower()
    available = configured_providers()
    if choice in ("grok", "claude"):
        return choice if choice in available else (available[0] if available else "fallback")
    if available:
        return available[0]
    return "fallback"


def _call_claude(user_prompt: str, timeout: int = 45) -> dict | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    body = json.dumps({
        "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        "max_tokens": 3500,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        text = "".join(
            block.get("text", "")
            for block in raw.get("content", [])
            if block.get("type") == "text"
        )
        return _parse_llm_json(text, "claude")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
        return None


def _call_grok(user_prompt: str, timeout: int = 40) -> dict | None:
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        return None
    base = os.environ.get("XAI_API_BASE", "https://api.x.ai/v1").rstrip("/")
    body = json.dumps({
        "model": os.environ.get("XAI_MODEL", "grok-4.6"),
        "temperature": 0.2,
        "max_tokens": 3500,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        text = (
            raw.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return _parse_llm_json(text, "grok")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError, IndexError):
        return None


PROVIDERS = {
    "grok": _call_grok,
    "claude": _call_claude,
}


def _call_llm(user_prompt: str) -> dict | None:
    primary = preferred_provider()
    order = []
    if primary in PROVIDERS:
        order.append(primary)
    for name in configured_providers():
        if name not in order:
            order.append(name)
    last_error = None
    for name in order:
        result = PROVIDERS[name](user_prompt)
        if result and not result.get("_error"):
            return result
        if result and result.get("_error"):
            last_error = result["_error"]
    if last_error:
        return {"_error": last_error}
    return None


def generate(kind: str, bundle: dict, message: str | None = None) -> dict:
    payload = json.dumps(payload_from_bundle(bundle), ensure_ascii=False, indent=2)
    prompts = {
        "analyse": (
            "Analyse le projet et identifie forces, faiblesses, risques. "
            "Réponds uniquement par le JSON demandé dans le contrat métier. "
            + payload
        ),
        "business_plan": (
            "Rédige un business plan en 10 sections JSON. "
            "N'invente aucun montant absent des données. "
            + payload
        ),
        "scenarios": (
            "Commente les 3 scénarios financiers sans recalculer les montants. "
            + payload
        ),
        "note_codir": (
            "Rédige une note d'arbitrage Codir d'une page au format JSON. "
            "La décision doit suivre le score fourni. "
            + payload
        ),
        "evaluation": (
            "Tu es l'évaluateur du score de pertinence. Le porteur N'A PAS saisi de notes. "
            "À partir du dossier (description, branche, typologie, montants, paramètres), "
            "attribue une note entière de 1 à 5 à chaque champ. "
            "1 = très faible, 5 = très élevé. Pour les risques, 5 = risque élevé. "
            "RÈGLES D'AJUSTEMENT : "
            "si la description mentionne des mitigations concrètes (formation, pilote, "
            "mode dégradé, sponsoring, abstraction multi-modèles, API contract-first, "
            "tests UX, ambassadeurs), BAISSE les risques concernés d'au moins 1 point "
            "par rapport à une description sans mitigation. "
            "Si la description précise un alignement Groupe, un impact social ou "
            "environnemental, ou une maturité technique, HAUSSE les champs correspondants. "
            "N'invente aucun montant. Ne calcule PAS le score 0–100. "
            "JSON strict : "
            '{"type":"evaluation",'
            '"alignement_groupe":1,"impact_branches":1,'
            '"complexite_operationnelle":1,"maturite_technique":1,'
            '"impact_social":1,"impact_environnemental":1,'
            '"risque_technique":1,"risque_humain":1,"risque_reglementaire":1,'
            '"justifications":{"alignement_groupe":"","impact_branches":"",'
            '"complexite_operationnelle":"","maturite_technique":"",'
            '"impact_social":"","impact_environnemental":"",'
            '"risque_technique":"","risque_humain":"","risque_reglementaire":""},'
            '"limites":[]}'
            "\n\nDossier : " + payload
        ),
        "chat": (
            "Tu es le conseiller du porteur. Le porteur ne note pas son projet : "
            "il modifie uniquement la description (et éventuellement les montants). "
            "L'IA réévaluera ensuite les dimensions. "
            "Réponds en JSON strict avec :\n"
            '{"type":"chat","reponse":"...","propositions":[{"champ":"description",'
            '"extrait_a_ajouter":"...","effet_attendu":"baisse risque_humain|hausse alignement_groupe|..."}],'
            '"impact_score":"hausse","limites":[]}\n'
            "Propose 2 à 3 phrases concrètes à AJOUTER à la description. "
            "Chaque phrase doit mentionner une mitigation ou un levier qui, "
            "à la réévaluation, fera BAISSER un risque ou HAUSSER un alignement/impact. "
            "N'invente aucun montant. Ne propose pas de champs de notation.\n\n"
            f"Demande : {message}\n\nProjet : {payload}"
        ),
    }
    llm = _call_llm(prompts.get(kind, payload))
    if llm and not llm.get("_error"):
        return llm
    if kind == "chat":
        fb = fallback_chat(bundle, message or "")
        if llm and llm.get("_error"):
            fb["limites"] = [f"Erreur API : {llm['_error']}"]
            fb["reponse"] += f" [Erreur API : {llm['_error']}]"
        return fb
    if llm and llm.get("_error"):
        fb = FALLBACKS[kind](bundle)
        fb.setdefault("limites", []).append(f"Erreur API : {llm['_error']}")
        return fb
    return FALLBACKS[kind](bundle)
