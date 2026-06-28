"""Genere un PDF francais des feuilles de route des 65 idees de projet fintech.

Usage:
    python scripts/generate_roadmaps_pdf.py

Sortie:
    docs/Feuilles_de_route_Projets_Fintech.pdf
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


# ----------------------------------------------------------------------------
# Polices
# ----------------------------------------------------------------------------
def _register_fonts() -> tuple[str, str, str]:
    candidates = [
        "/usr/share/fonts/dejavu-sans-fonts",
        "/usr/share/fonts/dejavu",
        "/usr/share/fonts/TTF",
        "/usr/share/fonts/truetype/dejavu",
    ]
    for base in candidates:
        p = Path(base)
        if (p / "DejaVuSans.ttf").exists():
            try:
                pdfmetrics.registerFont(TTFont("DejaVu", str(p / "DejaVuSans.ttf")))
                pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(p / "DejaVuSans-Bold.ttf")))
                pdfmetrics.registerFont(TTFont("DejaVu-Mono", str(p / "DejaVuSansMono.ttf")))
                return "DejaVu", "DejaVu-Bold", "DejaVu-Mono"
            except Exception:
                continue
    return "Helvetica", "Helvetica-Bold", "Courier"


FONT, FONT_B, FONT_M = _register_fonts()

# Couleurs
NAVY = colors.HexColor("#1e3a5f")
ACCENT = colors.HexColor("#c8553d")
GRAY = colors.HexColor("#4a4a4a")
LIGHT_BG = colors.HexColor("#f4f4f8")
TABLE_HEADER = colors.HexColor("#1e3a5f")
TABLE_ROW = colors.HexColor("#e8eef5")

LEVEL_COLORS = {
    "JUNIOR": colors.HexColor("#2e7d32"),       # vert
    "INTERMÉDIAIRE": colors.HexColor("#ef6c00"),  # orange
    "SENIOR": colors.HexColor("#c62828"),         # rouge
}


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle", parent=base["Title"],
            fontName=FONT_B, fontSize=28, leading=34,
            textColor=colors.whitesmoke, alignment=TA_CENTER, spaceAfter=10,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            fontName=FONT, fontSize=14, leading=18,
            textColor=colors.HexColor("#cfd8e3"), alignment=TA_CENTER,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta", fontName=FONT, fontSize=11, leading=15,
            textColor=GRAY, alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "H1", fontName=FONT_B, fontSize=18, leading=22,
            textColor=NAVY, spaceBefore=6, spaceAfter=10, keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2", fontName=FONT_B, fontSize=13, leading=16,
            textColor=NAVY, spaceBefore=10, spaceAfter=6, keepWithNext=True,
        ),
        "project_title": ParagraphStyle(
            "ProjectTitle", fontName=FONT_B, fontSize=12, leading=15,
            textColor=ACCENT, spaceBefore=6, spaceAfter=4, keepWithNext=True,
        ),
        "section_label": ParagraphStyle(
            "SectionLabel", fontName=FONT_B, fontSize=9.5, leading=12,
            textColor=NAVY, spaceBefore=4, spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "Body", fontName=FONT, fontSize=9.5, leading=13,
            textColor=colors.black, alignment=TA_JUSTIFY, spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "Bullet", fontName=FONT, fontSize=9.5, leading=12,
            textColor=colors.black, leftIndent=12, bulletIndent=2, spaceAfter=2,
        ),
        "phase_title": ParagraphStyle(
            "PhaseTitle", fontName=FONT_B, fontSize=9.5, leading=12,
            textColor=NAVY, leftIndent=4, spaceBefore=3, spaceAfter=2,
        ),
        "intro": ParagraphStyle(
            "Intro", fontName=FONT, fontSize=10.5, leading=15,
            textColor=colors.black, alignment=TA_JUSTIFY, spaceAfter=8,
        ),
        "toc1": ParagraphStyle(
            "TOC1", fontName=FONT_B, fontSize=10.5, leading=16,
            textColor=NAVY,
        ),
        "toc2": ParagraphStyle(
            "TOC2", fontName=FONT, fontSize=9.5, leading=13,
            textColor=GRAY, leftIndent=14,
        ),
    }


S = _styles()


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def bullets(items: list[str]) -> list[Paragraph]:
    return [Paragraph(f"• {item}", S["bullet"]) for item in items]


def level_badge(level: str) -> Table:
    color = LEVEL_COLORS.get(level, GRAY)
    cell_style = ParagraphStyle(
        "BadgeCell", fontName=FONT_B, fontSize=8.5, leading=10,
        textColor=colors.whitesmoke, alignment=TA_CENTER,
    )
    t = Table([[Paragraph(level, cell_style)]], colWidths=[3.2 * cm], rowHeights=[0.55 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def duration_badge(duration: str) -> Table:
    cell_style = ParagraphStyle(
        "DurCell", fontName=FONT, fontSize=8.5, leading=10,
        textColor=NAVY, alignment=TA_CENTER,
    )
    t = Table([[Paragraph("Durée : " + duration, cell_style)]],
              colWidths=[4 * cm], rowHeights=[0.55 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.4, NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def stack_table(stack: dict) -> Table:
    rows = [[Paragraph("<b>Couche</b>", S["body"]), Paragraph("<b>Outils</b>", S["body"])]]
    for k, v in stack.items():
        rows.append([
            Paragraph(k, ParagraphStyle("k", fontName=FONT_B, fontSize=9, leading=11, textColor=NAVY)),
            Paragraph(v, ParagraphStyle("v", fontName=FONT, fontSize=9, leading=11)),
        ])
    t = Table(rows, colWidths=[3.5 * cm, 12.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TABLE_ROW]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BOX", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
    ]))
    return t


def project_card(p: dict) -> KeepTogether:
    """Construit la carte d'un projet (1 page environ)."""
    title = f"{p['code']} — {p['title']}"
    flowables = [P(title, "project_title")]

    # Ligne badges
    badge_row = Table(
        [[level_badge(p["level"]), duration_badge(p["duration"])]],
        colWidths=[3.5 * cm, 4.5 * cm],
    )
    badge_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    flowables.append(badge_row)
    flowables.append(Spacer(1, 4))

    # Problème
    flowables.append(P("Problème", "section_label"))
    flowables.append(P(p["problem"], "body"))

    # Feuille de route
    flowables.append(P("Feuille de route", "section_label"))
    for phase_name, phase_items in p["roadmap"]:
        flowables.append(P(phase_name, "phase_title"))
        flowables.extend(bullets(phase_items))

    # Stack
    flowables.append(Spacer(1, 4))
    flowables.append(P("Stack technique", "section_label"))
    flowables.append(stack_table(p["stack"]))

    # Prérequis
    flowables.append(Spacer(1, 4))
    flowables.append(P("Prérequis & compétences clés", "section_label"))
    flowables.extend(bullets(p["prereq"]))
    flowables.append(Spacer(1, 10))
    return KeepTogether(flowables)


# ----------------------------------------------------------------------------
# Document avec TOC
# ----------------------------------------------------------------------------
class MyDocTemplate(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            sn = flowable.style.name
            if sn == "H1":
                self.notify("TOCEntry", (0, flowable.getPlainText(), self.page))
            elif sn == "ProjectTitle":
                self.notify("TOCEntry", (1, flowable.getPlainText(), self.page))


def _hdr_ftr(canvas, doc):
    canvas.saveState()
    w, h = A4
    if doc.page >= 3:
        canvas.setFont(FONT, 8.5)
        canvas.setFillColor(GRAY)
        canvas.drawString(2 * cm, h - 1.2 * cm, "Feuilles de route — Projets Fintech")
        canvas.drawRightString(w - 2 * cm, h - 1.2 * cm,
                               f"Version 1.0  ·  {date.today().isoformat()}")
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, h - 1.4 * cm, w - 2 * cm, h - 1.4 * cm)
    if doc.page >= 2:
        canvas.setFont(FONT, 8.5)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(w / 2, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _cover_bg(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 6 * cm, w, 6 * cm, stroke=0, fill=1)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, h - 6.3 * cm, w, 0.3 * cm, stroke=0, fill=1)
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, w, 2 * cm, stroke=0, fill=1)
    canvas.restoreState()


# ----------------------------------------------------------------------------
# Données : les 65 projets
# ----------------------------------------------------------------------------
PROJECTS: list[dict] = []  # rempli par le module data ci-dessous



# Helpers data
def _rm(*phases):
    return list(phases)


def _phase(title, items):
    return (title, items)


# ============================================================================
# 1. RISQUE & FRAUDE
# ============================================================================
PROJECTS.append({
    "code": "1.1", "category": "1. Risque & Fraude",
    "title": "Détection de comptes mules",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "Un compte mule reçoit puis transfère rapidement de l'argent volé. Les régulateurs sanctionnent durement les banques qui en hébergent (amendes ACPR/BaFin pouvant dépasser 10 M€).",
    "roadmap": _rm(
        _phase("Phase 1 — Cadrage & data (1-2 sem)", [
            "Recenser les cas avérés des 18 derniers mois avec l'équipe Fraude.",
            "Définir la fenêtre temporelle d'analyse (typiquement 7 à 30 jours).",
            "Spécifier les métriques cibles : recall @ 1 % FPR et coût par alerte.",
        ]),
        _phase("Phase 2 — Construction du graphe (2-3 sem)", [
            "Modéliser comptes et virements en graphe orienté pondéré.",
            "Extraire des features de graphe : pagerank, in/out degree ratio, vélocité.",
            "Calculer features classiques : âge du compte, volume, dispersion géo.",
        ]),
        _phase("Phase 3 — Modélisation hybride (2-3 sem)", [
            "Règles dures : compte récent + montant entrant > seuil + sortie ≤ 24 h.",
            "Modèle supervisé (LightGBM ou XGBoost) sur features graphe + classiques.",
            "Approche non supervisée (Isolation Forest) pour les patterns inconnus.",
        ]),
        _phase("Phase 4 — Industrialisation (2 sem)", [
            "API de scoring + intégration au workflow Fraud Ops.",
            "Tableau de bord d'investigation (vues graphe interactives).",
            "Shadow scoring puis activation progressive (10 % → 100 %).",
        ]),
    ),
    "stack": {
        "Données": "Snowflake / BigQuery, dbt, Pandas, PyArrow",
        "Graphes": "NetworkX, Neo4j ou Memgraph, DGL ou PyTorch Geometric",
        "Modèles": "LightGBM, scikit-learn, SHAP",
        "Serving": "FastAPI, Redis, Docker, Kubernetes",
        "Monitoring": "Prometheus, Grafana, Evidently AI",
    },
    "prereq": [
        "Maîtrise des modèles tabulaires déséquilibrés (techniques de sampling, métriques PR).",
        "Bases théoriques des graphes et de la propagation de scores.",
        "Connaissances AML / KYC (typologies de blanchiment).",
        "Esprit produit pour la collaboration avec les analystes Fraude.",
    ],
})

PROJECTS.append({
    "code": "1.2", "category": "1. Risque & Fraude",
    "title": "Chargeback prediction",
    "level": "INTERMÉDIAIRE", "duration": "4-6 semaines",
    "problem": "70 % des chargebacks sont contestables mais arrivent trop tard pour être défendus. Coût direct moyen : 20 à 100 $ par incident en plus du montant litigieux.",
    "roadmap": _rm(
        _phase("Phase 1 — Cadrage (1 sem)", [
            "Récupérer l'historique des chargebacks 12-24 mois avec horodatage.",
            "Cartographier les motifs (fraud, product not received, duplicate, etc.).",
            "Définir la fenêtre de prédiction (typiquement 30 à 120 jours).",
        ]),
        _phase("Phase 2 — Features & modélisation (2 sem)", [
            "Features marchand (taux historique, MCC, géo) + client + contexte transaction.",
            "Modèle binaire calibré (LightGBM + isotonique).",
            "Évaluation hold-out temporel avec PR AUC et lift @ top 5 %.",
        ]),
        _phase("Phase 3 — Décision (1-2 sem)", [
            "Seuils définis par coût/bénéfice métier (économie attendue par alerte).",
            "Workflow d'action : pre-emptive refund, contact client, collecte preuves.",
        ]),
        _phase("Phase 4 — Déploiement (1 sem)", [
            "Batch quotidien sur transactions des 7 derniers jours.",
            "Intégration au système de gestion des disputes.",
            "Mesure A/B vs groupe contrôle.",
        ]),
    ),
    "stack": {
        "Données": "PostgreSQL, dbt, Pandas",
        "Modèles": "LightGBM, scikit-learn, SHAP",
        "Pipeline": "Airflow ou Prefect",
        "Serving": "Batch (Airflow) + API REST légère",
        "Monitoring": "MLflow, dashboards Metabase",
    },
    "prereq": [
        "Connaissance des schémas carte (Visa/Mastercard reason codes).",
        "Modélisation binaire calibrée et seuillage coût-sensible.",
        "Notion d'analyse A/B test rigoureuse.",
    ],
})

PROJECTS.append({
    "code": "1.3", "category": "1. Risque & Fraude",
    "title": "Risk-Based Authentication / 3DS dynamique",
    "level": "SENIOR", "duration": "6-8 semaines",
    "problem": "Forcer le 3D-Secure sur 100 % des transactions tue la conversion de 5 à 15 points. Décider quand challenger l'utilisateur est un compromis fraude/UX critique.",
    "roadmap": _rm(
        _phase("Phase 1 — Cadrage règlementaire (1 sem)", [
            "Étude des exigences PSD2 / SCA (exemptions TRA, low value, MIT).",
            "Calcul du budget fraude par tranche de montant.",
        ]),
        _phase("Phase 2 — Scoring de risque (2 sem)", [
            "Modèle léger en latence < 50 ms : device, geo, vélocité, comportement.",
            "Calibration des seuils par segment marchand et tranche.",
        ]),
        _phase("Phase 3 — Décision multi-niveaux (1-2 sem)", [
            "Frictionless / OTP / biométrie selon le score et l'éligibilité TRA.",
            "Logique de fallback en cas d'échec d'un canal d'auth.",
        ]),
        _phase("Phase 4 — Intégration & A/B (2 sem)", [
            "Intégration au flow ACS / 3DS Server.",
            "A/B test contre la politique actuelle (conversion vs fraude).",
        ]),
    ),
    "stack": {
        "Modèle": "LightGBM ou logistic régression calibrée",
        "Serving": "FastAPI low-latency, Redis pour state device",
        "Intégration": "3DS Server (Netcetera, GPayments), ACS",
        "Monitoring": "Prometheus, observabilité OpenTelemetry",
        "Conformité": "Logs audit immuables (S3 Object Lock)",
    },
    "prereq": [
        "Très bonne connaissance PSD2 / SCA / EBA RTS.",
        "Latence et SLO stricts (< 50 ms p99).",
        "Compréhension fine du tunnel de paiement et des chiffres de conversion.",
    ],
})

PROJECTS.append({
    "code": "1.4", "category": "1. Risque & Fraude",
    "title": "Détection de manipulation de marché (spoofing, layering)",
    "level": "SENIOR", "duration": "10-12 semaines",
    "problem": "Les régulations MAR / MiFID II imposent la détection de manipulation (spoofing, layering, wash trading). Les amendes dépassent 100 M€ en cas de manquement.",
    "roadmap": _rm(
        _phase("Phase 1 — Cadrage & typologies (2 sem)", [
            "Recenser typologies réglementaires et exemples internes.",
            "Définir granularité (ordre / sous-ordre / fill).",
        ]),
        _phase("Phase 2 — Reconstruction carnet d'ordres (2-3 sem)", [
            "Replay des messages FIX pour reconstruire le carnet niveau par niveau.",
            "Features microstructure : imbalance, cancel rate, lifetime ordre.",
        ]),
        _phase("Phase 3 — Détection (3-4 sem)", [
            "Règles déterministes (spoofing : annulation > 80 % à < 1 s).",
            "Modèle non supervisé (Isolation Forest, autoencoder).",
        ]),
        _phase("Phase 4 — Workflow d'alerte (2 sem)", [
            "Interface analystes Surveillance avec replay visuel du carnet.",
            "Traçabilité réglementaire des décisions.",
        ]),
    ),
    "stack": {
        "Ingestion": "Kafka, Flink ou Spark Streaming",
        "Stockage": "Parquet partitionné + KDB+ pour requêtes tick",
        "Modèles": "scikit-learn, PyOD, anomalib",
        "UI": "Streamlit ou Bokeh pour visualisation carnet",
        "Conformité": "Logs WORM, signatures cryptographiques",
    },
    "prereq": [
        "Microstructure de marché et carnet d'ordres.",
        "Streaming temps réel à haut débit.",
        "Connaissance de MAR / MAD II / MiFID II.",
    ],
})

# ============================================================================
# 2. CRÉDIT & UNDERWRITING
# ============================================================================
PROJECTS.append({
    "code": "2.1", "category": "2. Crédit & Underwriting",
    "title": "Scoring crédit sur données alternatives",
    "level": "INTERMÉDIAIRE", "duration": "8-10 semaines",
    "problem": "1,7 milliard d'adultes sans historique bancaire (« credit invisible »). Sans alternative data, ils sont systématiquement refusés.",
    "roadmap": _rm(
        _phase("Phase 1 — Sourcing & partenariats (2 sem)", [
            "Identifier sources : mobile money, télécom, e-commerce, géolocalisation.",
            "Cadrer la légalité (consentement explicite, RGPD).",
        ]),
        _phase("Phase 2 — Feature engineering (2-3 sem)", [
            "Régularité des recharges télécom, stabilité géographique.",
            "Patterns de dépenses mobile money (réseaux, fréquence).",
        ]),
        _phase("Phase 3 — Modèle & XAI (3 sem)", [
            "Gradient boosting calibré, validation croisée temporelle.",
            "SHAP par décision (exigence régulateur : explicabilité individuelle).",
            "Tests de fairness par groupe protégé.",
        ]),
        _phase("Phase 4 — Déploiement (1-2 sem)", [
            "API de scoring + reason codes en sortie.",
            "Backtesting réglementaire (vintage analysis).",
        ]),
    ),
    "stack": {
        "Données": "Kafka pour ingestion, Snowflake, dbt",
        "Modèles": "LightGBM, XGBoost, SHAP, fairlearn",
        "Serving": "FastAPI, Docker",
        "Monitoring": "MLflow, drift PSI, fairness alerts",
        "Conformité": "Audit trail, model card, reason codes",
    },
    "prereq": [
        "Modélisation crédit (PD, scorecards, vintage analysis).",
        "XAI obligatoire (SHAP) et fairness (DPD, EO).",
        "Sensibilité RGPD et consentement.",
    ],
})

PROJECTS.append({
    "code": "2.2", "category": "2. Crédit & Underwriting",
    "title": "Early Warning System (détresse financière)",
    "level": "INTERMÉDIAIRE", "duration": "6-8 semaines",
    "problem": "Les banques attendent l'impayé pour réagir, alors qu'on peut anticiper 60 à 90 jours à l'avance. Coût d'un défaut évité : 5 000 à 50 000 € par client retail.",
    "roadmap": _rm(
        _phase("Phase 1 — Définition cible (1 sem)", [
            "Définir l'événement (impayé J+30, restructuration, surendettement).",
            "Horizons multiples : J+30, J+60, J+90.",
        ]),
        _phase("Phase 2 — Features (2 sem)", [
            "Solde moyen, dépassements, fréquence des refus carte.",
            "Variations de patterns sur 3 mois glissants.",
        ]),
        _phase("Phase 3 — Modélisation (2 sem)", [
            "Modèle de survie (Cox, Random Survival Forest) ou multi-horizon binaire.",
            "Évaluation : C-index, time-dependent AUC.",
        ]),
        _phase("Phase 4 — Activation (1-2 sem)", [
            "Routage vers équipe Recovery / Customer Care selon score.",
            "Mesure d'effet : taux de défaut sur cas traités vs contrôle.",
        ]),
    ),
    "stack": {
        "Données": "Data warehouse + features comportementales 90j",
        "Modèles": "lifelines, scikit-survival, LightGBM",
        "Pipeline": "Airflow batch quotidien",
        "Action": "CRM intégré (Salesforce, HubSpot), notifications",
        "Monitoring": "Drift + uplift mesuré",
    },
    "prereq": [
        "Modèles de survie (censure à droite, fonctions de hasard).",
        "Compréhension du métier Collection / Recovery.",
        "Évaluation rigoureuse (uplift modeling idéalement).",
    ],
})

PROJECTS.append({
    "code": "2.3", "category": "2. Crédit & Underwriting",
    "title": "Pricing dynamique du taux d'intérêt",
    "level": "SENIOR", "duration": "10-12 semaines",
    "problem": "Un taux unique laisse de la marge sur les bons profils et perd les mauvais. Optimiser le pricing à risque constant peut dégager plusieurs M€ de marge.",
    "roadmap": _rm(
        _phase("Phase 1 — Modèle de risque (3 sem)", [
            "Probabilité de défaut individuelle (PD).",
            "Loss Given Default (LGD), Exposure At Default (EAD).",
        ]),
        _phase("Phase 2 — Élasticité demande au prix (3 sem)", [
            "Modèle d'acceptation du prêt en fonction du taux (logistic).",
            "Inférence causale (DID, IV) pour éviter les biais de sélection.",
        ]),
        _phase("Phase 3 — Optimisation (2 sem)", [
            "Maximiser marge × acceptation sous contrainte taux d'usure.",
            "Caps par segment pour des raisons réglementaires et de fairness.",
        ]),
        _phase("Phase 4 — A/B & déploiement (2 sem)", [
            "Pilot sur segment réduit, mesure marge nette et conversion.",
            "Roll-out par cohorte.",
        ]),
    ),
    "stack": {
        "Modèles": "scikit-learn, lifelines, EconML, DoWhy",
        "Optimisation": "SciPy, CVXPY",
        "A/B": "Plateforme expérimentation (Optimizely, Eppo, ou interne)",
        "Conformité": "Documentation modèle, validation MRM",
    },
    "prereq": [
        "Modèles PD/LGD/EAD (Bâle III).",
        "Inférence causale et économétrie.",
        "Optimisation sous contrainte.",
    ],
})

PROJECTS.append({
    "code": "2.4", "category": "2. Crédit & Underwriting",
    "title": "BNPL Approval Engine (Buy Now Pay Later)",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Décision crédit en < 200 ms au checkout, avec très peu de données. Marché en forte croissance (Klarna, Alma, Affirm).",
    "roadmap": _rm(
        _phase("Phase 1 — Cadrage (1 sem)", [
            "Politique de risque (montants max, durées, taux refus cibles).",
            "Sources de données disponibles au checkout.",
        ]),
        _phase("Phase 2 — Règles + ML (2 sem)", [
            "Règles dures : âge, blacklist, montant max.",
            "Modèle ML calibré sur historique + données enrichies.",
        ]),
        _phase("Phase 3 — Decision Engine (1-2 sem)", [
            "Architecture identique au projet anti-fraude.",
            "Latence < 200 ms p99, fallback dégradé.",
        ]),
        _phase("Phase 4 — Monitoring (1 sem)", [
            "Métriques : taux d'approbation, taux de défaut par cohorte.",
            "Drift et performance par segment marchand.",
        ]),
    ),
    "stack": {
        "Modèle": "LightGBM, scikit-learn",
        "API": "FastAPI, Redis",
        "Pipeline": "Airflow pour réentraînement mensuel",
        "Monitoring": "MLflow, Grafana",
    },
    "prereq": [
        "Architecture règles + ML (vibe du projet anti-fraude).",
        "Pricing du risque sur petits prêts court terme.",
    ],
})



# ============================================================================
# 3. AML / KYC / Compliance
# ============================================================================
PROJECTS.append({
    "code": "3.1", "category": "3. AML / KYC / Compliance",
    "title": "KYC automatisé (OCR + LLM)",
    "level": "INTERMÉDIAIRE", "duration": "6-8 semaines",
    "problem": "La revue manuelle d'un dossier KYC coûte 5 à 50 € et prend 24 à 72 h. Automatisable à 80-90 %.",
    "roadmap": _rm(
        _phase("Phase 1 — Pipeline OCR (2 sem)", [
            "OCR sur pièce d'identité (MRZ, données structurées).",
            "Détection de falsification : cohérence polices, métadonnées EXIF.",
        ]),
        _phase("Phase 2 — Match selfie / liveness (2 sem)", [
            "Comparaison faciale (ArcFace, FaceNet).",
            "Challenge de liveness pour bloquer les photos de photos.",
        ]),
        _phase("Phase 3 — LLM pour justificatifs (2 sem)", [
            "Extraction structurée des factures (Pydantic schema).",
            "Vérification cohérence adresse vs déclaration.",
        ]),
        _phase("Phase 4 — Workflow décisionnel (1-2 sem)", [
            "Auto-approve si tous les contrôles passent.",
            "Routage manuel sinon, avec contexte enrichi pour analyste.",
        ]),
    ),
    "stack": {
        "OCR": "Tesseract, PaddleOCR, Mistral OCR API",
        "Vision": "OpenCV, FaceNet, DeepFace",
        "LLM": "OpenAI / Mistral / Claude API, instructor (output structuré)",
        "Workflow": "Temporal, Camunda ou n8n",
        "Conformité": "Audit trail + signature des décisions",
    },
    "prereq": [
        "Vision par ordinateur (reconnaissance, anti-spoof).",
        "LLM ops (prompt engineering, validation, eval).",
        "Connaissance des standards KYC (eIDAS, AML 5/6).",
    ],
})

PROJECTS.append({
    "code": "3.2", "category": "3. AML / KYC / Compliance",
    "title": "Sanctions screening intelligent (PEP / OFAC)",
    "level": "INTERMÉDIAIRE", "duration": "4-6 semaines",
    "problem": "Listes OFAC/UE/UN génèrent énormément de faux positifs à cause des translittérations (Mohamed/Mohammad/Muhammad). Analystes saturés.",
    "roadmap": _rm(
        _phase("Phase 1 — Sourcing listes (1 sem)", [
            "Ingestion automatisée OFAC, UE, UN, HMT, locale.",
            "Détection des mises à jour quotidiennes.",
        ]),
        _phase("Phase 2 — Matching intelligent (2 sem)", [
            "Fuzzy matching : Jaro-Winkler + double metaphone.",
            "Embedding phonétique multilingue.",
        ]),
        _phase("Phase 3 — Scoring contextuel (1-2 sem)", [
            "Score combinant nom, date de naissance, nationalité.",
            "Classification match / close match / no match.",
        ]),
        _phase("Phase 4 — UI analyste (1 sem)", [
            "Interface de revue avec score + justification.",
            "Feedback loop pour améliorer le modèle.",
        ]),
    ),
    "stack": {
        "Matching": "RapidFuzz, jellyfish, Sentence Transformers",
        "Index": "Elasticsearch ou OpenSearch",
        "API": "FastAPI",
        "UI": "Streamlit ou React léger",
        "Conformité": "Logs des décisions et de l'audit",
    },
    "prereq": [
        "NLP / fuzzy matching multilingue.",
        "Connaissance AML : PEP, sanctions, screening obligatoire.",
    ],
})

PROJECTS.append({
    "code": "3.3", "category": "3. AML / KYC / Compliance",
    "title": "Détection de réseaux frauduleux par GNN",
    "level": "SENIOR", "duration": "10-12 semaines",
    "problem": "La fraude organisée passe par 10-50 comptes complices, invisible compte par compte. Démantèlement d'anneaux entiers est l'objectif.",
    "roadmap": _rm(
        _phase("Phase 1 — Construction graphe (2 sem)", [
            "Modélisation comptes, transactions, devices comme graphe hétérogène.",
            "Stockage Neo4j ou Memgraph.",
        ]),
        _phase("Phase 2 — Features & embeddings (3 sem)", [
            "Métriques classiques : pagerank, betweenness, communautés (Louvain).",
            "Embeddings nœuds (node2vec, GraphSAGE).",
        ]),
        _phase("Phase 3 — GNN supervisé (3-4 sem)", [
            "Architecture GraphSAGE ou GAT.",
            "Apprentissage semi-supervisé (peu de labels positifs).",
        ]),
        _phase("Phase 4 — Détection communauté & alerting (2 sem)", [
            "Détection de cliques suspectes.",
            "Workflow d'investigation visuel.",
        ]),
    ),
    "stack": {
        "Graphe DB": "Neo4j, Memgraph, ou TigerGraph",
        "GNN": "DGL ou PyTorch Geometric",
        "Features": "NetworkX, Graph-tool",
        "UI": "Bloomberg Graph, GraphXR, ou custom",
        "Pipeline": "Spark pour batch, Kafka pour streaming",
    },
    "prereq": [
        "Théorie des graphes et algorithmes (Louvain, Leiden, GNN).",
        "PyTorch et frameworks GNN.",
        "Conscience AML (typologies de layering, structuring).",
    ],
})

PROJECTS.append({
    "code": "3.4", "category": "3. AML / KYC / Compliance",
    "title": "UBO Discovery (Beneficial Ownership)",
    "level": "INTERMÉDIAIRE", "duration": "4-6 semaines",
    "problem": "Remonter à la personne physique qui contrôle une entreprise est obligatoire (5e directive AML) mais souvent caché derrière 4-5 niveaux de holdings.",
    "roadmap": _rm(
        _phase("Phase 1 — Sourcing référentiels (1-2 sem)", [
            "Ingestion : registres nationaux (INSEE, Companies House), data brokers.",
            "Normalisation des entités.",
        ]),
        _phase("Phase 2 — Graphe de propriété (2 sem)", [
            "Modélisation participations pondérées par %.",
            "Parcours pondéré pour cumuler les détentions indirectes.",
        ]),
        _phase("Phase 3 — Algorithme UBO (1-2 sem)", [
            "Calcul du contrôle effectif (seuil 25 %).",
            "Détection contrôle indirect via majorité des votes.",
        ]),
        _phase("Phase 4 — UI & explicabilité (1 sem)", [
            "Visualisation arborescence avec chemins de détention.",
            "Export PDF pour reporting compliance.",
        ]),
    ),
    "stack": {
        "Graphe": "NetworkX ou Neo4j",
        "Sources": "INSEE API, OpenCorporates, Sirene",
        "UI": "D3.js ou Cytoscape pour visualisation",
        "API": "FastAPI",
    },
    "prereq": [
        "Algorithmes de graphe (DFS, parcours pondéré).",
        "Connaissance des structures juridiques (holdings, SPV).",
    ],
})

# ============================================================================
# 4. EXPÉRIENCE CLIENT & PERSONNALISATION
# ============================================================================
PROJECTS.append({
    "code": "4.1", "category": "4. Client & Personnalisation",
    "title": "Catégorisation automatique des transactions (PFM)",
    "level": "JUNIOR", "duration": "3-4 semaines",
    "problem": "Aucun client ne tague ses transactions manuellement, donc le PFM ne sert à rien. Engagement applicatif x2-3 si réussi.",
    "roadmap": _rm(
        _phase("Phase 1 — Référentiel catégories (1 sem)", [
            "Définir 30-50 catégories métier.",
            "Mapping MCC initial.",
        ]),
        _phase("Phase 2 — Modèle texte (1-2 sem)", [
            "Tokenisation du libellé bancaire.",
            "Classification (logistic regression sur TF-IDF ou DistilBERT).",
        ]),
        _phase("Phase 3 — Règles hybrides (1 sem)", [
            "Règles MCC pour overrides certains.",
            "Apprentissage par feedback utilisateur.",
        ]),
        _phase("Phase 4 — Intégration mobile (1 sem)", [
            "API de catégorisation batch + temps réel.",
            "Override manuel par l'utilisateur, propagation au modèle.",
        ]),
    ),
    "stack": {
        "Modèle": "scikit-learn ou Hugging Face DistilBERT",
        "Données": "Pandas, dbt",
        "API": "FastAPI",
        "Feedback": "Stockage Redis pour overrides utilisateur",
    },
    "prereq": [
        "Classification texte basique.",
        "Modèle léger contraint en latence.",
        "Sens produit (catégories qui parlent à l'utilisateur).",
    ],
})

PROJECTS.append({
    "code": "4.2", "category": "4. Client & Personnalisation",
    "title": "Prédiction de churn + actions de rétention",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "On perd 10-25 % de clients par an. Coût d'acquisition élevé (CAC > 100 € en banque). Anticiper le départ permet d'intervenir.",
    "roadmap": _rm(
        _phase("Phase 1 — Définition churn (1 sem)", [
            "Critères : clôture, inactivité 90 j, ou solde < seuil.",
            "Horizons : J+60, J+90.",
        ]),
        _phase("Phase 2 — Modélisation (2-3 sem)", [
            "Classification binaire ou modèle de survie.",
            "Idéalement uplift modeling (qui réagit à l'action).",
        ]),
        _phase("Phase 3 — Moteur d'action (1-2 sem)", [
            "Mapping score → action (offre, contact, geste commercial).",
            "Limite de saturation par canal.",
        ]),
        _phase("Phase 4 — A/B test (1 sem)", [
            "Mesure d'efficacité (rétention vs contrôle).",
            "Optimisation continue par segment.",
        ]),
    ),
    "stack": {
        "Modèle": "LightGBM, CausalML, scikit-survival",
        "Pipeline": "Airflow batch hebdo",
        "Action": "CRM, email/SMS, push mobile",
        "Mesure": "Plateforme A/B test, dashboards",
    },
    "prereq": [
        "Uplift modeling (idéalement).",
        "Inférence causale / A/B test.",
        "Sens commercial.",
    ],
})

PROJECTS.append({
    "code": "4.3", "category": "4. Client & Personnalisation",
    "title": "Recommandation de produits (cross-sell)",
    "level": "INTERMÉDIAIRE", "duration": "6-8 semaines",
    "problem": "Un client multi-équipé est 5x plus rentable. Recommander le bon produit au bon moment double le taux d'équipement.",
    "roadmap": _rm(
        _phase("Phase 1 — Catalogue produits (1 sem)", [
            "Modélisation produits avec features.",
            "Règles d'éligibilité réglementaires (un surendetté n'a pas droit au crédit).",
        ]),
        _phase("Phase 2 — Modèle (3 sem)", [
            "Two-tower model ou collaborative filtering.",
            "Contraintes : éligibilité, diversité, fatigue.",
        ]),
        _phase("Phase 3 — Re-ranking métier (1-2 sem)", [
            "Pondération marges, KPI commerciaux.",
            "Garde-fous compliance (devoir de conseil MiFID).",
        ]),
        _phase("Phase 4 — Activation (1-2 sem)", [
            "Affichage app + emailings ciblés.",
            "Mesure conversion par segment.",
        ]),
    ),
    "stack": {
        "Modèle": "TensorFlow Recommenders, implicit, Merlin",
        "Données": "Snowflake, dbt, feature store",
        "Serving": "FastAPI, Redis cache",
        "Activation": "CRM, push, in-app",
    },
    "prereq": [
        "Recommandation (CF, two-tower, séquentiel).",
        "Connaissance MiFID II (conseil et adéquation).",
    ],
})

PROJECTS.append({
    "code": "4.4", "category": "4. Client & Personnalisation",
    "title": "Chatbot RAG bancaire (doc interne + données client)",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Un conseiller met 5-15 min à trouver la réponse dans la doc. RAG bien fait divise par 3 le temps de traitement.",
    "roadmap": _rm(
        _phase("Phase 1 — Sourcing & vectorisation (2 sem)", [
            "Ingestion Confluence, FAQ, base produits.",
            "Chunking + embeddings + base vectorielle.",
        ]),
        _phase("Phase 2 — Retrieval (1-2 sem)", [
            "Hybrid search (BM25 + embeddings).",
            "Re-ranking et déduplication.",
        ]),
        _phase("Phase 3 — Génération & garde-fous (2 sem)", [
            "Prompt structuré, citation des sources.",
            "Garde-fous : pas de conseil financier non régulé, pas de fuite PII.",
        ]),
        _phase("Phase 4 — Eval & monitoring (1 sem)", [
            "Eval automatique (RAGAS, faithfulness).",
            "Métriques satisfaction utilisateur.",
        ]),
    ),
    "stack": {
        "LLM": "OpenAI / Mistral / Claude (selon contraintes RGPD)",
        "Vector DB": "Qdrant, Weaviate, pgvector",
        "Framework": "LangChain, LlamaIndex ou Haystack",
        "Eval": "RAGAS, DeepEval",
        "UI": "Conversational widget (Botpress, Rasa, ou custom)",
    },
    "prereq": [
        "RAG en production (chunking, eval, garde-fous).",
        "Prompt engineering rigoureux.",
        "Conscience RGPD pour LLM externes.",
    ],
})



# ============================================================================
# 5. CYBERSÉCURITÉ
# ============================================================================
PROJECTS.append({
    "code": "5.1", "category": "5. Cybersécurité",
    "title": "Account Takeover Detection (ATO)",
    "level": "SENIOR", "duration": "6-8 semaines",
    "problem": "Un compte volé fait 10x plus de dégâts qu'une carte volée. Détection au login indispensable.",
    "roadmap": _rm(
        _phase("Phase 1 — Telemetry & device (2 sem)", [
            "Collecte device fingerprint, IP, geo, ASN.",
            "Comportement : vitesse de frappe, navigation, mouvement souris.",
        ]),
        _phase("Phase 2 — Modèle non-supervisé (2 sem)", [
            "Profil comportemental par utilisateur (baseline).",
            "Détection d'anomalies (Isolation Forest, autoencoder).",
        ]),
        _phase("Phase 3 — Modèle supervisé (1-2 sem)", [
            "Apprentissage sur cas avérés d'ATO.",
            "Combinaison avec score non-supervisé.",
        ]),
        _phase("Phase 4 — Step-up auth (1-2 sem)", [
            "Challenge OTP / biométrie selon score.",
            "Fallback session bloquée + contact support.",
        ]),
    ),
    "stack": {
        "Streaming": "Kafka, Flink",
        "Modèles": "scikit-learn, PyOD, TensorFlow (autoencoder)",
        "Serving": "FastAPI, Redis pour state utilisateur",
        "Auth": "Intégration IAM (Auth0, Keycloak)",
    },
    "prereq": [
        "Streaming temps réel à haut débit.",
        "Anomaly detection.",
        "Connaissance sécurité (OAuth, OWASP).",
    ],
})

PROJECTS.append({
    "code": "5.2", "category": "5. Cybersécurité",
    "title": "Bot / Scraping detection",
    "level": "INTERMÉDIAIRE", "duration": "4-6 semaines",
    "problem": "Bots saturent les formulaires (simulation crédit, card-testing), faussent les analytics et la conversion.",
    "roadmap": _rm(
        _phase("Phase 1 — Telemetry frontale (1 sem)", [
            "Canvas fingerprint, WebGL, fontes, audio context.",
            "Patterns d'interaction (mouvements souris, scrolling).",
        ]),
        _phase("Phase 2 — Modèle (2 sem)", [
            "Features extraites du device + comportement.",
            "Classifieur calibré.",
        ]),
        _phase("Phase 3 — Décision (1 sem)", [
            "Challenge silencieux (PoW), reCAPTCHA, ou blocage.",
            "Allowlist clients API légitimes.",
        ]),
        _phase("Phase 4 — Iteration (1-2 sem)", [
            "Bot/human ratio par endpoint.",
            "Adaptation aux nouveaux bots.",
        ]),
    ),
    "stack": {
        "Frontend": "FingerprintJS, custom JS",
        "Backend": "FastAPI ou middleware Cloudflare Workers",
        "Modèle": "LightGBM, scikit-learn",
        "Edge": "Cloudflare, Akamai, Fastly",
    },
    "prereq": [
        "Sécurité web (fingerprinting, attaques bots).",
        "Latence frontend / edge.",
    ],
})

PROJECTS.append({
    "code": "5.3", "category": "5. Cybersécurité",
    "title": "Phishing URL detection",
    "level": "INTERMÉDIAIRE", "duration": "4-5 semaines",
    "problem": "Clones de l'app/site captent credentials. Détection proactive permet le takedown rapide.",
    "roadmap": _rm(
        _phase("Phase 1 — Sourcing URLs (1 sem)", [
            "Domaines fraîchement enregistrés (whois + RDAP).",
            "Variations typosquatting de la marque.",
        ]),
        _phase("Phase 2 — Features & modèle (2 sem)", [
            "Features lexicales URL + screenshot vision.",
            "Classifieur multimodal (texte + image).",
        ]),
        _phase("Phase 3 — Workflow takedown (1 sem)", [
            "Déclaration aux registrars et hébergeurs.",
            "Notifications clients impactés.",
        ]),
        _phase("Phase 4 — Boucle d'amélioration (1 sem)", [
            "Feedback des analystes sur faux positifs.",
            "Veille continue.",
        ]),
    ),
    "stack": {
        "Crawl": "Playwright, requests-html",
        "Modèles": "scikit-learn (URL), CLIP (image)",
        "Sources": "CertStream, Phishtank, OpenPhish",
        "API": "FastAPI + workers Celery",
    },
    "prereq": [
        "Vision par ordinateur (CLIP, classification image).",
        "Sécurité offensive (typosquatting, homoglyphes).",
    ],
})

# ============================================================================
# 6. PLATEFORME & OUTILS INTERNES
# ============================================================================
PROJECTS.append({
    "code": "6.1", "category": "6. Plateforme & Outils internes",
    "title": "Feature Store interne",
    "level": "SENIOR", "duration": "10-14 semaines",
    "problem": "Chaque équipe ML recalcule les mêmes features (solde 30j, vélocité…) avec définitions divergentes. Bugs, time-to-model x2-3.",
    "roadmap": _rm(
        _phase("Phase 1 — Cadrage (2 sem)", [
            "Inventaire des features utilisées par toutes les équipes.",
            "Définition des SLAs : freshness, latency, throughput.",
        ]),
        _phase("Phase 2 — Storage (3 sem)", [
            "Offline store (Parquet/Snowflake) pour entraînement.",
            "Online store (Redis/DynamoDB) pour serving.",
            "Synchronisation offline/online.",
        ]),
        _phase("Phase 3 — SDK & catalogue (3-4 sem)", [
            "API Python + CLI pour pousser et consommer.",
            "Catalogue documenté, propriété par équipe.",
        ]),
        _phase("Phase 4 — Adoption (2-3 sem)", [
            "Migration progressive des projets existants.",
            "Monitoring de freshness et adoption.",
        ]),
    ),
    "stack": {
        "Feature Store": "Feast, Tecton, ou Hopsworks",
        "Storage offline": "Snowflake, BigQuery, S3 + Parquet",
        "Storage online": "Redis, DynamoDB, ScyllaDB",
        "Streaming": "Kafka, Flink",
        "Catalogue": "DataHub, Amundsen, ou interne",
    },
    "prereq": [
        "Data platform et orchestration.",
        "Sens produit (DX pour ML engineers).",
        "Patience pour la migration et l'adoption.",
    ],
})

PROJECTS.append({
    "code": "6.2", "category": "6. Plateforme & Outils internes",
    "title": "Plateforme de monitoring ML centralisée",
    "level": "INTERMÉDIAIRE", "duration": "6-8 semaines",
    "problem": "Chaque modèle a son monitoring artisanal, drifts non détectés. Une plateforme unifiée est un game changer.",
    "roadmap": _rm(
        _phase("Phase 1 — SDK de logging (2 sem)", [
            "API Python simple pour logger predictions + features + ground truth.",
            "Batching pour ne pas impacter la latence.",
        ]),
        _phase("Phase 2 — Calculs drift & performance (2 sem)", [
            "PSI sur features, distribution des prédictions.",
            "Performance vs ground truth après délai (chargeback, etc.).",
        ]),
        _phase("Phase 3 — Alerting (1-2 sem)", [
            "Seuils par modèle, notifications Slack/PagerDuty.",
            "Auto-tickets dans le système de suivi.",
        ]),
        _phase("Phase 4 — UI (1-2 sem)", [
            "Dashboards par modèle.",
            "Vue consolidée pour la direction.",
        ]),
    ),
    "stack": {
        "Plateforme": "Evidently AI, WhyLabs, Arize ou interne",
        "Storage": "ClickHouse ou Druid pour métriques",
        "Alerting": "Alertmanager, Slack, PagerDuty",
        "UI": "Grafana, Superset, ou React",
    },
    "prereq": [
        "Statistiques de drift (PSI, KS, KL).",
        "Observabilité moderne (métriques, traces).",
    ],
})

PROJECTS.append({
    "code": "6.3", "category": "6. Plateforme & Outils internes",
    "title": "Plateforme de backtesting standardisée",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "Chaque DS refait son framework de backtesting. Impossible de comparer deux modèles équitablement.",
    "roadmap": _rm(
        _phase("Phase 1 — Spécification (2 sem)", [
            "Split temporel anti-leakage strict.",
            "Métriques business + techniques standardisées.",
        ]),
        _phase("Phase 2 — Eval harness (3 sem)", [
            "Pipeline reproductible avec seed.",
            "Comparaison vs baseline et modèle en prod.",
        ]),
        _phase("Phase 3 — Leaderboard (2 sem)", [
            "Stockage des runs, comparaison.",
            "Documentation automatique des résultats.",
        ]),
        _phase("Phase 4 — Intégration MRM (1-2 sem)", [
            "Export rapport de validation pour Risk.",
            "Conformité SR 11-7 / TRIM.",
        ]),
    ),
    "stack": {
        "Tracking": "MLflow ou Weights & Biases",
        "Pipeline": "Metaflow, Kedro ou ZenML",
        "Stockage": "S3 + Parquet versionné (DVC, LakeFS)",
        "UI": "MLflow UI ou Streamlit custom",
    },
    "prereq": [
        "Évaluation rigoureuse (time-series CV, leakage).",
        "Connaissance MRM (Model Risk Management).",
    ],
})

PROJECTS.append({
    "code": "6.4", "category": "6. Plateforme & Outils internes",
    "title": "Plateforme de données synthétiques",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "Impossible d'envoyer des données réelles à un prestataire externe. Bloque les PoC et la collaboration.",
    "roadmap": _rm(
        _phase("Phase 1 — Cas d'usage (1-2 sem)", [
            "Recenser les besoins (PoC partenaires, dev, tests).",
            "Définir niveau de fidélité requis.",
        ]),
        _phase("Phase 2 — Génération (3-4 sem)", [
            "Approches : règles métier (comme notre projet anti-fraude), CTGAN, copules.",
            "Préservation des distributions et corrélations clés.",
        ]),
        _phase("Phase 3 — Tests privacy (2 sem)", [
            "Mesure du risque de re-identification.",
            "Differential privacy si exigence forte.",
        ]),
        _phase("Phase 4 — Plateforme self-service (1-2 sem)", [
            "API + UI pour générer des datasets à la demande.",
            "Catalogue des jeux disponibles.",
        ]),
    ),
    "stack": {
        "Generation": "SDV (CTGAN, TVAE), Gretel, Mostly AI",
        "Privacy": "diffprivlib, smartnoise",
        "Stockage": "S3 + Parquet, versionning DVC",
        "API": "FastAPI",
    },
    "prereq": [
        "Modèles génératifs (CTGAN, copules).",
        "Differential privacy.",
        "RGPD et risque de re-identification.",
    ],
})



# ============================================================================
# 7. INSURTECH
# ============================================================================
PROJECTS.append({
    "code": "A.1", "category": "7. Insurance / Insurtech",
    "title": "Détection de fraude à la déclaration de sinistre",
    "level": "INTERMÉDIAIRE", "duration": "6-8 semaines",
    "problem": "10-15 % des sinistres auto/MRH contiennent une part de fraude. Modèle multimodal nécessaire.",
    "roadmap": _rm(
        _phase("Phase 1 — Sourcing (1-2 sem)", [
            "Texte de la déclaration, photos, historique du sinistré.",
            "Réseau de garagistes et experts impliqués.",
        ]),
        _phase("Phase 2 — Modèle multimodal (3 sem)", [
            "NLP sur déclaration + Vision sur photos.",
            "Features comportementales et réseau.",
        ]),
        _phase("Phase 3 — Décision & UI (1-2 sem)", [
            "Routage vers expert humain selon score.",
            "Visualisation pour gestionnaires.",
        ]),
        _phase("Phase 4 — Backtesting (1 sem)", [
            "Mesure du gain S/P estimé.",
            "Suivi des disputes après refus.",
        ]),
    ),
    "stack": {
        "NLP": "Hugging Face (CamemBERT, FlauBERT)",
        "Vision": "CLIP, YOLO pour objets, ELA pour photo forensics",
        "Modèles": "LightGBM pour fusion, SHAP pour explication",
        "UI": "Interface gestionnaire (Streamlit ou React)",
    },
    "prereq": [
        "Multimodal NLP + Vision.",
        "Métier assurance (typologies fraude).",
    ],
})

PROJECTS.append({
    "code": "A.2", "category": "7. Insurance / Insurtech",
    "title": "Underwriting automatique en assurance emprunteur",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Questionnaires médicaux de 10-30 min, taux d'abandon élevé. Simplification réglementaire (loi Lemoine).",
    "roadmap": _rm(
        _phase("Phase 1 — Tarif actuariel (2 sem)", [
            "Modèle de mortalité par âge / sexe / fumeur.",
            "Calibration sur tables INSEE et internes.",
        ]),
        _phase("Phase 2 — Questionnaire court (1-2 sem)", [
            "Sélection des 3-5 questions à plus haut pouvoir discriminant.",
            "Workflow simplifié.",
        ]),
        _phase("Phase 3 — Décision (1 sem)", [
            "Acceptation / tarif majoré / refus.",
            "Renvoi médical pour cas limites.",
        ]),
        _phase("Phase 4 — Suivi (1 sem)", [
            "Mesure S/P par segment.",
            "Itération sur les questions.",
        ]),
    ),
    "stack": {
        "Actuariel": "Lifelines, statsmodels",
        "Modèle": "Logistic regression (interprétable obligatoire)",
        "API": "FastAPI",
        "Conformité": "Audit trail des décisions",
    },
    "prereq": [
        "Actuariat vie (tables de mortalité).",
        "Modèles interprétables et conformes.",
    ],
})

PROJECTS.append({
    "code": "A.3", "category": "7. Insurance / Insurtech",
    "title": "Telematics-based pricing (assurance auto)",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "Tarifer un jeune conducteur correctement sans le pénaliser à l'aveugle. Pricing comportemental.",
    "roadmap": _rm(
        _phase("Phase 1 — Capture données (2 sem)", [
            "Ingestion boîtier ou téléphone (accéléro, GPS).",
            "Calcul features : freinages brusques, vitesse, horaires.",
        ]),
        _phase("Phase 2 — Score de conduite (3 sem)", [
            "Modèle scoring agrégé sur fenêtre roulante.",
            "Pondération par contexte (météo, route).",
        ]),
        _phase("Phase 3 — Tarif dynamique (2 sem)", [
            "Lien score → ajustement de prime mensuel.",
            "Caps réglementaires (pas de hausse > X % / mois).",
        ]),
        _phase("Phase 4 — Pilot client (1-2 sem)", [
            "Onboarding mobile, gamification.",
            "Mesure du churn et de la sinistralité.",
        ]),
    ),
    "stack": {
        "Ingestion": "Kafka, AWS IoT Core",
        "Stockage": "TimescaleDB ou InfluxDB",
        "Modèles": "Gradient boosting, séries temporelles",
        "Mobile": "SDK iOS/Android",
    },
    "prereq": [
        "Données IoT et streaming.",
        "Métier actuariat auto.",
        "Sens UX (gamification de la conduite).",
    ],
})

PROJECTS.append({
    "code": "A.4", "category": "7. Insurance / Insurtech",
    "title": "Prédiction de récurrence de sinistre",
    "level": "INTERMÉDIAIRE", "duration": "4-6 semaines",
    "problem": "Un sinistré est 3x plus susceptible d'en déclarer un autre dans les 12 mois. Cibler les actions de prévention.",
    "roadmap": _rm(
        _phase("Phase 1 — Cadrage (1 sem)", [
            "Définition de la cible (J+365 sinistre identique).",
            "Recensement signaux post-sinistre.",
        ]),
        _phase("Phase 2 — Modélisation (2-3 sem)", [
            "Modèle de survie ou classification horizon.",
            "Features comportementales (paiements, prime).",
        ]),
        _phase("Phase 3 — Actions (1 sem)", [
            "Renforcement prévention (alarme, conseils).",
            "Réajustement tarif ou résiliation.",
        ]),
        _phase("Phase 4 — Mesure (1 sem)", [
            "Taux de récurrence vs contrôle.",
        ]),
    ),
    "stack": {
        "Modèle": "lifelines, scikit-survival, LightGBM",
        "Pipeline": "Airflow batch",
        "Action": "CRM, email/SMS",
    },
    "prereq": [
        "Modèles de survie.",
        "Métier assurance dommages.",
    ],
})

# ============================================================================
# 8. WEALTH / ROBO-ADVISOR
# ============================================================================
PROJECTS.append({
    "code": "B.1", "category": "8. Wealth / Robo-advisor",
    "title": "Allocation d'actifs personnalisée (robo-advisor)",
    "level": "SENIOR", "duration": "10-12 semaines",
    "problem": "Démocratiser le conseil patrimonial (Yomoni, Nalo). Allocation et rebalancing automatiques.",
    "roadmap": _rm(
        _phase("Phase 1 — Profilage MiFID (2 sem)", [
            "Questionnaire de connaissance & expérience.",
            "Profil de risque, horizon, objectifs.",
        ]),
        _phase("Phase 2 — Allocation (3 sem)", [
            "Optimisation mean-variance ou Black-Litterman.",
            "Contraintes (ESG, fiscalité, classe d'actifs).",
        ]),
        _phase("Phase 3 — Rebalancing (2 sem)", [
            "Bandes de tolérance par classe.",
            "Mécanique d'exécution (frais, fiscalité).",
        ]),
        _phase("Phase 4 — Backtesting & onboarding (3 sem)", [
            "Backtests sur 10 ans, scénarios de stress.",
            "Onboarding mobile fluide.",
        ]),
    ),
    "stack": {
        "Optim": "PyPortfolioOpt, CVXPY, SciPy",
        "Données marché": "Refinitiv, Bloomberg, ou data vendors",
        "Backtest": "vectorbt, Zipline-reloaded",
        "Mobile": "React Native ou Flutter",
        "Conformité": "Suitability MiFID II, archivage",
    },
    "prereq": [
        "Théorie moderne du portefeuille.",
        "Conformité MiFID II / suitability.",
        "Optimisation sous contrainte.",
    ],
})

PROJECTS.append({
    "code": "B.2", "category": "8. Wealth / Robo-advisor",
    "title": "Tax-loss harvesting automatique",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Gain net de 0,5 à 1,5 % par an sur un portefeuille bien optimisé fiscalement.",
    "roadmap": _rm(
        _phase("Phase 1 — Règles fiscales (1-2 sem)", [
            "FR : PFU, PEA, abattement durée, FIFO.",
            "Wash sale rules.",
        ]),
        _phase("Phase 2 — Scan quotidien (2 sem)", [
            "Détection moins-values latentes.",
            "Substituts pour préserver l'exposition.",
        ]),
        _phase("Phase 3 — Exécution (1 sem)", [
            "Ordres vente / rachat orchestrés.",
            "Suivi des fenêtres anti-wash.",
        ]),
        _phase("Phase 4 — Reporting fiscal (1-2 sem)", [
            "Génération formulaire 2086 / 2074.",
        ]),
    ),
    "stack": {
        "Calcul": "Python + Pandas",
        "Pipeline": "Airflow",
        "Reporting": "ReportLab pour PDF",
    },
    "prereq": [
        "Fiscalité française des titres.",
        "Microstructure marché (substituts).",
    ],
})

PROJECTS.append({
    "code": "B.3", "category": "8. Wealth / Robo-advisor",
    "title": "Goal-based planning (planification par objectifs)",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Épargner sans objectif est démotivant. L'utilisateur veut savoir s'il atteindra son achat immo ou sa retraite.",
    "roadmap": _rm(
        _phase("Phase 1 — Modélisation objectifs (1 sem)", [
            "Type d'objectif, horizon, montant cible.",
            "Inflation et rendement attendu.",
        ]),
        _phase("Phase 2 — Monte Carlo (2 sem)", [
            "Simulation 10 000 trajectoires sur rendements projetés.",
            "Probabilité d'atteinte par scénario.",
        ]),
        _phase("Phase 3 — Recommandation (1-2 sem)", [
            "Ajustement versement, durée, allocation.",
            "Notifications proactives.",
        ]),
        _phase("Phase 4 — UI engageante (1-2 sem)", [
            "Visualisation probabiliste.",
            "Engagement via gamification.",
        ]),
    ),
    "stack": {
        "Simulation": "NumPy, SciPy",
        "Mobile": "React Native ou natif",
        "API": "FastAPI",
    },
    "prereq": [
        "Monte Carlo et théorie financière.",
        "Sens produit (UX).",
    ],
})

PROJECTS.append({
    "code": "B.4", "category": "8. Wealth / Robo-advisor",
    "title": "Détection de biais cognitifs (over-trading)",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "70 % des particuliers détruisent de la valeur en sur-tradant. Notifier au bon moment.",
    "roadmap": _rm(
        _phase("Phase 1 — Patterns destructeurs (1 sem)", [
            "Revente après baisse, FOMO post-hausse, sur-confiance.",
        ]),
        _phase("Phase 2 — Détection (2 sem)", [
            "Modèle séquentiel sur l'historique d'actions.",
            "Comparaison à comportement « expert ».",
        ]),
        _phase("Phase 3 — Notification (1-2 sem)", [
            "Friction douce, message éducatif.",
            "Pas d'empêchement (devoir conseiller, pas tuteur).",
        ]),
        _phase("Phase 4 — Mesure (1 sem)", [
            "Performance utilisateur après notification.",
        ]),
    ),
    "stack": {
        "Modèles": "Séquentiel (LSTM, Transformer), scikit-learn",
        "Mobile": "Notifications push",
        "Mesure": "Comparaison contrôle / traité",
    },
    "prereq": [
        "Finance comportementale.",
        "Conformité MiFID II (devoir de protection).",
    ],
})

# ============================================================================
# 9. TRÉSORERIE / CORPORATE / B2B
# ============================================================================
PROJECTS.append({
    "code": "C.1", "category": "9. Trésorerie / B2B",
    "title": "Prévision de trésorerie pour PME/ETI",
    "level": "INTERMÉDIAIRE", "duration": "6-8 semaines",
    "problem": "25 % des défaillances PME viennent d'un problème de trésorerie. Alerter J+45 avant rupture.",
    "roadmap": _rm(
        _phase("Phase 1 — Données (1 sem)", [
            "Historique flux comptes pro.",
            "Calendrier paiements clients/fournisseurs.",
        ]),
        _phase("Phase 2 — Modèle (3 sem)", [
            "Prophet, NeuralProphet, ou DeepAR.",
            "Décomposition saisonnière, événements.",
        ]),
        _phase("Phase 3 — Alerting (1-2 sem)", [
            "Seuil rupture configurable.",
            "Suggestions : avance facture, ligne de découvert.",
        ]),
        _phase("Phase 4 — Intégration (1 sem)", [
            "API + intégration app pro.",
        ]),
    ),
    "stack": {
        "Modèles": "Prophet, GluonTS, NeuralProphet",
        "Pipeline": "Airflow batch quotidien",
        "API": "FastAPI",
    },
    "prereq": [
        "Séries temporelles.",
        "Métier comptabilité PME.",
    ],
})

PROJECTS.append({
    "code": "C.2", "category": "9. Trésorerie / B2B",
    "title": "Détection de fraude au virement / président",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "Fraudes au virement coûtent 40-200 k€ par incident en PME / ETI. Conformité DSP2.",
    "roadmap": _rm(
        _phase("Phase 1 — Typologies (1 sem)", [
            "Faux président, faux fournisseur, IBAN modifié.",
        ]),
        _phase("Phase 2 — Scoring (3 sem)", [
            "Score temps réel d'un virement.",
            "Détection IBAN inconnu, montant inhabituel, timing.",
        ]),
        _phase("Phase 3 — Double validation conditionnelle (2 sem)", [
            "Step-up si score élevé.",
            "Validation mail + OTP + appel rappel.",
        ]),
        _phase("Phase 4 — Pilote (2 sem)", [
            "Mesure de fraudes évitées vs friction.",
        ]),
    ),
    "stack": {
        "Modèles": "LightGBM, scikit-learn",
        "API": "FastAPI low-latency",
        "Auth": "OTP, FIDO2",
    },
    "prereq": [
        "Scoring temps réel.",
        "Connaissance des fraudes B2B.",
    ],
})

PROJECTS.append({
    "code": "C.3", "category": "9. Trésorerie / B2B",
    "title": "Recommandation de couverture de change (FX hedging)",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "Une PME exportatrice ne sait pas combien et quand couvrir son risque FX.",
    "roadmap": _rm(
        _phase("Phase 1 — Prévision flux FX (3 sem)", [
            "Prévision multivariée par devise.",
            "Confidence intervals.",
        ]),
        _phase("Phase 2 — Modèle de couverture (3 sem)", [
            "Hedge ratio optimal sous contrainte coût.",
            "Instruments : forwards, options, NDF.",
        ]),
        _phase("Phase 3 — Pricing instruments (1-2 sem)", [
            "Modèle d'options (Black-Scholes étendu).",
            "Spread broker.",
        ]),
        _phase("Phase 4 — UI conseiller (1-2 sem)", [
            "Recommandations claires, what-if scénarios.",
        ]),
    ),
    "stack": {
        "Modèles": "GARCH, GluonTS, scipy.optimize",
        "Pricing": "QuantLib",
        "API": "FastAPI",
    },
    "prereq": [
        "Finance de marché FX.",
        "Pricing d'options (Black-Scholes, Greeks).",
    ],
})

PROJECTS.append({
    "code": "C.4", "category": "9. Trésorerie / B2B",
    "title": "Score de risque fournisseur",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "La faillite d'un fournisseur stratégique paralyse un client.",
    "roadmap": _rm(
        _phase("Phase 1 — Sourcing signaux (1-2 sem)", [
            "Rapports financiers, BODACC, news, retards paiement.",
        ]),
        _phase("Phase 2 — Scoring (2-3 sem)", [
            "Modèle de défaut 12 mois.",
            "Pondération par criticité du fournisseur.",
        ]),
        _phase("Phase 3 — Alerting (1 sem)", [
            "Notifications proactives au procurement.",
        ]),
        _phase("Phase 4 — Recommandations (1 sem)", [
            "Diversification, négociation conditions.",
        ]),
    ),
    "stack": {
        "Données": "Sirene, BODACC, news APIs",
        "Modèle": "LightGBM, SHAP",
        "Pipeline": "Airflow",
    },
    "prereq": [
        "Analyse financière entreprise.",
        "Modélisation défaut.",
    ],
})



# ============================================================================
# 10. CRYPTO / WEB3
# ============================================================================
PROJECTS.append({
    "code": "D.1", "category": "10. Crypto / Web3",
    "title": "Scoring de risque d'un wallet (Chainalysis-like)",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "Un exchange ou une banque doit savoir si un dépôt vient d'un mixer, du dark web, d'un wallet sanctionné.",
    "roadmap": _rm(
        _phase("Phase 1 — Ingestion on-chain (2 sem)", [
            "Indexation BTC + ETH + L2 (Polygon, Arbitrum).",
            "Reconstruction du graphe de transactions.",
        ]),
        _phase("Phase 2 — Étiquetage (2-3 sem)", [
            "Clusters connus (Tornado Cash, OFAC, exchanges).",
            "Heuristiques de clustering (common input ownership).",
        ]),
        _phase("Phase 3 — Propagation de risque (2-3 sem)", [
            "Score par profondeur dans le graphe.",
            "Modèle d'atténuation par nombre de sauts.",
        ]),
        _phase("Phase 4 — API & intégration (1-2 sem)", [
            "Score temps réel pour KYT (Know Your Transaction).",
            "Workflow alertes pour compliance.",
        ]),
    ),
    "stack": {
        "Indexation": "Etherscan API, The Graph, Erigon",
        "Graphe": "Neo4j, NetworkX, Memgraph",
        "ML": "GNN (DGL), embeddings node2vec",
        "Étiquetage": "Sources open (OFAC, Etherscan tags)",
    },
    "prereq": [
        "Compréhension blockchain (UTXO, account model).",
        "Graphes à grande échelle.",
        "Conformité MiCA, Travel Rule.",
    ],
})

PROJECTS.append({
    "code": "D.2", "category": "10. Crypto / Web3",
    "title": "Détection de rug pull / token frauduleux",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "30-50 % des nouveaux tokens DeFi sont des arnaques.",
    "roadmap": _rm(
        _phase("Phase 1 — Static analysis (2 sem)", [
            "Slither, Mythril sur le smart contract.",
            "Détection de patterns honeypot.",
        ]),
        _phase("Phase 2 — Dynamic analysis (2-3 sem)", [
            "Forking + simulation de buy/sell.",
            "Détection slippage anormal.",
        ]),
        _phase("Phase 3 — Signaux on-chain (2 sem)", [
            "Concentration des holders, lock de liquidité, renonce mint.",
        ]),
        _phase("Phase 4 — Classifieur final (1-2 sem)", [
            "Fusion des signaux.",
            "Score live à chaque mint.",
        ]),
    ),
    "stack": {
        "Static": "Slither, Mythril, Echidna",
        "Dynamic": "Foundry / Anvil, Tenderly",
        "ML": "LightGBM",
        "Indexation": "The Graph, Etherscan",
    },
    "prereq": [
        "Sécurité smart contract (Solidity).",
        "DeFi (DEX, AMM, liquidity pools).",
    ],
})

PROJECTS.append({
    "code": "D.3", "category": "10. Crypto / Web3",
    "title": "Early warning de dépeg de stablecoin",
    "level": "SENIOR", "duration": "6-8 semaines",
    "problem": "Un dépeg crée des pertes massives en quelques heures (UST mai 2022, USDC mars 2023).",
    "roadmap": _rm(
        _phase("Phase 1 — Signaux à suivre (1-2 sem)", [
            "Volumes redemption, ratios réserves, dépeg sur DEX.",
        ]),
        _phase("Phase 2 — Modèle de bascule (2-3 sem)", [
            "Détection de changement de régime.",
            "Score temps réel.",
        ]),
        _phase("Phase 3 — Décision (1-2 sem)", [
            "Fermeture marché ou couverture.",
            "Workflow trading desk.",
        ]),
        _phase("Phase 4 — Backtest (1 sem)", [
            "Sur épisodes connus (UST, USDC).",
        ]),
    ),
    "stack": {
        "On-chain": "Dune Analytics, Etherscan, The Graph",
        "Modèles": "HMM, scikit-learn, ruptures",
        "Alerting": "Slack, PagerDuty",
    },
    "prereq": [
        "DeFi (stablecoins, AMM).",
        "Détection de rupture (change-point).",
    ],
})

PROJECTS.append({
    "code": "D.4", "category": "10. Crypto / Web3",
    "title": "On-chain AML / Travel Rule",
    "level": "SENIOR", "duration": "10-12 semaines",
    "problem": "Régulateur exige traçabilité des contreparties > 1000 € sur blockchain (FATF, MiCA).",
    "roadmap": _rm(
        _phase("Phase 1 — Intégration TR (2-3 sem)", [
            "Protocoles TRP, IVMS101, Sumsub.",
            "Échange d'informations entre VASPs.",
        ]),
        _phase("Phase 2 — Monitoring transactions (3-4 sem)", [
            "Détection sauts de chaîne, mixers, bridges.",
            "Scoring AML par tx.",
        ]),
        _phase("Phase 3 — Reporting (2 sem)", [
            "Génération SAR/STR.",
            "Conservation 10 ans, audit trail.",
        ]),
        _phase("Phase 4 — Conformité MiCA (1-2 sem)", [
            "Mapping exigences MiCA / CASP.",
            "Documentation pour licence ACPR.",
        ]),
    ),
    "stack": {
        "TR": "Notabene, Sygna, Veriscope",
        "Monitoring": "Chainalysis KYT, Elliptic, ou interne",
        "Storage": "WORM (S3 Object Lock)",
    },
    "prereq": [
        "Très bonne connaissance MiCA, FATF, Travel Rule.",
        "Architecture VASP.",
    ],
})

# ============================================================================
# 11. PAIEMENTS
# ============================================================================
PROJECTS.append({
    "code": "E.1", "category": "11. Paiements",
    "title": "Fraude sur paiement instantané (SCT Inst, Pix, Wero)",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "Une fois envoyé, l'argent est parti. Budget latence < 50 ms.",
    "roadmap": _rm(
        _phase("Phase 1 — Cadrage (1 sem)", [
            "Cas typologie (fraude par manipulation, mule).",
            "SLA strict < 50 ms.",
        ]),
        _phase("Phase 2 — Modèle léger (3 sem)", [
            "Features pré-calculées (feature store).",
            "Modèle léger (logistic ou XGBoost compact).",
        ]),
        _phase("Phase 3 — Protection bilatérale (2 sem)", [
            "Scoring émetteur + récepteur.",
            "Échange entre banques via consortium.",
        ]),
        _phase("Phase 4 — Activation (2 sem)", [
            "Shadow mode, mesure de latence et fraude.",
        ]),
    ),
    "stack": {
        "Feature store": "Feast + Redis",
        "Modèle": "ONNX runtime pour latence",
        "API": "FastAPI ou Rust pour latence ultime",
    },
    "prereq": [
        "Architecture < 50 ms (Rust ou C++ utile).",
        "Connaissance SEPA Inst Reg 2024.",
    ],
})

PROJECTS.append({
    "code": "E.2", "category": "11. Paiements",
    "title": "Verification of Payee (VoP / CoP)",
    "level": "INTERMÉDIAIRE", "duration": "4-6 semaines",
    "problem": "Directive UE obligatoire (oct. 2025) : vérification IBAN ↔ nom avant chaque virement.",
    "roadmap": _rm(
        _phase("Phase 1 — Sourcing référentiels (1 sem)", [
            "Connexion aux schémas (EBA Clearing VOP, Iberpay).",
            "Cache local des comptes vérifiés.",
        ]),
        _phase("Phase 2 — Matching (2 sem)", [
            "Fuzzy matching Jaro-Winkler + phonétique.",
            "Tolérance translittération.",
        ]),
        _phase("Phase 3 — Scoring & UI (1-2 sem)", [
            "Trois statuts : match / close match / no match.",
            "Affichage utilisateur clair.",
        ]),
        _phase("Phase 4 — Conformité (1 sem)", [
            "Logs et opt-out règlementaire.",
        ]),
    ),
    "stack": {
        "Matching": "RapidFuzz, jellyfish",
        "API": "FastAPI",
        "Schémas": "EBA Clearing VOP, SurePay",
    },
    "prereq": [
        "Directive Instant Payments UE.",
        "Fuzzy matching multilingue.",
    ],
})

PROJECTS.append({
    "code": "E.3", "category": "11. Paiements",
    "title": "Optimisation du routage des autorisations",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "Mauvais routage entre réseaux (Visa/Mastercard/CB/locaux) = décline ou frais plus élevés.",
    "roadmap": _rm(
        _phase("Phase 1 — Mesure baseline (2 sem)", [
            "Taux d'autorisation par réseau.",
            "Coût interchange.",
        ]),
        _phase("Phase 2 — Bandit contextuel (3-4 sem)", [
            "Apprentissage en continu best route.",
            "Exploration/exploitation contrôlée.",
        ]),
        _phase("Phase 3 — Garde-fous (1-2 sem)", [
            "Quota par schéma, fallback.",
        ]),
        _phase("Phase 4 — A/B & roll-out (2 sem)", [
            "Mesure gain autorisation et frais.",
        ]),
    ),
    "stack": {
        "Bandits": "Vowpal Wabbit, custom",
        "API": "FastAPI",
        "Pipeline": "Kafka events, Spark",
    },
    "prereq": [
        "Bandit algorithms / RL contextuel.",
        "Connaissance schémas carte.",
    ],
})

PROJECTS.append({
    "code": "E.4", "category": "11. Paiements",
    "title": "Automatisation des disputes / pré-chargeback",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Disputes contestées à la main coûte cher, taux de gain faible.",
    "roadmap": _rm(
        _phase("Phase 1 — Collecte preuves (2 sem)", [
            "Intégration tracking livraison, comms client.",
            "Device fingerprint au moment du paiement.",
        ]),
        _phase("Phase 2 — Génération réponse (2 sem)", [
            "Template par reason code + LLM pour personnalisation.",
            "Vérification compliance.",
        ]),
        _phase("Phase 3 — Workflow (1-2 sem)", [
            "Auto-submit au schéma carte.",
            "Suivi des verdicts.",
        ]),
        _phase("Phase 4 — Amélioration (1 sem)", [
            "Analyse des disputes perdues.",
        ]),
    ),
    "stack": {
        "LLM": "OpenAI / Claude",
        "Intégration": "API Visa/Mastercard, Stripe Dispute",
        "Workflow": "Temporal",
    },
    "prereq": [
        "Connaissance schémas Visa/Mastercard dispute.",
        "LLM ops.",
    ],
})

# ============================================================================
# 12. REGTECH
# ============================================================================
PROJECTS.append({
    "code": "F.1", "category": "12. RegTech",
    "title": "Reporting réglementaire (FINREP, COREP, AnaCredit)",
    "level": "SENIOR", "duration": "12-16 semaines",
    "problem": "50-200 personnes à temps plein pour produire les rapports prudentiels d'une grande banque.",
    "roadmap": _rm(
        _phase("Phase 1 — Mapping (3 sem)", [
            "Spec EBA → champs internes.",
            "Glossaire métier.",
        ]),
        _phase("Phase 2 — Pipeline agrégation (4 sem)", [
            "Pipeline ETL avec tests qualité.",
            "Versioning des règles.",
        ]),
        _phase("Phase 3 — Génération XBRL (3 sem)", [
            "Output XBRL/XML conforme.",
            "Validation contre taxonomie EBA.",
        ]),
        _phase("Phase 4 — Workflow validation (2-3 sem)", [
            "Validation manager, audit trail.",
            "Submission automatisée.",
        ]),
    ),
    "stack": {
        "Données": "Snowflake / Oracle / Teradata",
        "ETL": "dbt, Airflow, Great Expectations",
        "XBRL": "Arelle, AltovaXBRL",
        "Workflow": "Camunda, BPMN",
    },
    "prereq": [
        "Connaissance réglementations EBA, BCE.",
        "Data engineering haute fiabilité.",
    ],
})

PROJECTS.append({
    "code": "F.2", "category": "12. RegTech",
    "title": "IFRS 9 — Expected Credit Loss (ECL)",
    "level": "SENIOR", "duration": "10-14 semaines",
    "problem": "Provisionner les pertes attendues, pas avérées. 3 modèles couplés (PD, LGD, EAD).",
    "roadmap": _rm(
        _phase("Phase 1 — PD (4 sem)", [
            "Probabilité de défaut par segment.",
            "Calibration lifetime.",
        ]),
        _phase("Phase 2 — LGD & EAD (4 sem)", [
            "Loss Given Default sur historique recovery.",
            "Exposure At Default avec CCF.",
        ]),
        _phase("Phase 3 — Stages IFRS 9 (2 sem)", [
            "Stage 1/2/3 selon SICR (Significant Increase in Credit Risk).",
        ]),
        _phase("Phase 4 — Scénarios macro (2-3 sem)", [
            "Forward-looking : GDP, chômage, inflation.",
            "Pondération de scénarios.",
        ]),
    ),
    "stack": {
        "Modèles": "scikit-learn, lifelines, statsmodels",
        "Données macro": "ECB, FRED",
        "Backtesting": "Validation MRM",
    },
    "prereq": [
        "Modélisation crédit Bâle III.",
        "Norme IFRS 9 maîtrisée.",
    ],
})

PROJECTS.append({
    "code": "F.3", "category": "12. RegTech",
    "title": "Surveillance des communications (MAR, MAD II)",
    "level": "SENIOR", "duration": "10-12 semaines",
    "problem": "Surveillance chats/mails/appels des traders. Amendes dizaines de millions sinon.",
    "roadmap": _rm(
        _phase("Phase 1 — Sourcing (2 sem)", [
            "Bloomberg, Symphony, mail, voice transcription.",
        ]),
        _phase("Phase 2 — NLP multilingue (4 sem)", [
            "Détection intention, sentiment, entités.",
            "Modèles fine-tunés sur language trading.",
        ]),
        _phase("Phase 3 — Scoring alerte (2-3 sem)", [
            "Combinaison signaux, contexte trader.",
            "Réduction faux positifs.",
        ]),
        _phase("Phase 4 — Workflow Compliance (2 sem)", [
            "Review interface, traçabilité.",
        ]),
    ),
    "stack": {
        "NLP": "Hugging Face, langchain, OpenAI",
        "Voice": "Whisper, Deepgram",
        "Storage": "Elastic, WORM",
        "UI": "Internal compliance tool",
    },
    "prereq": [
        "NLP multilingue.",
        "Conformité MAR / MiFID II.",
    ],
})

PROJECTS.append({
    "code": "F.4", "category": "12. RegTech",
    "title": "Plateforme de Model Risk Management",
    "level": "SENIOR", "duration": "12-16 semaines",
    "problem": "BCE/Fed exigent inventaire, validation, monitoring, recertification de tout modèle prod.",
    "roadmap": _rm(
        _phase("Phase 1 — Catalogue (3 sem)", [
            "Métadonnées par modèle : version, propriétaire, criticité.",
            "Cartographie des dépendances.",
        ]),
        _phase("Phase 2 — Workflow validation (4 sem)", [
            "Pipeline validation indépendante.",
            "Approbation par niveau de risque.",
        ]),
        _phase("Phase 3 — Monitoring (4 sem)", [
            "Drift, performance, fairness automatiques.",
        ]),
        _phase("Phase 4 — Recertification (2-3 sem)", [
            "Calendrier de revue par modèle.",
        ]),
    ),
    "stack": {
        "Catalogue": "DataHub, Amundsen, custom",
        "Tracking": "MLflow",
        "Workflow": "Temporal, Camunda",
        "UI": "React + FastAPI",
    },
    "prereq": [
        "SR 11-7, TRIM (BCE), SS1/23 (PRA).",
        "Architecture plateforme.",
    ],
})



# ============================================================================
# 13. CLIMAT & ESG
# ============================================================================
PROJECTS.append({
    "code": "G.1", "category": "13. Climat & ESG",
    "title": "Empreinte carbone d'un portefeuille / d'une carte",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Obligation SFDR / CSRD / art. 173. Différenciation produit aussi (Helios, Green-Got, Vivid).",
    "roadmap": _rm(
        _phase("Phase 1 — Référentiel facteurs (1-2 sem)", [
            "ADEME Base Carbone, GHG Protocol.",
            "Mapping MCC ↔ secteur ↔ facteur.",
        ]),
        _phase("Phase 2 — Calcul (2 sem)", [
            "Aggrégation par transaction puis portefeuille.",
            "Période glissante 12 mois.",
        ]),
        _phase("Phase 3 — Visualisation (1-2 sem)", [
            "Breakdown par catégorie, comparaison moyenne.",
            "Recommandations d'action.",
        ]),
        _phase("Phase 4 — Reporting réglementaire (1 sem)", [
            "Export pour SFDR / art. 173.",
        ]),
    ),
    "stack": {
        "Données": "ADEME Base Carbone, GHG Protocol",
        "Pipeline": "Airflow batch mensuel",
        "UI": "Mobile + dashboard",
    },
    "prereq": [
        "Comptabilité carbone (Scope 1/2/3).",
        "Réglementation SFDR / CSRD.",
    ],
})

PROJECTS.append({
    "code": "G.2", "category": "13. Climat & ESG",
    "title": "Climate Value at Risk (scénarios IPCC)",
    "level": "SENIOR", "duration": "10-12 semaines",
    "problem": "Portefeuille immo/énergie exposé au risque physique et de transition (taxe carbone).",
    "roadmap": _rm(
        _phase("Phase 1 — Scénarios (2-3 sem)", [
            "NGFS, IPCC, sectoriels.",
            "Sélection horizons (2030, 2050).",
        ]),
        _phase("Phase 2 — Impact sectoriel (4 sem)", [
            "Modèles d'impact secteur par scénario.",
            "Sensibilités spécifiques (immo zone inondable, etc.).",
        ]),
        _phase("Phase 3 — Climate VaR (3 sem)", [
            "Distribution perte projetée par actif.",
            "Agrégation portefeuille.",
        ]),
        _phase("Phase 4 — Reporting (2 sem)", [
            "Conformité ECB Climate Stress Test.",
        ]),
    ),
    "stack": {
        "Scénarios": "NGFS data, IIASA SSP",
        "Modèles": "Python, scipy, statsmodels",
        "Reporting": "ReportLab pour PDF réglementaire",
    },
    "prereq": [
        "Stress testing classique.",
        "Connaissance scénarios IPCC / NGFS.",
    ],
})

PROJECTS.append({
    "code": "G.3", "category": "13. Climat & ESG",
    "title": "Scoring de prêt vert (green loan)",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Taxonomie EU complexe. Difficile de classifier un prêt comme « vert » défendablement.",
    "roadmap": _rm(
        _phase("Phase 1 — Règles taxonomie (1-2 sem)", [
            "Mapping activités CapEx/OpEx ↔ taxonomie EU.",
        ]),
        _phase("Phase 2 — Extraction justificatifs (2 sem)", [
            "LLM sur DPE, factures travaux, devis.",
            "Output structuré.",
        ]),
        _phase("Phase 3 — Scoring conformité (1-2 sem)", [
            "Critères DNSH, MSS.",
            "Score 0-100.",
        ]),
        _phase("Phase 4 — Validation (1 sem)", [
            "Revue manuelle des cas limites.",
        ]),
    ),
    "stack": {
        "LLM": "OpenAI / Mistral",
        "OCR": "PaddleOCR",
        "Règles": "Moteur YAML",
    },
    "prereq": [
        "Taxonomie EU 2020/852.",
        "LLM extraction structurée.",
    ],
})

PROJECTS.append({
    "code": "G.4", "category": "13. Climat & ESG",
    "title": "Détection de greenwashing dans les fonds ISR",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "Fonds prétendus « durables » sans sous-jacents alignés. SEC, AMF, BAFIN sanctionnent.",
    "roadmap": _rm(
        _phase("Phase 1 — NLP sur prospectus (3 sem)", [
            "Extraction des engagements ESG affichés.",
            "Détection claims.",
        ]),
        _phase("Phase 2 — Analyse holdings réels (2-3 sem)", [
            "Scoring ESG des entreprises détenues.",
            "Sources : MSCI, Sustainalytics, ou open data.",
        ]),
        _phase("Phase 3 — Calcul écart (2 sem)", [
            "Score d'écart claims vs réalité.",
            "Détection statistique.",
        ]),
        _phase("Phase 4 — Reporting (1 sem)", [
            "Rapport pour AMF / régulateur.",
        ]),
    ),
    "stack": {
        "NLP": "Hugging Face, OpenAI",
        "ESG": "MSCI ESG, Sustainalytics, Refinitiv",
        "Analyse": "Pandas, scikit-learn",
    },
    "prereq": [
        "ESG investing.",
        "NLP financier.",
    ],
})

# ============================================================================
# 14. OPEN BANKING
# ============================================================================
PROJECTS.append({
    "code": "H.1", "category": "14. Open Banking",
    "title": "Enrichissement de libellés bancaires",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Libellés bancaires illisibles. Prérequis à PFM, mobile banking, comptabilité auto.",
    "roadmap": _rm(
        _phase("Phase 1 — Pipeline parsing (1-2 sem)", [
            "Regex + tokenisation.",
            "Détection date, montant, ville, devise.",
        ]),
        _phase("Phase 2 — Extraction marchand (2-3 sem)", [
            "Modèle NER ou classification.",
            "Base mutualisée marchands.",
        ]),
        _phase("Phase 3 — Enrichissement (1-2 sem)", [
            "Logo, adresse, catégorie, MCC.",
            "Cache pour latence.",
        ]),
        _phase("Phase 4 — API & feedback (1 sem)", [
            "API batch + temps réel.",
            "Feedback users pour corrections.",
        ]),
    ),
    "stack": {
        "NLP": "spaCy, Hugging Face",
        "DB": "PostgreSQL + Redis",
        "API": "FastAPI",
        "Sources logos": "Clearbit, Brandfetch",
    },
    "prereq": [
        "NER et regex en production.",
        "Architecture cache + base mutualisée.",
    ],
})

PROJECTS.append({
    "code": "H.2", "category": "14. Open Banking",
    "title": "Détection automatique des revenus récurrents",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Identifier avec certitude salaire, pension, allocation, loyer reçu.",
    "roadmap": _rm(
        _phase("Phase 1 — Clustering temporel (2 sem)", [
            "Détection de récurrence mensuelle / bimensuelle.",
            "Tolérance variation montant et date.",
        ]),
        _phase("Phase 2 — Classification (2 sem)", [
            "Salaire vs autre revenu récurrent.",
            "Features : émetteur, libellé, montant relatif.",
        ]),
        _phase("Phase 3 — Score de confiance (1 sem)", [
            "Stabilité, ancienneté, montant.",
        ]),
        _phase("Phase 4 — Intégration (1 sem)", [
            "Sortie pour scoring crédit, dashboard.",
        ]),
    ),
    "stack": {
        "Modèle": "scikit-learn, LightGBM",
        "Pipeline": "Airflow batch quotidien",
        "API": "FastAPI",
    },
    "prereq": [
        "Détection de séquences récurrentes.",
        "Métier crédit (revenus stables).",
    ],
})

PROJECTS.append({
    "code": "H.3", "category": "14. Open Banking",
    "title": "Income & affordability scoring",
    "level": "SENIOR", "duration": "6-8 semaines",
    "problem": "PSD2 permet d'évaluer la solvabilité sans fiche de paie. Crédit en 5 min vs 5 jours.",
    "roadmap": _rm(
        _phase("Phase 1 — Ingestion OB (1-2 sem)", [
            "Connexions agrégateurs (Powens, Bridge, Tink).",
            "Stockage transactions sécurisé.",
        ]),
        _phase("Phase 2 — Revenus & dépenses (2-3 sem)", [
            "Détection revenus stables (cf. H.2).",
            "Charges incompressibles (loyer, abonnements).",
        ]),
        _phase("Phase 3 — Score capacité (2 sem)", [
            "Reste à vivre, taux d'endettement projeté.",
            "Modèle calibré.",
        ]),
        _phase("Phase 4 — Décision (1 sem)", [
            "Combinaison avec scoring crédit.",
        ]),
    ),
    "stack": {
        "OB": "Powens, Bridge, Tink (Visa)",
        "Modèles": "LightGBM, SHAP",
        "API": "FastAPI",
    },
    "prereq": [
        "PSD2 / DSP2.",
        "Modélisation crédit + explicabilité.",
    ],
})

PROJECTS.append({
    "code": "H.4", "category": "14. Open Banking",
    "title": "Réconciliation comptable automatique",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Comptables passent 30-50 % de leur temps à apparier transactions bancaires et écritures.",
    "roadmap": _rm(
        _phase("Phase 1 — Modèle matching (2-3 sem)", [
            "Matching probabiliste (montant, date, libellé).",
            "Sentence embeddings sur libellé.",
        ]),
        _phase("Phase 2 — Suggestions (1-2 sem)", [
            "Top-3 matches par transaction.",
            "Confiance par match.",
        ]),
        _phase("Phase 3 — Apprentissage feedback (1 sem)", [
            "Mémorisation des matches confirmés.",
        ]),
        _phase("Phase 4 — Intégration logiciel compta (1 sem)", [
            "API pour Pennylane / Cegid / Sage.",
        ]),
    ),
    "stack": {
        "Modèle": "Sentence Transformers, scikit-learn",
        "DB": "PostgreSQL",
        "API": "FastAPI",
    },
    "prereq": [
        "Comptabilité (PCG, lettrage).",
        "Matching probabiliste.",
    ],
})

# ============================================================================
# 15. EMBEDDED FINANCE / BaaS
# ============================================================================
PROJECTS.append({
    "code": "I.1", "category": "15. Embedded Finance / BaaS",
    "title": "Score de risque d'un partenaire BaaS",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "Une banque BaaS hébergeant 50 fintechs : une seule peut faire couler la licence (cf. Synapse).",
    "roadmap": _rm(
        _phase("Phase 1 — Indicateurs (1-2 sem)", [
            "Volumes, taux fraude, qualité KYC, reporting.",
        ]),
        _phase("Phase 2 — Monitoring continu (3-4 sem)", [
            "Collecte automatisée + alerting.",
            "Score consolidé par partenaire.",
        ]),
        _phase("Phase 3 — Workflow partenariat (2 sem)", [
            "Onboarding nouvelle fintech.",
            "Révision périodique.",
        ]),
        _phase("Phase 4 — Reporting régulateur (1-2 sem)", [
            "Évidence conformité ACPR.",
        ]),
    ),
    "stack": {
        "Monitoring": "Grafana, Prometheus",
        "Data": "Snowflake, dbt",
        "Workflow": "Temporal",
    },
    "prereq": [
        "Connaissance BaaS et exigences ACPR.",
        "Risk monitoring opérationnel.",
    ],
})

PROJECTS.append({
    "code": "I.2", "category": "15. Embedded Finance / BaaS",
    "title": "API abuse detection / rate limiting adaptatif",
    "level": "INTERMÉDIAIRE", "duration": "4-6 semaines",
    "problem": "Partenaire mal-implémenté peut saturer l'API, ou déclencher du card-testing à ton insu.",
    "roadmap": _rm(
        _phase("Phase 1 — Telemetry (1 sem)", [
            "Logs par tenant, par endpoint.",
            "Métriques de comportement.",
        ]),
        _phase("Phase 2 — Détection (2 sem)", [
            "Anomalie sur pattern d'appel.",
            "Détection card testing.",
        ]),
        _phase("Phase 3 — Rate limiting (1-2 sem)", [
            "Quotas adaptatifs.",
            "Circuit breaker par tenant.",
        ]),
        _phase("Phase 4 — Facturation usage (1 sem)", [
            "Métrique d'usage juste.",
        ]),
    ),
    "stack": {
        "Streaming": "Kafka",
        "Détection": "PyOD, scikit-learn",
        "Gateway": "Kong, Envoy, Apigee",
    },
    "prereq": [
        "Anomaly detection en streaming.",
        "API gateway / microservices.",
    ],
})

PROJECTS.append({
    "code": "I.3", "category": "15. Embedded Finance / BaaS",
    "title": "Card program management automatisé",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "Gérer 100+ programmes carte (BIN, plafonds, règles, branding) à la main est intenable.",
    "roadmap": _rm(
        _phase("Phase 1 — Modélisation programme (2 sem)", [
            "Schéma : BIN range, plafonds, KYC level, branding.",
        ]),
        _phase("Phase 2 — Moteur de règles (3-4 sem)", [
            "Application des règles par programme.",
            "Versioning.",
        ]),
        _phase("Phase 3 — Workflow activation (2 sem)", [
            "Onboarding programme avec checklist.",
        ]),
        _phase("Phase 4 — Monitoring saturation (1-2 sem)", [
            "Alertes saturation BIN.",
        ]),
    ),
    "stack": {
        "Backend": "Java/Kotlin (souvent en banque) ou Python",
        "Workflow": "Camunda, Temporal",
        "DB": "PostgreSQL",
    },
    "prereq": [
        "Émission carte (Visa/Mastercard licensee).",
        "Architecture multi-tenant.",
    ],
})

# ============================================================================
# 16. CROSS-BORDER / REMITTANCE
# ============================================================================
PROJECTS.append({
    "code": "J.1", "category": "16. Cross-border / Remittance",
    "title": "Optimisation de corridor de paiement",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "FR → SN peut passer par 5 routes. Coût et délai varient du simple au quintuple.",
    "roadmap": _rm(
        _phase("Phase 1 — Mapping corridors (1-2 sem)", [
            "SWIFT, SEPA, mobile money, stablecoin, fintechs.",
        ]),
        _phase("Phase 2 — Mesure (2-3 sem)", [
            "Coût réel et délai observé par route.",
        ]),
        _phase("Phase 3 — Bandit contextuel (3 sem)", [
            "Apprentissage en continu best route.",
        ]),
        _phase("Phase 4 — Production (2 sem)", [
            "Décision temps réel + A/B test.",
        ]),
    ),
    "stack": {
        "Bandit": "VW, custom",
        "Routing": "FastAPI, Kafka events",
        "Observabilité": "Prometheus, Datadog",
    },
    "prereq": [
        "RL / bandit algorithms.",
        "Connaissance SWIFT / mobile money.",
    ],
})

PROJECTS.append({
    "code": "J.2", "category": "16. Cross-border / Remittance",
    "title": "Prédiction des taux de change pour pricing",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Afficher un taux fixe 24 h nécessite couverture intelligente.",
    "roadmap": _rm(
        _phase("Phase 1 — Modèle volatilité (2 sem)", [
            "GARCH, EWMA, ou LSTM.",
        ]),
        _phase("Phase 2 — Pricing avec spread (1-2 sem)", [
            "Calibration spread par couple devise.",
        ]),
        _phase("Phase 3 — Hedging automatique (1-2 sem)", [
            "Au-delà d'un seuil, hedge sur marché interbancaire.",
        ]),
        _phase("Phase 4 — Suivi P&L (1 sem)", [
            "Mesure de la marge stabilisée.",
        ]),
    ),
    "stack": {
        "Modèles": "arch (GARCH), statsmodels, GluonTS",
        "Trading": "Connexion broker via API",
    },
    "prereq": [
        "FX trading et volatilité.",
        "Pricing dérivés simples.",
    ],
})

PROJECTS.append({
    "code": "J.3", "category": "16. Cross-border / Remittance",
    "title": "Détection de mules transfrontalières",
    "level": "SENIOR", "duration": "10-12 semaines",
    "problem": "Remittance = canal favori pour faire sortir argent volé. Quasi-irréversibilité.",
    "roadmap": _rm(
        _phase("Phase 1 — Graphe multi-pays (3 sem)", [
            "Modélisation comptes émetteurs / bénéficiaires.",
        ]),
        _phase("Phase 2 — Détection patterns layering (3-4 sem)", [
            "Algorithmes graphe + ML.",
        ]),
        _phase("Phase 3 — Collaboration PSP (2 sem)", [
            "Consortium de partage de signaux.",
        ]),
        _phase("Phase 4 — Workflow (2 sem)", [
            "Investigation tools.",
        ]),
    ),
    "stack": {
        "Graphe": "Neo4j, DGL",
        "Streaming": "Kafka",
        "Consortium": "API B2B sécurisée",
    },
    "prereq": [
        "Graphes + AML.",
        "Conformité multi-juridictions.",
    ],
})



# ============================================================================
# 17. PROPTECH
# ============================================================================
PROJECTS.append({
    "code": "K.1", "category": "17. PropTech / Crédit immobilier",
    "title": "AVM — Automated Valuation Model",
    "level": "SENIOR", "duration": "10-12 semaines",
    "problem": "Évaluer un bien immo coûte 300-500 € et prend 2 semaines. AVM = 0 € et 5 s.",
    "roadmap": _rm(
        _phase("Phase 1 — Données (2-3 sem)", [
            "DVF (transactions réelles), DPE, IGN, INSEE.",
            "Features géo à fine maille (IRIS).",
        ]),
        _phase("Phase 2 — Modèle (3-4 sem)", [
            "Gradient boosting sur features.",
            "Quantile regression pour intervalle de confiance.",
        ]),
        _phase("Phase 3 — Validation (2 sem)", [
            "MAPE par segment géo.",
            "Comparaison expert humain.",
        ]),
        _phase("Phase 4 — API & UI (2 sem)", [
            "Estimation + intervalle de confiance.",
        ]),
    ),
    "stack": {
        "Données": "DVF (open data), IGN, ADEME, INSEE",
        "Modèles": "LightGBM, NGBoost, scikit-learn",
        "Géo": "GeoPandas, H3",
        "API": "FastAPI",
    },
    "prereq": [
        "Modélisation géospatiale.",
        "Quantile regression / modèles d'incertitude.",
    ],
})

PROJECTS.append({
    "code": "K.2", "category": "17. PropTech / Crédit immobilier",
    "title": "Pré-scoring crédit immobilier en 30 secondes",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "60 % des demandes de prêt immo rejetées après 3 semaines d'instruction.",
    "roadmap": _rm(
        _phase("Phase 1 — Simulateur dur (1-2 sem)", [
            "DT/I, taux d'usure, durée max.",
            "Règles bancaires.",
        ]),
        _phase("Phase 2 — Scoring soft OB (2 sem)", [
            "Income & affordability (cf. H.3).",
        ]),
        _phase("Phase 3 — Décision (1-2 sem)", [
            "Verdict instantané : OK / quasi / non.",
            "Explication des écarts.",
        ]),
        _phase("Phase 4 — Conversion (1 sem)", [
            "Mesure conversion tunnel.",
        ]),
    ),
    "stack": {
        "OB": "Powens, Bridge, Tink",
        "Modèles": "LightGBM",
        "API": "FastAPI",
        "UI": "React, formulaire simplifié",
    },
    "prereq": [
        "Crédit immobilier (HCSF, taux d'usure).",
        "UX tunnel d'achat.",
    ],
})

PROJECTS.append({
    "code": "K.3", "category": "17. PropTech / Crédit immobilier",
    "title": "Risque climatique d'un bien immobilier",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Bien en zone inondable ou mauvais DPE perd 10-30 % de valeur sur 10 ans.",
    "roadmap": _rm(
        _phase("Phase 1 — Données risques (1-2 sem)", [
            "Géorisques (inondation, retrait-gonflement), DPE.",
        ]),
        _phase("Phase 2 — Croisement géo (2 sem)", [
            "Adresse → géocodage → couches risque.",
        ]),
        _phase("Phase 3 — Scoring (1-2 sem)", [
            "Score combiné physique + transition.",
            "Projection scénarios IPCC.",
        ]),
        _phase("Phase 4 — Intégration (1 sem)", [
            "Affichage estimation immo / prêt.",
        ]),
    ),
    "stack": {
        "Données": "Géorisques, ADEME DPE, BRGM",
        "Géo": "GeoPandas, Shapely",
        "API": "FastAPI",
    },
    "prereq": [
        "Données géospatiales.",
        "Risques physiques climatiques.",
    ],
})

# ============================================================================
# 18. TAX & COMPTABILITÉ
# ============================================================================
PROJECTS.append({
    "code": "L.1", "category": "18. Tax & Comptabilité",
    "title": "Calcul TVA temps réel multi-pays (e-commerce)",
    "level": "INTERMÉDIAIRE", "duration": "6-8 semaines",
    "problem": "OSS, seuils, exceptions par pays. Cauchemar opérationnel.",
    "roadmap": _rm(
        _phase("Phase 1 — Référentiel fiscal (2 sem)", [
            "Taux par pays/produit/contexte.",
            "Seuils, exceptions.",
        ]),
        _phase("Phase 2 — Moteur règles (2 sem)", [
            "Détection adresse, type bien.",
            "Calcul TVA applicable.",
        ]),
        _phase("Phase 3 — Génération OSS (1-2 sem)", [
            "Déclaration trimestrielle.",
        ]),
        _phase("Phase 4 — Intégration e-commerce (1-2 sem)", [
            "Plugins Shopify / WooCommerce.",
        ]),
    ),
    "stack": {
        "Règles": "Moteur Python ou Drools",
        "API": "FastAPI",
        "Reporting": "XML OSS",
    },
    "prereq": [
        "Fiscalité TVA UE.",
        "Architecture moteur de règles.",
    ],
})

PROJECTS.append({
    "code": "L.2", "category": "18. Tax & Comptabilité",
    "title": "Déclaration plus-values crypto / bourse",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Investisseur retail avec 200 transactions / an ne sait pas remplir sa 2086.",
    "roadmap": _rm(
        _phase("Phase 1 — Ingestion (1-2 sem)", [
            "Connexions exchanges (Binance, Coinbase, Kraken).",
            "Imports CSV.",
        ]),
        _phase("Phase 2 — Calcul PV (2-3 sem)", [
            "FIFO ou prix moyen pondéré.",
            "Conversions devises historiques.",
        ]),
        _phase("Phase 3 — Génération 2086 (1-2 sem)", [
            "Formulaires fiscaux prêts.",
        ]),
        _phase("Phase 4 — UX (1 sem)", [
            "Onboarding fluide, support multi-exchange.",
        ]),
    ),
    "stack": {
        "Ingestion": "API exchanges + CCXT",
        "Calcul": "Python + Pandas",
        "PDF": "ReportLab",
    },
    "prereq": [
        "Fiscalité crypto FR.",
        "API exchanges crypto.",
    ],
})

PROJECTS.append({
    "code": "L.3", "category": "18. Tax & Comptabilité",
    "title": "OCR + auto-comptabilisation des notes de frais",
    "level": "JUNIOR", "duration": "4-6 semaines",
    "problem": "Note de frais traitée à la main dans 70 % des PME.",
    "roadmap": _rm(
        _phase("Phase 1 — OCR ticket (1-2 sem)", [
            "PaddleOCR, Tesseract, Mistral OCR.",
        ]),
        _phase("Phase 2 — Extraction structurée (2 sem)", [
            "Montant, TVA, marchand, catégorie.",
            "LLM pour cas difficiles.",
        ]),
        _phase("Phase 3 — Suggestion compte compta (1 sem)", [
            "Mapping catégorie → PCG.",
        ]),
        _phase("Phase 4 — Workflow validation (1 sem)", [
            "Approbation manager.",
        ]),
    ),
    "stack": {
        "OCR": "PaddleOCR, Tesseract, Mistral OCR API",
        "LLM": "Mistral / OpenAI",
        "API": "FastAPI",
    },
    "prereq": [
        "OCR pratique.",
        "Bases comptabilité (PCG).",
    ],
})

# ============================================================================
# 19. IDENTITÉ & LIVENESS
# ============================================================================
PROJECTS.append({
    "code": "M.1", "category": "19. Identité & Liveness",
    "title": "Détection de liveness anti-deepfake",
    "level": "SENIOR", "duration": "8-10 semaines",
    "problem": "Deepfakes ouvrent comptes bancaires à grande échelle, contournant selfie classique.",
    "roadmap": _rm(
        _phase("Phase 1 — Challenges actifs (2 sem)", [
            "Bouger la tête, prononcer mots aléatoires.",
            "Cohérence audio/vidéo.",
        ]),
        _phase("Phase 2 — Modèles anti-spoof (3-4 sem)", [
            "Détection face swap, GAN, diffusion.",
            "Détection inconsistencies pupille, peau, lighting.",
        ]),
        _phase("Phase 3 — Scoring (2 sem)", [
            "Combinaison signaux.",
            "Seuils par cas d'usage.",
        ]),
        _phase("Phase 4 — Robustesse (1-2 sem)", [
            "Adversarial testing.",
            "Mise à jour continue face aux nouveaux deepfakes.",
        ]),
    ),
    "stack": {
        "Vision": "MediaPipe, OpenCV, PyTorch",
        "Anti-spoof": "modèles spécialisés (DeepFakeLiveness, Sensity)",
        "API": "FastAPI",
    },
    "prereq": [
        "Computer vision avancée.",
        "Veille deepfakes / adversarial ML.",
    ],
})

PROJECTS.append({
    "code": "M.2", "category": "19. Identité & Liveness",
    "title": "Détection de falsification de documents",
    "level": "SENIOR", "duration": "6-8 semaines",
    "problem": "Faux passeports et justificatifs générés par IA inondent les onboardings.",
    "roadmap": _rm(
        _phase("Phase 1 — Référentiel documents (1 sem)", [
            "Specs MRZ, hologrammes, fontes officielles.",
        ]),
        _phase("Phase 2 — Modèles vision (3 sem)", [
            "Cohérence visuelle.",
            "Détection trace de modification.",
        ]),
        _phase("Phase 3 — Métadonnées (1-2 sem)", [
            "EXIF, fingerprint génération.",
        ]),
        _phase("Phase 4 — Workflow analyste (1-2 sem)", [
            "UI revue.",
        ]),
    ),
    "stack": {
        "Vision": "OpenCV, PyTorch",
        "OCR MRZ": "PassportEye",
        "API": "FastAPI",
    },
    "prereq": [
        "Computer vision.",
        "Document forensics.",
    ],
})

PROJECTS.append({
    "code": "M.3", "category": "19. Identité & Liveness",
    "title": "Age verification ZK (preuves preservant la vie privée)",
    "level": "INTERMÉDIAIRE", "duration": "5-7 semaines",
    "problem": "Régulateur exige preuve d'âge sans dévoiler identité (eIDAS 2, accès sites adultes).",
    "roadmap": _rm(
        _phase("Phase 1 — Architecture ZK (2 sem)", [
            "Zero-knowledge proof : preuve d'âge sans révéler date.",
        ]),
        _phase("Phase 2 — Estimation visuelle (2 sem)", [
            "Modèle CNN d'âge (fallback).",
        ]),
        _phase("Phase 3 — Workflow conditionnel (1-2 sem)", [
            "Doc identité demandé seulement si doute.",
        ]),
        _phase("Phase 4 — Intégration eIDAS (1 sem)", [
            "Wallet EU eID prêt.",
        ]),
    ),
    "stack": {
        "ZK": "snarkjs, circom, ou Anon Aadhaar",
        "Vision": "PyTorch (age estimation)",
        "Wallet eID": "EUDI Wallet specs",
    },
    "prereq": [
        "Zero-knowledge proofs (basics).",
        "eIDAS 2 / DSS.",
    ],
})



# ============================================================================
# Construction du PDF
# ============================================================================
def build(out_path: Path) -> None:
    doc = MyDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Feuilles de route — Projets Fintech",
        author="MLOps Team",
    )

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="m")
    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=[frame], onPage=_cover_bg),
        PageTemplate(id="Content", frames=[frame], onPage=_hdr_ftr),
    ])

    story: list = []

    # ---- Cover ----
    story.append(Spacer(1, 4.5 * cm))
    story.append(Paragraph(
        "Feuilles de route<br/>Projets Fintech",
        ParagraphStyle("Big", fontName=FONT_B, fontSize=30, leading=38,
                       textColor=colors.whitesmoke, alignment=TA_CENTER),
    ))
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "70 idées concrètes, regroupées en 19 verticales",
        ParagraphStyle("Sub", fontName=FONT, fontSize=14, leading=18,
                       textColor=colors.HexColor("#cfd8e3"), alignment=TA_CENTER),
    ))
    story.append(Spacer(1, 6 * cm))
    story.append(P(
        "<b>Document de planification — équipe MLOps</b>",
        "cover_subtitle",
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(P(
        f"Version 1.0  ·  {date.today().strftime('%d %B %Y')}",
        "cover_meta",
    ))

    story.append(NextPageTemplate("Content"))
    story.append(PageBreak())

    # ---- Sommaire ----
    story.append(P("Sommaire", "h1"))
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    story.append(toc)
    story.append(PageBreak())

    # ---- Guide de lecture ----
    story.append(P("Guide de lecture", "h1"))
    story.append(P(
        "Ce document présente <b>70 idées de projets fintech</b> sous forme de "
        "feuilles de route prêtes à attaquer. Pour chaque projet, vous trouverez "
        "le contexte métier, une feuille de route en quatre phases, la stack "
        "technique recommandée et les prérequis nécessaires.",
        "intro",
    ))

    story.append(P("Légende des niveaux", "h2"))
    legend_data = [
        [level_badge("JUNIOR"),
         P("Premier projet ML/data en autonomie. Sujet classique, exigeant rigueur et propreté.", "body")],
        [level_badge("INTERMÉDIAIRE"),
         P("Modélisation maîtrisée, intégration prod, observabilité. 1 à 2 ans d'expérience nécessaires.", "body")],
        [level_badge("SENIOR"),
         P("Sujet complexe : multi-composants, contraintes réglementaires, plateforme, ou recherche appliquée.", "body")],
    ]
    lt = Table(legend_data, colWidths=[3.5 * cm, 13 * cm])
    lt.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(lt)

    story.append(P("Structure d'une carte projet", "h2"))
    story.append(P(
        "Chaque projet est présenté sous la forme d'une carte autonome qui tient "
        "sur une page environ :",
        "intro",
    ))
    story.extend(bullets([
        "<b>Titre</b> et code projet (ex. 1.1, A.2, L.3).",
        "<b>Niveau requis</b> et <b>durée estimée</b> sous forme de badges.",
        "<b>Problème métier</b> : le « pourquoi » en une phrase.",
        "<b>Feuille de route</b> en 4 phases temporelles avec livrables.",
        "<b>Stack technique</b> : outils par couche (données, modèles, serving, monitoring).",
        "<b>Prérequis</b> : compétences clés à maîtriser avant d'attaquer.",
    ]))

    story.append(P("Recommandation d'attaque", "h2"))
    story.append(P(
        "Choisir un projet est plus important que d'en lire 65. Une bonne "
        "heuristique :",
        "intro",
    ))
    story.extend(bullets([
        "<b>Premier projet portfolio</b> : choisir un projet INTERMÉDIAIRE dont la stack ne contient aucun outil nouveau pour vous.",
        "<b>Montée en compétence</b> : choisir un projet INTERMÉDIAIRE / SENIOR avec UNE technologie nouvelle (graphes, streaming, LLM, etc.). Pas deux.",
        "<b>Recherche d'emploi</b> : viser un projet RegTech, climat ou crypto — pénurie de talents 2025-2026.",
    ]))

    story.append(PageBreak())

    # ---- Sections : projets groupés par catégorie ----
    current_cat = None
    for p in PROJECTS:
        if p["category"] != current_cat:
            current_cat = p["category"]
            story.append(P(current_cat, "h1"))
        story.append(project_card(p))

    # ---- Footer final ----
    story.append(Spacer(1, 1 * cm))
    story.append(P(
        "<i>Document de planification — équipe MLOps</i>",
        "cover_meta",
    ))

    doc.multiBuild(story)


def main() -> None:
    out_dir = Path("docs")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "Feuilles_de_route_Projets_Fintech.pdf"
    build(out_path)
    print(f"PDF généré : {out_path.resolve()}")
    print(f"Taille     : {out_path.stat().st_size / 1024:.1f} KB")
    print(f"Projets    : {len(PROJECTS)}")


if __name__ == "__main__":
    main()
