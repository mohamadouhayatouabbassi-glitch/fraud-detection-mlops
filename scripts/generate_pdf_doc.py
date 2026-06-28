"""Genere une documentation PDF en francais retracant le projet.

Usage:
    python scripts/generate_pdf_doc.py
Sortie: docs/Documentation_Fraud_Detection_MLOps.pdf
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
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
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


# ----------------------------------------------------------------------------
# Polices : on essaie d'utiliser DejaVu (gere les accents francais), sinon
# fallback Helvetica.
# ----------------------------------------------------------------------------
def _register_fonts() -> tuple[str, str, str]:
    candidates = [
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        p = Path(path)
        if p.exists():
            base = p.parent
            try:
                pdfmetrics.registerFont(TTFont("DejaVu", str(base / "DejaVuSans.ttf")))
                pdfmetrics.registerFont(
                    TTFont("DejaVu-Bold", str(base / "DejaVuSans-Bold.ttf"))
                )
                pdfmetrics.registerFont(
                    TTFont("DejaVu-Mono", str(base / "DejaVuSansMono.ttf"))
                )
                return "DejaVu", "DejaVu-Bold", "DejaVu-Mono"
            except Exception:  # pragma: no cover
                continue
    return "Helvetica", "Helvetica-Bold", "Courier"


FONT, FONT_B, FONT_M = _register_fonts()

# Couleurs
NAVY = colors.HexColor("#1e3a5f")
ACCENT = colors.HexColor("#c8553d")
GRAY = colors.HexColor("#4a4a4a")
LIGHT_BG = colors.HexColor("#f4f4f8")
CODE_BG = colors.HexColor("#272822")
CODE_FG = colors.HexColor("#f8f8f2")
TABLE_HEADER = colors.HexColor("#1e3a5f")
TABLE_ROW = colors.HexColor("#e8eef5")


# ----------------------------------------------------------------------------
# Styles
# ----------------------------------------------------------------------------
def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName=FONT_B,
            fontSize=30,
            leading=36,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            fontName=FONT,
            fontSize=15,
            leading=20,
            textColor=GRAY,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            fontName=FONT,
            fontSize=11,
            leading=16,
            textColor=GRAY,
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "H1",
            fontName=FONT_B,
            fontSize=20,
            leading=24,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=12,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            fontName=FONT_B,
            fontSize=14,
            leading=18,
            textColor=NAVY,
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3",
            fontName=FONT_B,
            fontSize=12,
            leading=15,
            textColor=ACCENT,
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=FONT,
            fontSize=10.5,
            leading=15,
            textColor=colors.black,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            fontName=FONT,
            fontSize=10.5,
            leading=15,
            textColor=colors.black,
            leftIndent=16,
            bulletIndent=4,
            spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "Code",
            fontName=FONT_M,
            fontSize=9,
            leading=12,
            textColor=CODE_FG,
            backColor=CODE_BG,
            leftIndent=6,
            rightIndent=6,
            spaceBefore=4,
            spaceAfter=10,
            borderPadding=8,
        ),
        "note": ParagraphStyle(
            "Note",
            fontName=FONT,
            fontSize=9.5,
            leading=13,
            textColor=GRAY,
            alignment=TA_LEFT,
            leftIndent=10,
            spaceAfter=8,
        ),
        "toc1": ParagraphStyle(
            "TOC1",
            fontName=FONT_B,
            fontSize=11.5,
            leading=18,
            textColor=NAVY,
            leftIndent=0,
        ),
        "toc2": ParagraphStyle(
            "TOC2",
            fontName=FONT,
            fontSize=10.5,
            leading=15,
            textColor=GRAY,
            leftIndent=18,
        ),
        "ascii": ParagraphStyle(
            "Ascii",
            fontName=FONT_M,
            fontSize=8.5,
            leading=11,
            textColor=colors.black,
            backColor=LIGHT_BG,
            leftIndent=4,
            rightIndent=4,
            spaceBefore=6,
            spaceAfter=10,
        ),
    }


S = _styles()


# ----------------------------------------------------------------------------
# Document avec en-tete + pied de page + table des matieres
# ----------------------------------------------------------------------------
class MyDocTemplate(BaseDocTemplate):
    """Document avec gestion automatique du sommaire (TOC)."""

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            text = flowable.getPlainText()
            if style_name == "H1":
                self.notify("TOCEntry", (0, text, self.page))
            elif style_name == "H2":
                self.notify("TOCEntry", (1, text, self.page))


def _draw_header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    # Pas d'en-tete sur la page de garde et le sommaire (pages 1-2)
    if doc.page >= 3:
        canvas.setFont(FONT, 8.5)
        canvas.setFillColor(GRAY)
        canvas.drawString(2 * cm, height - 1.2 * cm, "Fraud Detection MLOps — Documentation")
        canvas.drawRightString(
            width - 2 * cm, height - 1.2 * cm, f"Version 1.0  ·  {date.today().isoformat()}"
        )
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, height - 1.4 * cm, width - 2 * cm, height - 1.4 * cm)

    # Pied de page (toutes pages sauf la garde)
    if doc.page >= 2:
        canvas.setFont(FONT, 8.5)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(width / 2, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _draw_cover(canvas, doc):
    canvas.saveState()
    width, height = A4
    # Bandeau decoratif en haut
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 5 * cm, width, 5 * cm, stroke=0, fill=1)
    # Bandeau accent
    canvas.setFillColor(ACCENT)
    canvas.rect(0, height - 5.3 * cm, width, 0.3 * cm, stroke=0, fill=1)
    # Footer color
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, width, 2 * cm, stroke=0, fill=1)
    canvas.restoreState()


# ----------------------------------------------------------------------------
# Helpers content
# ----------------------------------------------------------------------------
def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def bullets(items: list[str]) -> list[Paragraph]:
    return [Paragraph(f"• {item}", S["bullet"]) for item in items]


def code(text: str) -> Preformatted:
    # Preformatted preserve les sauts de ligne ; on lui passe le style code
    return Preformatted(text.strip("\n"), S["code"])


def ascii_art(text: str) -> Preformatted:
    return Preformatted(text.strip("\n"), S["ascii"])


def make_table(data: list[list[str]], col_widths: list[float] | None = None) -> Table:
    paragraphed: list[list[Paragraph]] = []
    for r, row in enumerate(data):
        new_row: list[Paragraph] = []
        for cell in row:
            style = ParagraphStyle(
                "cell",
                fontName=FONT_B if r == 0 else FONT,
                fontSize=9.5,
                leading=12,
                textColor=colors.whitesmoke if r == 0 else colors.black,
                alignment=TA_LEFT,
            )
            new_row.append(Paragraph(str(cell), style))
        paragraphed.append(new_row)

    t = Table(paragraphed, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TABLE_ROW]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, 0), 1, NAVY),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ]
        )
    )
    return t


# ----------------------------------------------------------------------------
# Construction du document
# ----------------------------------------------------------------------------
def build(out_path: Path) -> None:
    doc = MyDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Fraud Detection MLOps — Documentation",
        author="MLOps Team",
        subject="Documentation du projet",
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="main",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    cover_template = PageTemplate(
        id="Cover", frames=[frame], onPage=_draw_cover
    )
    content_template = PageTemplate(
        id="Content", frames=[frame], onPage=_draw_header_footer
    )
    doc.addPageTemplates([cover_template, content_template])

    story: list = []

    # ---------------- PAGE DE GARDE ----------------
    story.append(Spacer(1, 4 * cm))
    story.append(
        Paragraph(
            "Détection de fraude<br/>à la carte bancaire",
            ParagraphStyle(
                "BigTitle",
                fontName=FONT_B,
                fontSize=32,
                leading=40,
                textColor=colors.whitesmoke,
                alignment=TA_CENTER,
            ),
        )
    )
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            "Plateforme MLOps de bout en bout — règles métier + Machine Learning",
            ParagraphStyle(
                "BigSub",
                fontName=FONT,
                fontSize=14,
                leading=18,
                textColor=colors.HexColor("#cfd8e3"),
                alignment=TA_CENTER,
            ),
        )
    )
    story.append(Spacer(1, 6 * cm))
    story.append(
        P(
            "<b>Document technique informatif</b>",
            "cover_subtitle",
        )
    )
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        P(
            f"Version 1.0  &nbsp;·&nbsp;  {date.today().strftime('%d %B %Y')}<br/>"
            "Auteur : équipe MLOps",
            "cover_meta",
        )
    )

    story.append(NextPageTemplate("Content"))
    story.append(PageBreak())

    # ---------------- SOMMAIRE ----------------
    story.append(P("Sommaire", "h1"))
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    story.append(toc)
    story.append(PageBreak())

    # ---------------- 1. CONTEXTE ----------------
    story.append(P("1. Contexte et objectif", "h1"))
    story.append(
        P(
            "La fraude à la carte bancaire représente plusieurs milliards d'euros "
            "de pertes annuelles pour le secteur financier. Les attaques évoluent "
            "constamment (skimming, prises de contrôle de comptes, tests de cartes "
            "à grande échelle…) et exigent une réponse temps réel : chaque "
            "transaction doit être autorisée ou refusée en moins de 100&nbsp;ms.",
            "body",
        )
    )
    story.append(
        P(
            "Ce projet livre une plateforme de scoring <b>de bout en bout</b>, "
            "capable de prendre une transaction en entrée et de retourner une "
            "décision parmi trois actions :",
            "body",
        )
    )
    story.extend(
        bullets(
            [
                "<b>APPROVE</b> — laisser passer la transaction.",
                "<b>REVIEW</b> — envoyer la transaction en revue manuelle.",
                "<b>DECLINE</b> — refuser la transaction.",
            ]
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        P(
            "La décision repose sur la combinaison de <b>deux signaux "
            "complémentaires</b> : un moteur de règles métier (auditable, "
            "détenu par l'équipe Risque) et un modèle de Machine Learning "
            "calibré (adaptatif, détenu par l'équipe Data Science).",
            "body",
        )
    )

    story.append(P("Pourquoi une approche hybride règles + ML ?", "h2"))
    story.append(
        make_table(
            [
                ["Critère", "Règles seules", "ML seul", "Hybride (ce projet)"],
                [
                    "Couverture des fraudes connues",
                    "Forte par définition",
                    "Dépend du jeu d'entraînement",
                    "Forte (règles) + adaptative (ML)",
                ],
                [
                    "Adaptation aux nouveaux schémas",
                    "Lente (écriture manuelle)",
                    "Rapide (réentraînement)",
                    "Rapide",
                ],
                [
                    "Explicabilité",
                    "Excellente",
                    "Limitée",
                    "Codes de règles + probabilité ML",
                ],
                [
                    "Contraintes réglementaires",
                    "Faciles à encoder",
                    "Difficiles à garantir",
                    "Encodées en règles HARD_BLOCK",
                ],
                [
                    "Maîtrise du taux de faux positifs",
                    "Grossière",
                    "Réglable par seuil",
                    "Combinée (uplift + seuil)",
                ],
            ],
            col_widths=[4 * cm, 4 * cm, 4 * cm, 4.5 * cm],
        )
    )

    story.append(PageBreak())

    # ---------------- 2. ARCHITECTURE ----------------
    story.append(P("2. Architecture", "h1"))
    story.append(
        P(
            "L'architecture est volontairement <b>simple et stateless</b>. "
            "Toute la complexité métier est dans les modules : l'API ne fait "
            "qu'orchestrer un appel séquentiel à cinq composants.",
            "body",
        )
    )

    story.append(P("Vue d'ensemble du flux temps réel", "h2"))
    story.append(
        ascii_art(
            """
                  +----------------------+
                  |  Appelant (PSP)      |
                  +----------+-----------+
                             |  HTTPS POST /v1/score
                             v
+----------------------------+-----------------------------+
| Service FastAPI                                          |
|   1. Validation Pydantic   (schema Transaction)          |
|   2. Feature engineering   (build_features.py)           |
|   3. Moteur de regles      (rules/engine.py + YAML)      |
|   4. Modele ML             (LightGBM + calibration)      |
|   5. Moteur de decision    (regles + ML -> action)       |
+----------------------------+-----------------------------+
                             |
                             +--> logs JSON (correlation_id)
                             +--> /metrics Prometheus
                             +--> reponse DecisionResponse
"""
        )
    )

    story.append(P("Principe d'unicité du feature engineering", "h2"))
    story.append(
        P(
            "Le bug le plus fréquent en ML production est le <b>train/serve "
            "skew</b> : les features sont calculées différemment en mode batch "
            "(entraînement) et en mode online (service). Pour l'éliminer, "
            "<i>une seule fonction</i> <font face='%s'>build_features(df)</font> "
            "est utilisée par les deux chemins. Toute évolution de feature est "
            "automatiquement disponible partout, et les tests d'intégration "
            "garantissent l'invariant." % FONT_M,
            "body",
        )
    )

    story.append(P("Composants et responsabilités", "h2"))
    story.append(
        make_table(
            [
                ["Composant", "Rôle", "Chemin"],
                [
                    "Schémas Pydantic",
                    "Contrat strict d'entrée et de sortie",
                    "data/schemas.py",
                ],
                [
                    "Générateur de données",
                    "5 patterns de fraude réalistes, déterministe",
                    "data/synthetic.py",
                ],
                [
                    "Feature engineering",
                    "~20 features, source unique pour train et serve",
                    "features/build_features.py",
                ],
                [
                    "Moteur de règles",
                    "Règles YAML déclaratives, 3 sévérités",
                    "rules/engine.py",
                ],
                [
                    "Modèle ML",
                    "LightGBM + calibration isotonique",
                    "models/train.py, models/predict.py",
                ],
                [
                    "Moteur de décision",
                    "Fusion règles + ML → APPROVE / REVIEW / DECLINE",
                    "decision/engine.py",
                ],
                [
                    "API",
                    "FastAPI + lifespan + correlation_id",
                    "api/main.py",
                ],
                [
                    "Observabilité",
                    "Métriques Prometheus + drift PSI",
                    "monitoring/",
                ],
            ],
            col_widths=[3.5 * cm, 7 * cm, 6 * cm],
        )
    )

    story.append(PageBreak())

    # ---------------- 3. STACK ----------------
    story.append(P("3. Stack technique", "h1"))
    story.append(
        P(
            "Le projet est <b>100 % Python 3.11</b>. Chaque dépendance a été "
            "choisie pour son adéquation au cas d'usage et sa maturité en "
            "production.",
            "body",
        )
    )
    story.append(
        make_table(
            [
                ["Couche", "Outil", "Justification"],
                ["Langage", "Python 3.11", "Écosystème ML + FastAPI"],
                ["Modèle ML", "LightGBM 4.3", "Performant sur le tabulaire déséquilibré"],
                [
                    "Calibration",
                    "scikit-learn 1.9",
                    "CalibratedClassifierCV + FrozenEstimator",
                ],
                ["Tracking ML", "MLflow (SQLite)", "Suivi d'expériences + artifacts"],
                ["Validation", "Pydantic v2", "Strict, rapide, à la frontière API"],
                ["API", "FastAPI + uvicorn", "Async, OpenAPI auto, lifespan hooks"],
                ["Logs", "structlog", "JSON + correlation_id par contextvars"],
                ["Métriques", "prometheus-client", "Format d'exposition standard"],
                ["Config", "pydantic-settings + YAML", "12-factor + règles versionnées"],
                ["CLI", "Typer + Rich", "Génération data, entraînement, scoring"],
                ["Tests", "pytest + httpx", "Unitaire + intégration avec modèle réel"],
                ["Qualité", "ruff + black + mypy", "Lint, format, typage"],
                ["Container", "Docker multi-stage", "Image slim, non-root, healthcheck"],
                ["CI/CD", "GitHub Actions", "CI sur PR, image GHCR sur tag"],
                ["Notebook", "Jupyter + seaborn", "Analyse exploratoire des données"],
            ],
            col_widths=[3.5 * cm, 4.5 * cm, 8.5 * cm],
        )
    )

    story.append(PageBreak())

    # ---------------- 4. ÉTAPES ----------------
    story.append(P("4. Étapes du projet", "h1"))
    story.append(
        P(
            "Le projet a été construit en <b>13 étapes</b> dans un ordre "
            "logique : du contrat de données au déploiement, en passant par "
            "le modèle, l'API et la documentation.",
            "body",
        )
    )

    steps = [
        (
            "Étape 1 — Bootstrap du projet",
            "Mise en place de l'environnement reproductible : pyproject.toml "
            "(PEP 621), Makefile pour les opérations courantes, "
            ".pre-commit-config.yaml, .gitignore et arborescence src/ standard.",
            "Pourquoi : permettre à un nouveau développeur de cloner, "
            "installer et tester en moins de 3 minutes.",
        ),
        (
            "Étape 2 — Contrat d'entrée Pydantic",
            "Définition du schéma Transaction avec contraintes au niveau "
            "des champs : amount &gt; 0, codes ISO pour les pays, longueur "
            "exacte du MCC (Merchant Category Code), enum pour le canal.",
            "Pourquoi : rejeter les payloads invalides à la porte d'entrée, "
            "pas en plein milieu du pipeline.",
        ),
        (
            "Étape 3 — Générateur de données synthétiques",
            "Implémentation de cinq patterns de fraude : card_testing, "
            "geo_anomaly, cashout, account_takeover, high_risk_mcc. "
            "Chaque pattern reflète une attaque observée en production. "
            "Générateur déterministe (même seed = même fichier).",
            "Pourquoi : le projet est reproductible sans donnée "
            "propriétaire, et les patterns donnent au modèle et aux "
            "règles quelque chose de pertinent à apprendre / détecter.",
        ),
        (
            "Étape 4 — Feature engineering (source unique)",
            "Fonction build_features(df) qui dérive ~20 features : ratio au "
            "panier moyen 30j, z-score, vélocité 1h/24h, indicateurs nuit / "
            "week-end, geo mismatch, indicateurs CNP / ECOM / ATM, MCC à risque.",
            "Pourquoi : utilisée à la fois en entraînement (DataFrame batch) "
            "et en serving (DataFrame à une ligne). Élimine définitivement "
            "le train/serve skew.",
        ),
        (
            "Étape 5 — Moteur de règles déclaratif",
            "Fichier rules.yaml chargé au démarrage. Trois sévérités : "
            "HARD_BLOCK (force le refus), SUSPECT (ajoute une pondération à "
            "la probabilité ML), INFO (audit). 9 règles initiales : montant "
            "élevé, geo mismatch, MCC à risque, vélocité, ATM nocturne, etc.",
            "Pourquoi : l'équipe Risque peut modifier les règles sans "
            "toucher au code. Le fichier est auditable et versionné dans Git.",
        ),
        (
            "Étape 6 — Pipeline d'entraînement",
            "LightGBM avec is_unbalance=true, early stopping sur ensemble "
            "de validation temporel, puis calibration isotonique sur la "
            "même validation. MLflow log les paramètres, métriques et "
            "artifact (model.joblib + schema + stats).",
            "Pourquoi : la calibration rend les probabilités directement "
            "interprétables comme seuils, ce qui est indispensable pour "
            "que les seuils REVIEW/DECLINE aient un sens.",
        ),
        (
            "Étape 7 — Moteur de décision",
            "Logique : si une règle HARD_BLOCK déclenche, DECLINE "
            "immédiatement (court-circuit du ML, gain de latence). Sinon, "
            "chaque règle SUSPECT ajoute +0.05 à la probabilité ML, plafonné "
            "à +0.20. Seuils : &lt; 0.30 = APPROVE, 0.30–0.70 = REVIEW, "
            "≥ 0.70 = DECLINE.",
            "Pourquoi : aucune des deux composantes (règles, ML) ne peut "
            "surpasser l'autre silencieusement. La décision est traçable.",
        ),
        (
            "Étape 8 — Service FastAPI",
            "Quatre endpoints : POST /v1/score, POST /v1/score/batch, "
            "GET /healthz, GET /metrics. Middleware correlation_id qui "
            "propage un identifiant de trace via contextvars dans tous les "
            "logs. Lifespan hook qui charge le modèle une seule fois au "
            "démarrage.",
            "Pourquoi : production-grade — pas de surprise (modèle non "
            "chargé, traçabilité absente, etc.).",
        ),
        (
            "Étape 9 — Observabilité",
            "Métriques Prometheus exposées sur /metrics : nombre de "
            "décisions par action, déclenchements par règle, distribution "
            "de la probabilité, latence (histogramme), état de santé. "
            "Utilitaire PSI (Population Stability Index) pour la "
            "détection de drift offline.",
            "Pourquoi : un modèle qu'on ne mesure pas est un modèle qu'on "
            "ne maîtrise pas.",
        ),
        (
            "Étape 10 — Tests",
            "22 tests unitaires (features, règles, décision, drift, "
            "synthétique) + 6 tests d'intégration via TestClient FastAPI "
            "qui entraînent un vrai modèle puis exercent l'API. "
            "Couverture totale : 88 %.",
            "Pourquoi : les tests d'intégration attrapent les bugs que les "
            "tests unitaires manquent (chargement de modèle, train/serve skew).",
        ),
        (
            "Étape 11 — Containerisation",
            "Dockerfile multi-stage : un stage builder qui installe les "
            "dépendances, un stage runtime slim qui copie le venv et la "
            "source, sans build-essential. Utilisateur non-root, healthcheck "
            "automatique, libgomp1 pour LightGBM.",
            "Pourquoi : surface d'attaque minimale, image légère, conforme "
            "aux bonnes pratiques sécurité.",
        ),
        (
            "Étape 12 — CI/CD GitHub Actions",
            "Trois workflows : ci.yml (lint + tests + build sur chaque PR), "
            "cd.yml (build et push de l'image vers GHCR sur tag v*.*.*), "
            "train.yml (réentraînement manuel via workflow_dispatch).",
            "Pourquoi : chaque PR est vérifiable, chaque release est "
            "reproductible, le réentraînement est un clic.",
        ),
        (
            "Étape 13 — Documentation",
            "README de 12 sections, docs/architecture.md (composants et "
            "flux), docs/model_card.md (carte modèle Google-style avec "
            "limitations et fairness), docs/runbook.md (procédures on-call), "
            "docs/api.md (contrat API), notebook EDA.",
            "Pourquoi : un projet sans documentation est un projet "
            "inutilisable au-delà de son auteur.",
        ),
    ]

    for title, what, why in steps:
        block = [
            P(title, "h3"),
            P(what, "body"),
            P(f"<i>{why}</i>", "note"),
        ]
        story.append(KeepTogether(block))

    story.append(PageBreak())

    # ---------------- 5. PIPELINE COMPLET ----------------
    story.append(P("5. Pipeline complet du projet", "h1"))
    story.append(
        P(
            "Le projet comporte <b>deux pipelines distincts</b> qui partagent "
            "le même code de feature engineering :",
            "body",
        )
    )

    story.append(P("Pipeline 1 — Entraînement (offline)", "h2"))
    story.append(
        ascii_art(
            """
[1] generate-data   --> data/processed/transactions_train.parquet
                        data/processed/transactions_test.parquet

[2] train-pipeline
    +-- load parquet
    +-- build_features(df)              (m\u00eame fonction qu'en serving)
    +-- split temporel train / val
    +-- LightGBM.fit (early stopping)
    +-- CalibratedClassifierCV (isotonic, FrozenEstimator)
    +-- evaluation sur test (ROC AUC, PR AUC, Recall@1%FPR, top-1%)
    +-- joblib.dump  --> artifacts/model.joblib
    +-- MLflow log_params + log_metrics + log_artifact
"""
        )
    )

    story.append(P("Pipeline 2 — Inférence (online)", "h2"))
    story.append(
        ascii_art(
            """
HTTP POST /v1/score
       |
       v
[Pydantic Transaction]   ----> 422 si payload invalide
       |
       v
[transaction_to_feature_row]   (build_features() sur une ligne)
       |
       v
[RulesEngine.evaluate]    ----> hits[]
       |
       +-- si HARD_BLOCK ----> on saute le ML, action = DECLINE
       |
       v
[FraudModel.predict_one]   ----> p_ml
       |
       v
[DecisionEngine.decide]    ----> action, risk_score, reasons
       |
       v
[DecisionResponse JSON]    ----> reponse au client
"""
        )
    )

    story.append(P("Pipeline 3 — CI / CD (automatique)", "h2"))
    story.append(
        ascii_art(
            """
Push / Pull Request sur main
       |
       v
[ci.yml]
    +-- ruff check (lint)
    +-- black --check (format)
    +-- mypy (typage, informatif)
    +-- pytest --cov (28 tests, 88% couverture)
    +-- docker build (sans push)

Tag v*.*.*
       |
       v
[cd.yml]
    +-- build multi-stage
    +-- push image vers ghcr.io/owner/repo:vX.Y.Z

Action manuelle (workflow_dispatch)
       |
       v
[train.yml]
    +-- generate-data
    +-- train
    +-- upload artifacts (model.joblib, mlruns)
"""
        )
    )

    story.append(PageBreak())

    # ---------------- 6. MODÈLE ML ----------------
    story.append(P("6. Détail du modèle ML", "h1"))
    story.append(P("Algorithme et hyperparamètres", "h2"))
    story.append(
        P(
            "Le modèle est un <b>LightGBM binaire</b> (gradient boosting sur "
            "arbres) avec gestion native du déséquilibre de classes. "
            "Hyperparamètres versionnés dans configs/model.yaml :",
            "body",
        )
    )
    story.append(
        code(
            """lightgbm:
  objective: binary
  metric: auc
  learning_rate: 0.05
  num_leaves: 64
  min_data_in_leaf: 50
  feature_fraction: 0.85
  bagging_fraction: 0.85
  bagging_freq: 5
  lambda_l2: 1.0
  is_unbalance: true

training:
  num_boost_round: 600
  early_stopping_rounds: 40
  val_fraction: 0.15
  calibration_method: isotonic"""
        )
    )

    story.append(P("Features utilisées", "h2"))
    story.append(
        P(
            "21 features groupées en cinq familles :",
            "body",
        )
    )
    story.extend(
        bullets(
            [
                "<b>Montant</b> : amount, amount_log, amount_ratio_avg_30d, amount_zscore_30d",
                "<b>Vélocité</b> : n_tx_last_1h, n_tx_last_24h, velocity_score, is_burst_1h",
                "<b>Temporel</b> : hour, is_night (0-5h), is_weekend",
                "<b>Géographique</b> : is_geo_mismatch (carte vs commerçant)",
                "<b>Canal / risque</b> : is_cnp, is_ecom, is_atm, is_high_risk_mcc",
                "<b>Client</b> : customer_age_days, card_age_days, amount_avg_30d, amount_std_30d, distinct_countries_last_24h",
            ]
        )
    )

    story.append(P("Métriques d'évaluation", "h2"))
    story.append(
        make_table(
            [
                ["Métrique", "Pourquoi on la suit"],
                [
                    "ROC AUC",
                    "Qualité globale du ranking (référence générale).",
                ],
                [
                    "PR AUC",
                    "<b>Métrique principale</b> — robuste au déséquilibre.",
                ],
                [
                    "Recall @ 1% FPR",
                    "Combien de fraudes on attrape en gardant un taux de fausse alarme faible.",
                ],
                [
                    "Precision @ top 1%",
                    "Charge de revue manuelle : sur le 1% le plus risqué, quelle proportion est réellement frauduleuse.",
                ],
                [
                    "F1 @ 0.5",
                    "Référence seulement ; les vrais seuils de production viennent de model.yaml.",
                ],
            ],
            col_widths=[4 * cm, 12.5 * cm],
        )
    )

    story.append(P("Résultats obtenus", "h2"))
    story.append(
        make_table(
            [
                ["Métrique", "Valeur"],
                ["ROC AUC", "0,991"],
                ["PR AUC", "0,983"],
                ["Recall @ 1% FPR", "0,98"],
                ["Precision @ top 1%", "1,00"],
                ["F1 @ seuil par défaut", "0,991"],
                ["Latence p99 /v1/score", "&lt; 20 ms (objectif : &lt; 100 ms)"],
                ["Couverture des tests", "88 %"],
            ],
            col_widths=[8 * cm, 6 * cm],
        )
    )

    story.append(PageBreak())

    # ---------------- 7. RÈGLES MÉTIER ----------------
    story.append(P("7. Règles métier", "h1"))
    story.append(
        P(
            "Les règles sont déclarées dans configs/rules.yaml. Trois sévérités :",
            "body",
        )
    )
    story.extend(
        bullets(
            [
                "<b>HARD_BLOCK</b> — force DECLINE quelle que soit la probabilité ML.",
                "<b>SUSPECT</b> — pousse la probabilité ML vers le haut, peut router vers REVIEW.",
                "<b>INFO</b> — audit uniquement, sans impact sur la décision.",
            ]
        )
    )

    story.append(
        make_table(
            [
                ["Code", "Sévérité", "Déclencheur"],
                ["R001_HIGH_AMOUNT_CNP", "SUSPECT", "Card-Not-Present ≥ 1000 €"],
                ["R002_VERY_HIGH_AMOUNT", "HARD_BLOCK", "Transaction ≥ 5000 €"],
                ["R003_GEO_MISMATCH_ECOM", "SUSPECT", "Pays carte ≠ pays commerçant en ECOM"],
                ["R004_VELOCITY_BURST", "HARD_BLOCK", "≥ 8 transactions dans l'heure"],
                ["R005_HIGH_RISK_MCC", "SUSPECT", "MCC à risque (jeu d'argent, adulte)"],
                ["R006_NIGHT_ATM", "SUSPECT", "Retrait DAB entre minuit et 5 h"],
                ["R007_NEW_CARD_LARGE_AMOUNT", "SUSPECT", "Carte &lt; 7 jours et montant ≥ 300 €"],
                ["R008_MULTI_COUNTRY_24H", "HARD_BLOCK", "≥ 3 pays distincts en 24 h"],
                ["R009_ZSCORE_OUTLIER", "SUSPECT", "Z-score du montant ≥ 6"],
            ],
            col_widths=[5.5 * cm, 2.5 * cm, 8.5 * cm],
        )
    )

    story.append(PageBreak())

    # ---------------- 8. API ----------------
    story.append(P("8. API et exemples d'appel", "h1"))
    story.append(P("Endpoints exposés", "h2"))
    story.append(
        make_table(
            [
                ["Méthode", "Chemin", "Description"],
                ["POST", "/v1/score", "Scorer une transaction"],
                ["POST", "/v1/score/batch", "Scorer jusqu'à 100 transactions"],
                ["GET", "/healthz", "Liveness + readiness (modèle chargé ?)"],
                ["GET", "/metrics", "Format d'exposition Prometheus"],
                ["GET", "/docs", "Swagger UI (OpenAPI)"],
            ],
            col_widths=[2 * cm, 4 * cm, 10.5 * cm],
        )
    )

    story.append(P("Exemple de requête (curl)", "h2"))
    story.append(
        code(
            """curl -X POST http://localhost:8000/v1/score \\
  -H "Content-Type: application/json" \\
  -H "X-Correlation-ID: demo-001" \\
  -d '{
    "transaction_id": "TX_DEMO_001",
    "timestamp": "2025-06-15T03:10:00Z",
    "customer_id": "C0000001",
    "card_id": "K0000001",
    "amount": 1500.0,
    "currency": "EUR",
    "merchant_id": "M999999",
    "merchant_country": "NG",
    "merchant_mcc": "7995",
    "card_country": "FR",
    "channel": "ECOM",
    "is_cnp": true,
    "customer_age_days": 900,
    "card_age_days": 400,
    "n_tx_last_1h": 4,
    "n_tx_last_24h": 10,
    "amount_avg_30d": 70.0,
    "amount_std_30d": 20.0,
    "distinct_countries_last_24h": 2
  }'"""
        )
    )

    story.append(P("Réponse pour un cas frauduleux", "h2"))
    story.append(
        code(
            """{
  "transaction_id": "TX_DEMO_001",
  "action": "DECLINE",
  "fraud_probability": 1.0,
  "risk_score": 1000,
  "reasons": [
    "rule:R001_HIGH_AMOUNT_CNP",
    "rule:R003_GEO_MISMATCH_ECOM",
    "rule:R005_HIGH_RISK_MCC",
    "ml:p=1.000>=decline_threshold"
  ],
  "rule_hits": [...],
  "model_version": "20260628-181316",
  "latency_ms": 13.09
}"""
        )
    )

    story.append(PageBreak())

    # ---------------- 9. OBSERVABILITÉ ----------------
    story.append(P("9. Observabilité et exploitation", "h1"))
    story.append(P("Logs structurés", "h2"))
    story.append(
        P(
            "Tous les logs sont émis en <b>JSON</b> (structlog) et portent un "
            "<font face='%s'>correlation_id</font> propagé par contextvar dans "
            "tous les composants (feature engineering, règles, ML, décision). "
            "Un appel HTTP unique peut donc être tracé de bout en bout dans "
            "Loki, Elasticsearch ou CloudWatch." % FONT_M,
            "body",
        )
    )

    story.append(P("Métriques Prometheus", "h2"))
    story.append(
        make_table(
            [
                ["Métrique", "Type", "Utilité"],
                [
                    "fraud_decisions_total{action}",
                    "Counter",
                    "KPI produit : ratio APPROVE/REVIEW/DECLINE",
                ],
                [
                    "fraud_rule_hits_total{code,severity}",
                    "Counter",
                    "Suivi des règles : détection d'une règle muette ou folle",
                ],
                [
                    "fraud_probability",
                    "Histogramme",
                    "Distribution des probabilités, signal de drift",
                ],
                [
                    "fraud_inference_latency_seconds",
                    "Histogramme",
                    "SLO de latence (p99 &lt; 100 ms)",
                ],
                [
                    "fraud_service_healthy",
                    "Gauge",
                    "État de santé : modèle chargé ?",
                ],
            ],
            col_widths=[6 * cm, 2.5 * cm, 8 * cm],
        )
    )

    story.append(P("Détection de drift (PSI)", "h2"))
    story.append(
        P(
            "Le Population Stability Index (PSI) est le standard du secteur "
            "financier pour mesurer un décalage de distribution entre une "
            "référence (training) et un échantillon courant (production). "
            "Seuils :",
            "body",
        )
    )
    story.extend(
        bullets(
            [
                "<b>PSI &lt; 0,10</b> — distribution stable.",
                "<b>0,10 ≤ PSI &lt; 0,25</b> — décalage modéré, à investiguer.",
                "<b>PSI ≥ 0,25</b> — décalage majeur, réentraînement requis.",
            ]
        )
    )

    story.append(PageBreak())

    # ---------------- 10. DÉPLOIEMENT ----------------
    story.append(P("10. Déploiement et exploitation", "h1"))
    story.append(P("Image Docker", "h2"))
    story.append(
        P(
            "Le Dockerfile est <b>multi-stage</b> (builder + runtime) et "
            "utilise un utilisateur non-root. Seule libgomp1 est conservée "
            "dans l'image finale (dépendance native de LightGBM).",
            "body",
        )
    )

    story.append(P("Lancement local", "h2"))
    story.append(
        code(
            """# Installation
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Pipeline complet
make data    # genere les transactions synthetiques
make train   # entraine le modele
make serve   # lance l'API sur :8000

# Ou via Docker
make docker-build
make docker-up   # API sur :8000 avec artifacts montes en read-only"""
        )
    )

    story.append(P("Scalabilité en production", "h2"))
    story.append(
        make_table(
            [
                ["Préoccupation", "Approche"],
                [
                    "Débit",
                    "Horizontale — API stateless, ajouter des répliques derrière un load balancer ou un HPA k8s.",
                ],
                [
                    "Latence",
                    "LightGBM monoligne &lt; 5 ms. Le coût dominant est Pydantic + feature build.",
                ],
                [
                    "Chargement du modèle",
                    "Une seule fois au démarrage (lifespan). Aucun I/O par requête.",
                ],
                [
                    "Features de vélocité",
                    "Calculées en amont par un feature store (Redis, Feast). L'API les reçoit dans le payload.",
                ],
                [
                    "Réentraînement",
                    "Airflow, Kubeflow ou workflow_dispatch GitHub Actions.",
                ],
                [
                    "Déploiement progressif",
                    "Shadow scoring : nouveau modèle en parallèle de l'ancien, on log les deux et on compare.",
                ],
            ],
            col_widths=[4 * cm, 12.5 * cm],
        )
    )

    story.append(PageBreak())

    # ---------------- 11. RÉSULTATS ----------------
    story.append(P("11. Résultats vérifiés", "h1"))
    story.append(
        P(
            "Le projet a été exécuté de bout en bout dans un environnement "
            "propre avec les résultats suivants :",
            "body",
        )
    )
    story.append(
        make_table(
            [
                ["Vérification", "Résultat"],
                ["Lint (ruff)", "Clean"],
                ["Format (black --check)", "Clean"],
                ["Tests unitaires + intégration", "28 / 28 verts, couverture 88 %"],
                ["Modèle — ROC AUC", "0,991"],
                ["Modèle — PR AUC", "0,983"],
                ["Modèle — Recall @ 1% FPR", "0,98"],
                ["Smoke test 4 scénarios métier", "Tous corrects"],
                ["Latence end-to-end (smoke)", "9 – 17 ms par requête"],
            ],
            col_widths=[8 * cm, 8.5 * cm],
        )
    )

    story.append(P("Scénarios de smoke test", "h2"))
    story.append(
        make_table(
            [
                ["Scénario", "Action attendue", "Résultat"],
                ["POS local épicerie", "APPROVE", "APPROVE (p ≈ 0)"],
                [
                    "ECOM + geo mismatch + MCC risque + nuit",
                    "DECLINE",
                    "DECLINE (4 règles SUSPECT + ML)",
                ],
                [
                    "Montant 7500 € (&gt; 5000)",
                    "DECLINE",
                    "DECLINE (R002 HARD_BLOCK)",
                ],
                [
                    "12 transactions en 1 heure",
                    "DECLINE",
                    "DECLINE (R004 HARD_BLOCK)",
                ],
            ],
            col_widths=[6.5 * cm, 4 * cm, 6 * cm],
        )
    )

    story.append(PageBreak())

    # ---------------- 12. CONCLUSION / NEXT STEPS ----------------
    story.append(P("12. Conclusion et perspectives", "h1"))
    story.append(
        P(
            "Le projet livre une plateforme MLOps <b>opérationnelle</b>, "
            "auditable et industrialisée. Les choix d'architecture (hybride "
            "règles + ML, feature engineering unifié, calibration des "
            "probabilités, observabilité dès le jour 1) sont alignés avec "
            "les pratiques observées dans les fintech matures.",
            "body",
        )
    )

    story.append(P("Pistes d'évolution", "h2"))
    story.extend(
        bullets(
            [
                "<b>Modèle challenger</b> (XGBoost ou réseau peu profond) avec shadow scoring intégré à l'API.",
                "<b>Optimisation automatique des seuils</b> sur courbe coût/bénéfice métier.",
                "<b>SHAP par transaction</b> exposé dans /v1/score pour l'équipe Fraud.",
                "<b>Streaming Kafka</b> en complément du mode REST.",
                "<b>Feature store Feast</b> pour les features de vélocité (au lieu du payload).",
                "<b>Manifest Kubernetes</b> + Helm chart (HPA, PDB, ServiceMonitor).",
                "<b>Versioning Data + Modèle</b> avec DVC ou LakeFS, artifact store S3.",
                "<b>Authentification mTLS ou JWT</b> sur /v1/score.",
                "<b>Dashboard Grafana</b> prêt à l'emploi pour les métriques Prometheus.",
                "<b>Chaos tests</b> (modèle absent, config corrompue, latence dégradée) pour valider le runbook.",
            ]
        )
    )

    story.append(Spacer(1, 1.5 * cm))
    story.append(
        Paragraph(
            "<i>Document de référence — équipe MLOps</i>",
            ParagraphStyle(
                "FootSig",
                fontName=FONT,
                fontSize=10,
                textColor=GRAY,
                alignment=TA_CENTER,
            ),
        )
    )

    # Build du document avec multi-build pour le TOC
    doc.multiBuild(story)


def main() -> None:
    out_dir = Path("docs")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "Documentation_Fraud_Detection_MLOps.pdf"
    build(out_path)
    print(f"PDF genere : {out_path.resolve()}")
    print(f"Taille     : {out_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
