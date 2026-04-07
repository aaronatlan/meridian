"""
Export module for Meridian API.
Generates HTML memo documents from analysis results.
"""

import math


def generate_memo_html(company, ticker, quarter, created_at, analysis):
    """Generate a professional printable HTML memo with scoring radar."""
    a = analysis
    rec_color = {"BUY": "#16a34a", "SELL": "#dc2626", "HOLD": "#d97706"}.get(a["recommendation"], "#333")
    rec_bg = {"BUY": "#f0fdf4", "SELL": "#fef2f2", "HOLD": "#fffbeb"}.get(a["recommendation"], "#f8f9fa")

    def metric_row(label, m):
        change = m["yoyChange"]
        color = "#16a34a" if change >= 0 else "#dc2626"
        sign = "+" if change >= 0 else ""
        bar_w = min(abs(change) * 2, 100)
        bar_dir = "right" if change >= 0 else "left"
        return f'''<tr>
<td style="padding:12px 16px;border-bottom:1px solid #f1f5f9;font-weight:500">{label}</td>
<td style="padding:12px 16px;border-bottom:1px solid #f1f5f9;text-align:right;font-family:'SF Mono',Consolas,monospace;font-size:13px">{m["current"]} {m["unit"]}</td>
<td style="padding:12px 16px;border-bottom:1px solid #f1f5f9;text-align:right;font-family:'SF Mono',Consolas,monospace;font-size:13px;color:{color};font-weight:600">{sign}{change}%</td>
<td style="padding:12px 16px;border-bottom:1px solid #f1f5f9;width:120px"><div style="height:6px;background:#f1f5f9;border-radius:3px;overflow:hidden"><div style="height:100%;width:{bar_w}%;background:{color};border-radius:3px;float:{bar_dir}"></div></div></td>
</tr>'''

    def factor_html(f, color_theme):
        ic = {"HIGH": "#dc2626", "MEDIUM": "#d97706", "LOW": "#16a34a"}.get(f["impact"], "#666")
        return f'''<div style="margin-bottom:16px;padding:12px 16px;background:#f8fafc;border-radius:8px;border-left:3px solid {color_theme}">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<span style="font-size:10px;font-weight:700;color:{ic};background:{ic}12;padding:2px 8px;border-radius:4px;letter-spacing:0.05em">{f["impact"]}</span>
<strong style="font-size:14px">{f["factor"]}</strong>
</div><div style="color:#64748b;font-size:13px;line-height:1.6">{f["description"]}</div></div>'''

    def catalyst_html(c):
        cc = {"POSITIVE": "#16a34a", "NEGATIVE": "#dc2626", "NEUTRAL": "#94a3b8"}.get(c["impact"], "#666")
        return f'''<div style="margin-bottom:14px;display:flex;gap:12px;align-items:flex-start">
<div style="width:8px;height:8px;border-radius:50%;background:{cc};margin-top:7px;flex-shrink:0"></div>
<div><div style="display:flex;align-items:baseline;gap:8px"><strong style="font-size:14px">{c["name"]}</strong>
<span style="font-family:'SF Mono',Consolas,monospace;font-size:11px;color:#94a3b8">{c["expectedDate"]}</span></div>
<div style="color:#64748b;font-size:13px;margin-top:2px">{c["description"]}</div></div></div>'''

    # Scoring radar SVG
    scoring = a.get("detailedScoring", {})
    labels = ["Croissance", "Rentabilité", "Momentum", "Risque", "Qualité"]
    keys = ["growthScore", "profitabilityScore", "momentumScore", "riskScore", "qualityScore"]
    values = [scoring.get(k, 50) for k in keys]
    cx, cy, r = 120, 120, 90

    def polar(angle_deg, radius):
        rad = math.radians(angle_deg - 90)
        return cx + radius * math.cos(rad), cy + radius * math.sin(rad)

    angles = [i * 72 for i in range(5)]
    grid_svg = ""
    for level in [0.25, 0.5, 0.75, 1.0]:
        pts = " ".join(f"{polar(a, r*level)[0]},{polar(a, r*level)[1]}" for a in angles)
        grid_svg += f'<polygon points="{pts}" fill="none" stroke="#e2e8f0" stroke-width="1"/>'
    for a_deg in angles:
        x, y = polar(a_deg, r)
        grid_svg += f'<line x1="{cx}" y1="{cy}" x2="{x}" y2="{y}" stroke="#e2e8f0" stroke-width="1"/>'
    data_pts = " ".join(f"{polar(angles[i], r*values[i]/100)[0]},{polar(angles[i], r*values[i]/100)[1]}" for i in range(5))
    grid_svg += f'<polygon points="{data_pts}" fill="#3b82f620" stroke="#3b82f6" stroke-width="2"/>'
    for i in range(5):
        dx, dy = polar(angles[i], r * values[i] / 100)
        lx, ly = polar(angles[i], r + 20)
        anchor = "middle"
        if angles[i] < 180 and angles[i] > 0: anchor = "start"
        if angles[i] > 180: anchor = "end"
        grid_svg += f'<circle cx="{dx}" cy="{dy}" r="3" fill="#3b82f6"/>'
        grid_svg += f'<text x="{lx}" y="{ly}" text-anchor="{anchor}" font-size="11" fill="#64748b" font-weight="500">{labels[i]}</text>'
        grid_svg += f'<text x="{lx}" y="{ly+14}" text-anchor="{anchor}" font-size="12" fill="#1e293b" font-weight="700" font-family="SF Mono,Consolas,monospace">{values[i]}</text>'

    radar_svg = f'<svg viewBox="0 0 240 240" width="240" height="240" style="display:block;margin:0 auto">{grid_svg}</svg>'

    score_bars = ""
    for i, label in enumerate(labels):
        v = values[i]
        bar_color = "#22c55e" if v >= 70 else "#f59e0b" if v >= 40 else "#ef4444"
        score_bars += f'''<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
<div style="width:90px;font-size:12px;color:#64748b;font-weight:500">{label}</div>
<div style="flex:1;height:8px;background:#f1f5f9;border-radius:4px;overflow:hidden"><div style="height:100%;width:{v}%;background:{bar_color};border-radius:4px"></div></div>
<div style="width:30px;text-align:right;font-family:'SF Mono',Consolas,monospace;font-size:13px;font-weight:600;color:#1e293b">{v}</div></div>'''

    fm = a["financialMetrics"]
    metrics = metric_row("Chiffre d'affaires", fm["revenue"]) + metric_row("BPA (EPS)", fm["eps"]) + metric_row("Marge brute", fm["grossMargin"]) + metric_row("Marge opérationnelle", fm["operatingMargin"]) + metric_row("Dette / Fonds propres", fm["debtToEquity"]) + metric_row("Free Cash Flow", fm["freeCashFlow"])
    bull_factors = ''.join(factor_html(f, "#16a34a") for f in a["bullCase"]["factors"])
    bear_factors = ''.join(factor_html(f, "#dc2626") for f in a["bearCase"]["factors"])
    catalysts_html = ''.join(catalyst_html(c) for c in a["catalysts"])

    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>Meridian | {company} ({ticker}) — {quarter}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:860px;margin:0 auto;padding:40px 32px;color:#1e293b;line-height:1.6;background:#fff}}
h2{{font-size:16px;font-weight:700;margin-top:36px;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #e2e8f0;letter-spacing:-0.01em}}
table{{width:100%;border-collapse:collapse;margin:12px 0}}
th{{text-align:left;padding:10px 16px;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#94a3b8;border-bottom:2px solid #e2e8f0;font-weight:600}}
p{{margin-bottom:12px}}
@media print{{body{{margin:20px;padding:20px}}@page{{margin:1.5cm}}}}
</style></head>
<body>
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:32px;padding-bottom:24px;border-bottom:1px solid #e2e8f0">
<div>
<div style="font-size:10px;font-weight:700;letter-spacing:0.1em;color:#3b82f6;margin-bottom:6px">MERIDIAN INVESTMENT ANALYSIS</div>
<h1 style="font-size:28px;font-weight:800;letter-spacing:-0.02em;margin-bottom:4px">{company}</h1>
<div style="display:flex;gap:12px;align-items:baseline">
<span style="font-family:'SF Mono',Consolas,monospace;font-size:16px;font-weight:600;color:#3b82f6">{ticker}</span>
<span style="color:#94a3b8;font-size:13px">{quarter}</span>
<span style="color:#cbd5e1;font-size:13px">|</span>
<span style="color:#94a3b8;font-size:13px">{created_at[:10] if len(created_at) > 10 else created_at}</span>
</div></div>
<div style="text-align:right">
<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;color:{rec_color};opacity:0.7;margin-bottom:4px">RECOMMANDATION</div>
<div style="font-size:36px;font-weight:800;color:{rec_color};letter-spacing:-0.02em">{a["recommendation"]}</div>
<div style="font-family:'SF Mono',Consolas,monospace;font-size:14px;color:{rec_color};font-weight:600">Confiance: {round(a["confidenceScore"]*100)}%</div>
</div></div>

<div style="background:{rec_bg};border:1px solid {rec_color}30;border-radius:10px;padding:20px 24px;margin-bottom:8px">
<div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;color:{rec_color};margin-bottom:8px">These d'investissement</div>
<p style="font-size:14px;line-height:1.8;color:#334155;margin:0">{a["thesisSummary"]}</p>
</div>

<h2>Scoring detaille</h2>
<div style="display:flex;gap:32px;align-items:center;margin-bottom:8px">
<div>{radar_svg}</div>
<div style="flex:1">{score_bars}</div>
</div>

<h2>Metriques financieres</h2>
<table><thead><tr><th>Metrique</th><th style="text-align:right">Valeur</th><th style="text-align:right">Var. YoY</th><th style="text-align:right">Tendance</th></tr></thead><tbody>{metrics}</tbody></table>

<h2 style="color:#16a34a">Bull Case</h2>
<p style="color:#475569;line-height:1.8;margin-bottom:16px">{a["bullCase"]["thesis"]}</p>{bull_factors}

<h2 style="color:#dc2626">Bear Case</h2>
<p style="color:#475569;line-height:1.8;margin-bottom:16px">{a["bearCase"]["thesis"]}</p>{bear_factors}

<h2>Catalyseurs (12 mois)</h2>{catalysts_html}

<div style="margin-top:48px;padding-top:20px;border-top:2px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center">
<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;color:#3b82f6">MERIDIAN AI</div>
<div style="font-size:11px;color:#94a3b8">Ce document ne constitue pas un conseil en investissement.</div>
</div>
</body></html>"""
