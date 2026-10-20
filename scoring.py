"""Score de pertinence 0–100 — 6 dimensions pondérées.

Pondération retenue (justification dans PROMPTS.md et README) :
  rentabilite                 25 %
  alignement_strategique      20 %
  risque                      15 %   (inversé : moins de risque = mieux)
  impact_operationnel         15 %
  impact_social_env           15 %
  faisabilite_technique       10 %
"""

from __future__ import annotations

WEIGHTS = {
    "rentabilite": 0.25,
    "alignement_strategique": 0.20,
    "risque": 0.15,
    "impact_operationnel": 0.15,
    "impact_social_env": 0.15,
    "faisabilite_technique": 0.10,
}


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _scale_1_5(score_1_5: float, invert: bool = False) -> float:
    """Mappe un avis 1–5 vers 0–100."""
    v = float(score_1_5 or 3)
    v = _clamp(v, 1, 5)
    pct = (v - 1) / 4 * 100
    return 100 - pct if invert else pct


def score_rentabilite(projet: dict) -> float:
    roi = float(projet.get("roi_pct") or 0)
    delai = float(projet.get("delai_retour_mois") or 36)
    inv = float(projet.get("investissement_k_eur") or 1)
    ca3 = float(projet.get("ca_annee_3_k") or 0)

    # ROI : 0 % → 20 / 15 % → 60 / 30 %+ → 100
    roi_pts = _clamp(20 + roi * (80 / 30))
    # Délai de retour : 12 mois → 100 / 48 mois → 20
    delai_pts = _clamp(100 - (delai - 12) * (80 / 36))
    # Intensité de création de valeur : CA an 3 / investissement
    ratio = ca3 / inv if inv > 0 else 0
    ratio_pts = _clamp(ratio / 2.5 * 100)

    return _clamp(0.45 * roi_pts + 0.30 * delai_pts + 0.25 * ratio_pts)


def score_alignement(projet: dict) -> float:
    return _clamp(
        0.65 * _scale_1_5(projet.get("alignement_groupe"))
        + 0.35 * _scale_1_5(projet.get("impact_branches"))
    )


def score_risque(projet: dict) -> float:
    """Plus le risque déclaré est faible, plus la note est élevée."""
    tech = _scale_1_5(projet.get("risque_technique"), invert=True)
    hum = _scale_1_5(projet.get("risque_humain"), invert=True)
    reg = _scale_1_5(projet.get("risque_reglementaire"), invert=True)
    return _clamp(0.40 * tech + 0.30 * hum + 0.30 * reg)


def score_impact_operationnel(projet: dict) -> float:
    # Complexité haute pénalise (plus dur à déployer) mais impact branches valorise.
    complexite = _scale_1_5(projet.get("complexite_operationnelle"), invert=True)
    impact = _scale_1_5(projet.get("impact_branches"))
    return _clamp(0.45 * complexite + 0.55 * impact)


def score_social_env(projet: dict) -> float:
    return _clamp(
        0.55 * _scale_1_5(projet.get("impact_social"))
        + 0.45 * _scale_1_5(projet.get("impact_environnemental"))
    )


def score_faisabilite(projet: dict) -> float:
    tech = _scale_1_5(projet.get("maturite_technique"))
    maturite_porteur = _scale_1_5(projet.get("porteur_maturite") or 3)
    complexite = _scale_1_5(projet.get("complexite_operationnelle"), invert=True)
    return _clamp(0.50 * tech + 0.25 * maturite_porteur + 0.25 * complexite)


DIMENSION_FNS = {
    "rentabilite": score_rentabilite,
    "alignement_strategique": score_alignement,
    "risque": score_risque,
    "impact_operationnel": score_impact_operationnel,
    "impact_social_env": score_social_env,
    "faisabilite_technique": score_faisabilite,
}

LABELS = {
    "rentabilite": "Rentabilité",
    "alignement_strategique": "Alignement stratégique",
    "risque": "Maîtrise des risques",
    "impact_operationnel": "Impact opérationnel",
    "impact_social_env": "Impact social / environnemental",
    "faisabilite_technique": "Faisabilité technique",
}


def compute_score(projet: dict) -> dict:
    dimensions = {}
    total = 0.0
    for key, fn in DIMENSION_FNS.items():
        value = round(fn(projet), 1)
        dimensions[key] = {
            "label": LABELS[key],
            "value": value,
            "weight": WEIGHTS[key],
            "contribution": round(value * WEIGHTS[key], 2),
        }
        total += value * WEIGHTS[key]
    total = round(_clamp(total), 1)

    if total >= 75:
        recommandation, go = "GO prioritaire", "go"
    elif total >= 60:
        recommandation, go = "GO sous conditions", "go_conditions"
    elif total >= 45:
        recommandation, go = "Réviser avant arbitrage", "reviser"
    else:
        recommandation, go = "NO-GO ou report", "nogo"

    return {
        "score": total,
        "recommandation": recommandation,
        "go": go,
        "dimensions": dimensions,
        "formule": "L'IA note les dimensions qualitatives (1–5) ; la rentabilité vient des montants saisis ; le 0–100 est la somme pondérée.",
    }


# Champs projet que l'IA a le droit de renseigner — jamais le score final.
RATING_FIELDS = (
    "alignement_groupe",
    "impact_branches",
    "complexite_operationnelle",
    "maturite_technique",
    "impact_social",
    "impact_environnemental",
    "risque_technique",
    "risque_humain",
    "risque_reglementaire",
)


def _as_1_5(value, default=3) -> int:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        n = default
    return max(1, min(5, n))


def apply_ai_ratings(projet: dict, ratings: dict | None) -> dict:
    """Fusionne les notes IA (1–5) dans le projet, sans toucher aux montants."""
    updated = dict(projet)
    ratings = ratings or {}
    for field in RATING_FIELDS:
        if field in ratings and ratings[field] is not None:
            updated[field] = _as_1_5(ratings[field], updated.get(field) or 3)
    return updated
