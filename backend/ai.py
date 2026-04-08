"""
AI service module for Meridian API.
Handles transcript analysis using Claude API or mock fallback.
"""

import json
import random
import datetime

from config import ANTHROPIC_AVAILABLE, USE_CLAUDE, ANTHROPIC_API_KEY


# ============================================================
# SYSTEM PROMPT FOR CLAUDE
# ============================================================
SYSTEM_PROMPT = """Tu es un analyste equity senior dans un hedge fund long/short avec 15 ans d'expérience sur les marchés. Tu analyses des transcripts d'earnings calls et tu produis des mémos d'investissement institutionnels.

## Ta mission

À partir du transcript fourni, produis une analyse complète et actionnable. Tu dois :

1. **Extraire les métriques exactes** mentionnées dans le transcript (revenue, EPS, margins, guidance). Ne jamais inventer de chiffres — utilise uniquement ce qui est dit explicitement. Si une métrique n'est pas mentionnée, indique current à 0 et yoyChange à 0. Pour les unités : revenue et freeCashFlow → "B USD" (ou "M USD"), eps → "USD", grossMargin et operatingMargin → "%" (toujours, même si la valeur est 0), debtToEquity → "x".

2. **Calculer les variations YoY** à partir des données du transcript. Si le transcript mentionne "revenue was $39.3B, up 78% year over year", utilise exactement ces chiffres.

3. **Structurer une thèse d'investissement** en identifiant :
   - Le narratif dominant du management (ce qu'ils veulent que le marché retienne)
   - Les points d'inflexion vs le quarter précédent
   - Les incohérences entre les résultats et le discours (si le management dit "strong" mais les chiffres disent autrement)

4. **Construire le bull case et le bear case** comme un analyste qui débat avec lui-même. Chaque case doit être honnête et défendable, avec des éléments spécifiques au transcript.

5. **Identifier les catalyseurs concrets** à surveiller — pas des généralités, mais des événements spécifiques mentionnés ou impliqués dans le call.

6. **Émettre une recommandation** BUY / HOLD / SELL avec un score de confiance entre 0.0 et 1.0. Sois tranchant.

7. **Calculer un scoring détaillé** sur 5 dimensions (chacune de 0 à 100) :
   - **growthScore** : dynamique de croissance (revenus, volumes, expansion géographique)
   - **profitabilityScore** : rentabilité et marges (gross margin, operating margin, FCF)
   - **momentumScore** : tendance vs trimestres précédents (accélération ou décélération)
   - **riskScore** : niveau de risque (dette, concentration clients, dépendance macro) — 100 = risque faible
   - **qualityScore** : qualité du management et de la communication (cohérence, guidance, transparence)

## Règles strictes

- JAMAIS de chiffres inventés. Si le transcript ne mentionne pas une métrique, mets current à 0 et unit à "N/A".
- Les variations YoY doivent correspondre exactement au transcript.
- La thèse doit être spécifique à cette entreprise et ce quarter, pas un template générique.
- Les facteurs de risque doivent citer des éléments concrets du call (noms de produits, marchés, concurrents mentionnés).
- Les catalyseurs doivent avoir des dates réalistes basées sur le calendrier habituel de l'entreprise.
- Écris en français, style institutionnel. Pas de bullet points dans les thèses — des paragraphes denses et analytiques.
- Chaque bullCase et bearCase doit contenir exactement 3 factors.
- Il doit y avoir exactement 3 catalysts.

## Format de sortie

Tu DOIS retourner UNIQUEMENT un JSON valide, sans aucun texte avant ou après. Pas de markdown, pas de ```json```, juste le JSON brut.

{
  "recommendation": "BUY" | "HOLD" | "SELL",
  "confidenceScore": 0.0 à 1.0,
  "thesisSummary": "string — 3-4 phrases denses résumant la thèse",
  "financialMetrics": {
    "revenue": {"current": number, "yoyChange": number, "unit": "string"},
    "eps": {"current": number, "yoyChange": number, "unit": "string"},
    "grossMargin": {"current": number, "yoyChange": number, "unit": "string"},
    "operatingMargin": {"current": number, "yoyChange": number, "unit": "string"},
    "debtToEquity": {"current": number, "yoyChange": number, "unit": "string"},
    "freeCashFlow": {"current": number, "yoyChange": number, "unit": "string"}
  },
  "bullCase": {
    "thesis": "string",
    "factors": [{"factor": "string", "impact": "HIGH"|"MEDIUM"|"LOW", "description": "string"}]
  },
  "bearCase": {
    "thesis": "string",
    "factors": [{"factor": "string", "impact": "HIGH"|"MEDIUM"|"LOW", "description": "string"}]
  },
  "catalysts": [
    {"name": "string", "expectedDate": "YYYY-MM-DD", "impact": "POSITIVE"|"NEGATIVE"|"NEUTRAL", "description": "string"}
  ],
  "detailedScoring": {
    "growthScore": 0-100,
    "profitabilityScore": 0-100,
    "momentumScore": 0-100,
    "riskScore": 0-100,
    "qualityScore": 0-100
  }
}"""


# ============================================================
# ANALYSIS DISPATCHER
# ============================================================
def analyze_transcript(transcript, company_name, ticker):
    """Analyse un transcript. Utilise Claude API si disponible, sinon mock."""
    if USE_CLAUDE:
        return _analyze_with_claude(transcript, company_name, ticker)
    return _analyze_mock(transcript, company_name, ticker)


def _analyze_with_claude(transcript, company_name, ticker):
    """Analyse via Claude API."""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Analyse le transcript suivant de l'earnings call de {company_name} ({ticker}).\n\nTRANSCRIPT:\n{transcript}\n\nProduis le mémo d'investissement complet en JSON structuré."
        }]
    )

    response_text = message.content[0].text.strip()
    # Nettoyer si Claude ajoute des backticks
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

    analysis = json.loads(response_text)

    # Validation
    required = ["recommendation", "confidenceScore", "thesisSummary",
                 "financialMetrics", "bullCase", "bearCase", "catalysts", "detailedScoring"]
    for key in required:
        if key not in analysis:
            raise ValueError(f"Clé manquante dans la réponse Claude: {key}")
    if analysis["recommendation"] not in ("BUY", "HOLD", "SELL"):
        analysis["recommendation"] = "HOLD"

    return analysis


def _analyze_mock(transcript, company_name, ticker):
    """Mock quand pas de clé API. Génère des données réalistes mais aléatoires."""
    text = transcript.lower()
    is_positive = any(w in text for w in ['growth', 'exceeded', 'strong', 'record', 'beat', 'croissance', 'hausse'])
    is_negative = any(w in text for w in ['decline', 'headwind', 'miss', 'challenging', 'baisse', 'recul'])

    if is_positive and not is_negative:
        rec = 'BUY'
    elif is_negative and not is_positive:
        rec = 'SELL'
    else:
        rec = 'HOLD'

    confidence = round(0.65 + random.random() * 0.25, 2)
    rev_base = round(5 + random.random() * 40, 1)
    rev_growth = round((8 + random.random() * 30) if is_positive else (-15 + random.random() * 10) if is_negative else (-2 + random.random() * 12), 1)

    def future_date(days):
        return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()

    thesis_map = {
        'BUY': f"{company_name} ({ticker}) affiche des résultats trimestriels supérieurs aux attentes du consensus, avec une accélération de la croissance organique et une expansion des marges opérationnelles. La guidance révisée à la hausse confirme la solidité du momentum commercial. Le profil risque/rendement reste attractif aux niveaux de valorisation actuels.",
        'SELL': f"{company_name} ({ticker}) déçoit sur les principaux indicateurs ce trimestre, avec une croissance en décélération marquée et des marges sous pression. La guidance abaissée suggère des vents contraires persistants. Le titre intègre insuffisamment ces risques aux niveaux actuels.",
        'HOLD': f"{company_name} ({ticker}) publie des résultats mitigés, avec des éléments positifs sur le chiffre d'affaires mais une rentabilité en demi-teinte. La visibilité limitée sur les prochains trimestres justifie une approche attentiste en attendant des catalyseurs plus clairs."
    }

    return {
        "recommendation": rec,
        "confidenceScore": confidence,
        "thesisSummary": thesis_map[rec],
        "financialMetrics": {
            "revenue": {"current": rev_base, "yoyChange": rev_growth, "unit": "B USD"},
            "eps": {"current": round(1 + random.random() * 8, 2), "yoyChange": round(rev_growth * 1.2 + (random.random() - 0.5) * 10, 1), "unit": "USD"},
            "grossMargin": {"current": round(35 + random.random() * 35, 1), "yoyChange": round((1.5 if is_positive else -2) * (1 + random.random()), 1), "unit": "%"},
            "operatingMargin": {"current": round(15 + random.random() * 25, 1), "yoyChange": round((1 if is_positive else -1.5) * (1 + random.random()), 1), "unit": "%"},
            "debtToEquity": {"current": round(0.2 + random.random() * 1.2, 2), "yoyChange": round(-10 + random.random() * 20, 1), "unit": "x"},
            "freeCashFlow": {"current": round(rev_base * 0.15 + random.random() * 3, 1), "yoyChange": round(rev_growth + (random.random() - 0.5) * 15, 1), "unit": "B USD"}
        },
        "bullCase": {
            "thesis": f"{company_name} dispose d'avantages compétitifs durables — technologie propriétaire, base clients captive et capacité d'innovation — qui devraient soutenir une surperformance relative dans un contexte de croissance séculaire de son marché adressable.",
            "factors": [
                {"factor": "Croissance du chiffre d'affaires", "impact": "HIGH", "description": f"{company_name} affiche une trajectoire de croissance soutenue portée par l'expansion de ses marchés adressables et le lancement de nouveaux produits."},
                {"factor": "Expansion des marges", "impact": "HIGH", "description": "Les efforts d'optimisation opérationnelle et l'effet de levier sur les coûts fixes permettent une amélioration structurelle de la rentabilité."},
                {"factor": "Positionnement concurrentiel", "impact": "MEDIUM", "description": f"La position de leader de {company_name} dans son segment crée des barrières à l'entrée significatives et un pricing power durable."}
            ]
        },
        "bearCase": {
            "thesis": f"La valorisation de {company_name} intègre un scénario de croissance optimiste qui laisse peu de place à la déception. L'intensification concurrentielle et les risques macro pourraient remettre en question la soutenabilité des marges actuelles.",
            "factors": [
                {"factor": "Valorisation tendue", "impact": "HIGH", "description": "Le titre se traite à un multiple élevé par rapport à ses moyennes historiques, laissant peu de marge d'erreur."},
                {"factor": "Risque macroéconomique", "impact": "MEDIUM", "description": "Un ralentissement économique global pourrait peser sur la demande et comprimer les multiples de valorisation du secteur."},
                {"factor": "Pression concurrentielle", "impact": "MEDIUM", "description": "L'intensification de la concurrence pourrait éroder les parts de marché et exercer une pression baissière sur les prix."}
            ]
        },
        "catalysts": [
            {"name": "Publication des résultats du prochain trimestre", "expectedDate": future_date(60), "impact": "POSITIVE" if is_positive else "NEUTRAL", "description": f"Les guidances de {company_name} seront déterminantes pour confirmer ou infirmer la trajectoire actuelle."},
            {"name": "Journée investisseurs / Analyst Day", "expectedDate": future_date(120), "impact": "POSITIVE", "description": "Potentielle révision à la hausse des objectifs moyen terme et présentation de la feuille de route produit."},
            {"name": "Décision réglementaire sectorielle", "expectedDate": future_date(180), "impact": "NEGATIVE", "description": "Évolution du cadre réglementaire susceptible d'impacter les marges ou les conditions d'exercice."}
        ],
        "detailedScoring": {
            "growthScore": min(95, max(15, int(55 + rev_growth * 1.2 + random.randint(-5, 5)))),
            "profitabilityScore": min(95, max(15, int(50 + (15 if is_positive else -10 if is_negative else 3) + random.randint(-8, 8)))),
            "momentumScore": min(95, max(15, int(45 + (25 if is_positive else -15 if is_negative else 5) + random.randint(-5, 5)))),
            "riskScore": min(95, max(15, int(60 + (-15 if is_negative else 10 if is_positive else 0) + random.randint(-10, 10)))),
            "qualityScore": min(95, max(20, int(65 + random.randint(-15, 15))))
        }
    }
