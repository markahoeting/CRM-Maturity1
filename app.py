import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file, url_for
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "assessments.db"
LOGO_PATH = BASE_DIR / "static" / "img" / "info-tech-logo.png"
ADMIN_CODE = os.getenv("ADMIN_CODE", "infotech-admin")
APP_SECRET = os.getenv("APP_SECRET", "crm-maturity-secret")

BRAND = {
    "name": "Info-Tech Research Group",
    "logo_path": "/static/img/info-tech-logo.png",
    "logo_source": "https://www.genspark.ai/api/files/s/cfPwk2vJ",
    "primary": "#2676B7",
    "accent": "#74A5CD",
    "navy": "#02122B",
    "paper": "#F4F8FC",
}

DOMAINS = [
    {
        "id": "strategy",
        "step": 2,
        "title": "Institutional CRM Strategy & Vision",
        "weight": 8,
        "focus": "Enterprise CRM strategy, executive sponsorship, roadmap discipline, and defined business outcomes.",
        "weak_signal": "CRM is viewed primarily as a departmental tool rather than an institutional capability.",
        "strong_signal": "CRM is positioned as a strategic enterprise platform supporting the constituent lifecycle.",
        "questions": [
            "CRM strategy is aligned to institutional goals across enrollment, retention, advancement, and engagement.",
            "Executive sponsorship extends beyond one department or business unit.",
            "A multi-year CRM roadmap exists with prioritized investments and sequencing.",
            "Business outcomes for CRM are clearly defined and tracked."
        ],
        "recommendations": {
            "quick": "Define an enterprise CRM vision and align it to enrollment, retention, advancement, and experience objectives.",
            "mid": "Create a multi-year roadmap with governance checkpoints, funding logic, and measurable outcomes.",
            "long": "Institutionalize CRM as part of transformation planning and lifecycle-based engagement design."
        },
        "consultant_actions": [
            "Run a leadership alignment workshop to define target-state CRM outcomes.",
            "Draft a north-star architecture and roadmap narrative for executive approval.",
            "Tie roadmap milestones to operating model and KPI ownership."
        ]
    },
    {
        "id": "governance",
        "step": 2,
        "title": "Governance & Organizational Model",
        "weight": 7,
        "focus": "Decision rights, cross-functional governance, prioritization, stewardship, and change management.",
        "weak_signal": "Independent departmental systems and political friction drive CRM decisions.",
        "strong_signal": "A formal shared operating model governs CRM standards, priorities, and ownership.",
        "questions": [
            "A formal CRM governance body exists with clear membership and decision rights.",
            "Enhancement requests and priorities are managed through a transparent process.",
            "Data stewardship, platform ownership, and business accountability are clearly assigned.",
            "Change management is embedded into CRM initiatives."
        ],
        "recommendations": {
            "quick": "Stand up an enterprise CRM governance council with clear intake, escalation, and decision processes.",
            "mid": "Clarify platform ownership, stewardship roles, and vendor governance across institutional units.",
            "long": "Evolve to a shared operating model that balances enterprise standards and campus autonomy."
        },
        "consultant_actions": [
            "Map current decision rights and identify governance collisions across units.",
            "Design a governance charter, intake model, and prioritization rubric.",
            "Establish change sponsorship and cross-functional communication routines."
        ]
    },
    {
        "id": "security",
        "step": 2,
        "title": "Security, Privacy & Compliance",
        "weight": 7,
        "focus": "FERPA, role-based access, consent, retention, third-party risk, and AI governance.",
        "weak_signal": "Sensitive data and communication controls are inconsistently managed across platforms.",
        "strong_signal": "Permissions, consent, and AI-enabled use cases are governed through active controls and policy.",
        "questions": [
            "Role-based access is appropriate for the data handled in CRM workflows.",
            "FERPA, consent, and communication compliance requirements are operationalized.",
            "Retention, identity governance, and third-party risk practices are defined and followed.",
            "AI-enabled CRM use cases are governed through policy and review."
        ],
        "recommendations": {
            "quick": "Review role-based access, consent capture, and sensitive data handling within CRM-connected processes.",
            "mid": "Standardize retention and third-party review practices across CRM-connected systems.",
            "long": "Expand governance into AI oversight, identity governance, and continuous compliance monitoring."
        },
        "consultant_actions": [
            "Perform a permission and data-handling control review across priority workflows.",
            "Define a CRM privacy and AI governance checklist for new use cases.",
            "Add compliance sign-off points to roadmap and release processes."
        ]
    },
    {
        "id": "lifecycle",
        "step": 3,
        "title": "Student / Constituent Lifecycle Management",
        "weight": 15,
        "focus": "Journey design, personalization, event-triggered outreach, intervention workflows, and coordinated engagement.",
        "weak_signal": "Lifecycle communications are fragmented, generic, and managed independently by departments.",
        "strong_signal": "Constituent journeys are orchestrated across recruitment, success, advancement, and partnerships.",
        "questions": [
            "Key constituent journeys are mapped across the student and alumni lifecycle.",
            "Communications are personalized based on stage, segment, or behavior.",
            "Interventions such as advising or outreach are automated where appropriate.",
            "Engagement across departments is coordinated instead of duplicated."
        ],
        "recommendations": {
            "quick": "Map high-value journeys for prospect, applicant, student, at-risk, alumni, donor, and partner populations.",
            "mid": "Implement coordinated event-triggered outreach and intervention workflows across departments.",
            "long": "Use predictive and next-best-action capabilities to orchestrate personalized lifecycle engagement."
        },
        "consultant_actions": [
            "Facilitate journey mapping sessions for top-priority lifecycle segments.",
            "Design future-state intervention triggers and service handoffs.",
            "Sequence omnichannel engagement use cases by value and readiness."
        ]
    },
    {
        "id": "process",
        "step": 3,
        "title": "Process Standardization & Automation",
        "weight": 10,
        "focus": "Documented workflows, repeatability, communication automation, case management, and SLA discipline.",
        "weak_signal": "CRM-dependent processes vary widely across teams and rely on manual handoffs.",
        "strong_signal": "Repeatable workflows and intelligent automation reduce effort and improve service quality.",
        "questions": [
            "High-value CRM-related processes are documented and repeatable.",
            "Manual handoffs are reduced through workflow automation or operating standards.",
            "Communication automation is used consistently to support lifecycle engagement.",
            "Case, approval, or service workflows are monitored for timeliness and quality."
        ],
        "recommendations": {
            "quick": "Document the highest-volume workflows and identify manual bottlenecks, handoffs, and approval loops.",
            "mid": "Standardize core processes and automate communication, routing, and case management where practical.",
            "long": "Adopt adaptive journeys and intelligent automation informed by events and risk signals."
        },
        "consultant_actions": [
            "Baseline cycle times, handoffs, and rework across high-volume workflows.",
            "Prioritize automations using value, complexity, and readiness scoring.",
            "Define service standards and operational dashboards for automation performance."
        ]
    },
    {
        "id": "adoption",
        "step": 3,
        "title": "User Adoption & Culture",
        "weight": 10,
        "focus": "Training, trust, CRM literacy, leadership engagement, and reduction of shadow systems.",
        "weak_signal": "Users avoid CRM, rely on spreadsheets, and see standardization as burden.",
        "strong_signal": "CRM is embedded into daily operations and leaders actively use CRM-driven insights.",
        "questions": [
            "Users receive role-based training and ongoing support for CRM use.",
            "Users trust the data and see CRM as helpful rather than administrative burden.",
            "Leaders actively use CRM insight in decision-making and management routines.",
            "Shadow systems are being reduced or replaced by standard CRM workflows."
        ],
        "recommendations": {
            "quick": "Assess training gaps and identify where shadow systems are replacing intended CRM workflows.",
            "mid": "Establish adoption metrics, role-based learning paths, and leadership expectations for CRM usage.",
            "long": "Build a data-driven culture where CRM insight informs planning, coaching, and service delivery."
        },
        "consultant_actions": [
            "Measure adoption by role and workflow, not just license count.",
            "Create role-specific enablement paths and leader scorecards.",
            "Introduce usage governance for shadow spreadsheets and off-platform processes."
        ]
    },
    {
        "id": "data",
        "step": 4,
        "title": "Data Architecture & Data Quality",
        "weight": 15,
        "focus": "Trusted records, identity resolution, data standards, integration architecture, and profile unification.",
        "weak_signal": "Manual imports, duplicate records, and spreadsheet reconciliation are common.",
        "strong_signal": "Unified profiles and trusted enterprise data support real-time constituent engagement.",
        "questions": [
            "A trusted system of record and shared data definitions exist for CRM-relevant entities.",
            "Identity resolution and duplicate management support a unified constituent profile.",
            "Data quality is monitored and trusted by users and leaders.",
            "CRM integrations with SIS, ERP, advancement, and related systems are reliable and standardized."
        ],
        "recommendations": {
            "quick": "Document the system of record, key data definitions, and highest-risk quality issues.",
            "mid": "Establish identity resolution, duplicate management, and shared data standards across systems.",
            "long": "Implement a trusted enterprise data model that enables unified constituent profiles and near real-time exchange."
        },
        "consultant_actions": [
            "Create a constituent data model and profile unification roadmap.",
            "Prioritize quality issues by business impact and process dependency.",
            "Define integration patterns and stewardship accountability for critical data objects."
        ]
    },
    {
        "id": "technology",
        "step": 4,
        "title": "Technology & Platform Ecosystem",
        "weight": 10,
        "focus": "Platform rationalization, API strategy, integration maturity, workflow tooling, and self-service capability.",
        "weak_signal": "Disconnected platforms and brittle integrations create significant manual effort.",
        "strong_signal": "The ecosystem is rationalized, API-enabled, and designed for automation and self-service.",
        "questions": [
            "CRM platforms are intentionally selected and rationalized across the institution.",
            "CRM is well integrated with SIS, ERP, LMS, advancement, and marketing systems.",
            "Workflow automation, mobile capabilities, and self-service are actively leveraged.",
            "The technical architecture supports scalable integrations instead of manual workarounds."
        ],
        "recommendations": {
            "quick": "Inventory CRM-adjacent platforms and identify the biggest duplication and integration pain points.",
            "mid": "Rationalize overlapping tools and establish an API-first integration strategy.",
            "long": "Build an event-driven architecture or integration layer that supports low-code orchestration and self-service."
        },
        "consultant_actions": [
            "Map platform sprawl and identify retire, retain, replace candidates.",
            "Define target integration patterns and reusable service layers.",
            "Sequence modernization by constituent impact and technical debt reduction."
        ]
    },
    {
        "id": "analytics",
        "step": 4,
        "title": "Analytics, Reporting & AI Capability",
        "weight": 10,
        "focus": "Dashboards, predictive analytics, segmentation, responsible AI, and prescriptive decision support.",
        "weak_signal": "Reporting is mostly retrospective, fragmented, or difficult to access.",
        "strong_signal": "Analytics and AI inform interventions, segmentation, engagement, and institutional intelligence.",
        "questions": [
            "Leaders can access timely KPI dashboards that measure CRM-related outcomes and engagement effectiveness.",
            "Analytics extend beyond descriptive reporting into segmentation or predictive insight.",
            "AI use cases such as copilots, chatbots, or next-best-action are being explored or used responsibly.",
            "Interventions and communications are informed by data rather than intuition alone."
        ],
        "recommendations": {
            "quick": "Define the core CRM KPI set and improve dashboard access for leaders and frontline teams.",
            "mid": "Expand from descriptive reporting into predictive models for yield, retention, and engagement.",
            "long": "Operationalize responsible AI, prescriptive analytics, and AI-assisted engagement across the lifecycle."
        },
        "consultant_actions": [
            "Align KPI definitions to executive and frontline decision points.",
            "Prioritize analytics use cases by feasibility, value, and data readiness.",
            "Establish an AI governance and use-case pipeline for CRM-adjacent opportunities."
        ]
    },
    {
        "id": "outcomes",
        "step": 4,
        "title": "Outcomes & Value Realization",
        "weight": 8,
        "focus": "KPI alignment, ROI, enrollment and retention impact, service improvement, and operational efficiency.",
        "weak_signal": "Projects are completed, but business value is not consistently measured or communicated.",
        "strong_signal": "CRM investments are tied to measurable institutional outcomes and continuous improvement decisions.",
        "questions": [
            "CRM initiatives are linked to measurable institutional KPIs and success metrics.",
            "The institution tracks value realization such as yield, retention, efficiency, or campaign outcomes.",
            "CRM performance results are reviewed regularly to inform future decisions.",
            "Leaders distinguish between technology deployment and true institutional impact."
        ],
        "recommendations": {
            "quick": "Define outcome measures for enrollment, student success, advancement, and operations.",
            "mid": "Track KPI movement and operational savings against CRM initiatives and workflow changes.",
            "long": "Use value realization reviews to refine roadmap priorities, funding, and capability scaling decisions."
        },
        "consultant_actions": [
            "Create a value realization framework tied to roadmap initiatives.",
            "Define baseline metrics and review cadences for benefit tracking.",
            "Build executive storytelling around CRM impact, not just delivery milestones."
        ]
    },
]

STEP_TITLES = {
    1: "Institutional Context",
    2: "Strategy, Governance & Risk",
    3: "Lifecycle, Process & Adoption",
    4: "Data, Technology & Intelligence",
    5: "Review, Submit & Report",
}

app = Flask(__name__)
app.secret_key = APP_SECRET


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            institution_name TEXT,
            institution_type TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            overall_score REAL DEFAULT 0,
            overall_label TEXT DEFAULT '',
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


@app.before_request
def ensure_db():
    init_db()


def normalize_payload(data):
    payload = data or {}
    context = payload.get("context", {}) or {}
    responses = payload.get("responses", {}) or {}
    normalized = {"context": context, "responses": {}}
    for domain in DOMAINS:
        raw = responses.get(domain["id"], {}) or {}
        if isinstance(raw, list):
            scores = [int(x) if x else None for x in raw]
            evidence = ""
        else:
            scores = raw.get("scores", [])
            evidence = (raw.get("evidence") or "").strip()
        fixed_scores = []
        for idx in range(len(domain["questions"])):
            value = scores[idx] if idx < len(scores) else None
            fixed_scores.append(int(value) if value in [1, 2, 3, 4, 5] else None)
        normalized["responses"][domain["id"]] = {"scores": fixed_scores, "evidence": evidence}
    return normalized


def maturity_label(score):
    if score < 1.8:
        return "Ad Hoc"
    if score < 2.6:
        return "Emerging"
    if score < 3.4:
        return "Defined"
    if score < 4.4:
        return "Integrated"
    return "Optimized / Intelligent"


def maturity_narrative(score):
    label = maturity_label(score)
    mapping = {
        "Ad Hoc": "Capabilities are fragmented, reactive, and heavily dependent on local workarounds.",
        "Emerging": "The institution has early structures in place, but governance and repeatability remain inconsistent.",
        "Defined": "Core practices are documented and partially standardized, though end-to-end integration is still uneven.",
        "Integrated": "Capabilities are coordinated across functions with trusted data, repeatable workflows, and clear accountability.",
        "Optimized / Intelligent": "CRM operates as a strategic enterprise capability with continuous improvement, predictive insight, and increasingly intelligent orchestration.",
    }
    return label, mapping[label]


def recommendation_phase(avg_score):
    if avg_score < 2.6:
        return "quick"
    if avg_score < 3.8:
        return "mid"
    return "long"


def compute_results(payload):
    results = []
    total_answered = 0
    total_questions = 0
    weighted_sum = 0.0

    for domain in DOMAINS:
        domain_payload = payload.get("responses", {}).get(domain["id"], {"scores": [], "evidence": ""})
        scores = domain_payload.get("scores", [])
        evidence = domain_payload.get("evidence", "").strip()
        answered_scores = [int(score) for score in scores if score in [1, 2, 3, 4, 5]]
        total_answered += len(answered_scores)
        total_questions += len(domain["questions"])
        average = round(sum(answered_scores) / len(answered_scores), 2) if answered_scores else 0.0
        weighted_sum += average * (domain["weight"] / 100)
        results.append(
            {
                "id": domain["id"],
                "title": domain["title"],
                "weight": domain["weight"],
                "step": domain["step"],
                "average": average,
                "answered": len(answered_scores),
                "total_questions": len(domain["questions"]),
                "evidence": evidence,
                "weak_signal": domain["weak_signal"],
                "strong_signal": domain["strong_signal"],
                "focus": domain["focus"],
                "phase": recommendation_phase(average if average else 1),
                "recommendations": domain["recommendations"],
                "consultant_actions": domain["consultant_actions"],
            }
        )

    overall = round(weighted_sum, 2)
    label, narrative = maturity_narrative(overall if overall else 1)
    completion_pct = round((total_answered / total_questions) * 100, 1) if total_questions else 0.0

    low_domains = sorted(results, key=lambda item: item["average"] if item["average"] else 0)[:4]
    high_domains = sorted(results, key=lambda item: item["average"], reverse=True)[:3]

    consultant_recommendations = []
    for item in low_domains:
        consultant_recommendations.append(
            {
                "domain": item["title"],
                "score": item["average"],
                "priority": "High" if item["average"] < 2.6 else "Medium",
                "engagement_play": item["recommendations"][item["phase"]],
                "consultant_actions": item["consultant_actions"],
            }
        )

    context = payload.get("context", {})
    institution_name = context.get("institutionName") or "This institution"
    executive_summary = (
        f"{institution_name} currently scores {overall:.2f} out of 5.00, which places it in the {label} maturity band. "
        f"The assessment suggests the institution's CRM environment is best understood as an institutional coordination challenge rather than simply a platform question. "
        f"Priority focus areas should center on low-scoring domains, especially where fragmented governance, lifecycle orchestration, data trust, or process inconsistency are limiting measurable outcomes."
    )

    return {
        "overall_score": overall,
        "overall_label": label,
        "overall_narrative": narrative,
        "completion_pct": completion_pct,
        "domain_results": results,
        "low_domains": low_domains,
        "high_domains": high_domains,
        "consultant_recommendations": consultant_recommendations,
        "executive_summary": executive_summary,
    }


def score_fill(score):
    if score < 2.0:
        return colors.HexColor("#C64756")
    if score < 2.6:
        return colors.HexColor("#E58A2B")
    if score < 3.4:
        return colors.HexColor("#D7A91A")
    if score < 4.4:
        return colors.HexColor(BRAND["accent"])
    return colors.HexColor(BRAND["primary"])


def chart_domain_label(domain):
    mapping = {
        "strategy": "Strategy & Vision",
        "governance": "Governance",
        "security": "Security & Compliance",
        "lifecycle": "Lifecycle Management",
        "process": "Process Automation",
        "adoption": "Adoption & Culture",
        "data": "Data Quality",
        "technology": "Platform Ecosystem",
        "analytics": "Analytics & AI",
        "outcomes": "Outcomes & ROI",
    }
    return mapping.get(domain["id"], domain["title"])


def truncate_text(text, limit=86):
    text = text or ""
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def report_chrome(canvas, doc):
    canvas.saveState()
    page_width, page_height = letter
    canvas.setFillColor(colors.HexColor(BRAND["navy"]))
    canvas.rect(0, page_height - 20, page_width, 20, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor(BRAND["accent"]))
    canvas.setLineWidth(1)
    canvas.line(doc.leftMargin, page_height - 30, page_width - doc.rightMargin, page_height - 30)
    canvas.setFillColor(colors.HexColor(BRAND["navy"]))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(doc.leftMargin, 18, BRAND["name"])
    canvas.drawRightString(page_width - doc.rightMargin, 18, f"Page {doc.page}")
    canvas.restoreState()


def build_metric_cards(results, styles):
    strongest = max(results["domain_results"], key=lambda item: item["average"])
    top_gap = min(results["domain_results"], key=lambda item: item["average"])
    cards = [
        Paragraph(f"<b>Overall Score</b><br/><font size='18'>{results['overall_score']:.2f} / 5.00</font><br/><font size='7'>Weighted enterprise maturity</font>", styles["CardMetric"]),
        Paragraph(f"<b>Maturity Band</b><br/><font size='16'>{results['overall_label']}</font><br/><font size='7'>{results['overall_narrative']}</font>", styles["CardMetric"]),
        Paragraph(f"<b>Strongest Domain</b><br/><font size='14'>{chart_domain_label(strongest)}</font><br/><font size='7'>Score {strongest['average']:.2f}</font>", styles["CardMetric"]),
        Paragraph(f"<b>Priority Gap</b><br/><font size='14'>{chart_domain_label(top_gap)}</font><br/><font size='7'>Score {top_gap['average']:.2f}</font>", styles["CardMetric"]),
    ]
    table = Table([cards], colWidths=[1.47 * inch, 1.72 * inch, 1.47 * inch, 1.47 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(BRAND["primary"])),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor(BRAND["navy"])),
                ("BACKGROUND", (2, 0), (2, 0), colors.HexColor(BRAND["accent"])),
                ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#C64756")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def build_maturity_spectrum(score, label):
    drawing = Drawing(500, 94)
    x0, y0, total_width, band_height = 18, 30, 450, 20
    segment_width = total_width / 5
    segment_colors = [
        colors.HexColor("#C64756"),
        colors.HexColor("#E58A2B"),
        colors.HexColor("#D7A91A"),
        colors.HexColor(BRAND["accent"]),
        colors.HexColor(BRAND["primary"]),
    ]
    segment_labels = ["Ad Hoc", "Emerging", "Defined", "Integrated", "Optimized"]
    for idx, (segment_label, fill) in enumerate(zip(segment_labels, segment_colors)):
        x = x0 + (idx * segment_width)
        drawing.add(Rect(x, y0, segment_width - 3, band_height, fillColor=fill, strokeColor=fill))
        drawing.add(String(x + (segment_width / 2) - 1, y0 - 12, segment_label, fontName="Helvetica", fontSize=7, fillColor=colors.HexColor(BRAND["navy"]), textAnchor="middle"))
        drawing.add(String(x + (segment_width / 2) - 1, y0 + 28, str(idx + 1), fontName="Helvetica-Bold", fontSize=8, fillColor=colors.HexColor(BRAND["navy"]), textAnchor="middle"))
    marker_x = x0 + (max(score, 0) / 5.0) * total_width
    drawing.add(Line(marker_x, y0 - 4, marker_x, y0 + 46, strokeColor=colors.HexColor(BRAND["navy"]), strokeWidth=1.3))
    badge_x = min(max(marker_x - 32, x0), x0 + total_width - 64)
    drawing.add(Rect(badge_x, y0 + 50, 64, 18, fillColor=colors.HexColor(BRAND["navy"]), strokeColor=colors.HexColor(BRAND["navy"])))
    drawing.add(String(badge_x + 32, y0 + 56, f"{score:.2f}", fontName="Helvetica-Bold", fontSize=9, fillColor=colors.white, textAnchor="middle"))
    drawing.add(String(x0, 84, "Overall maturity placement", fontName="Helvetica-Bold", fontSize=10, fillColor=colors.HexColor(BRAND["navy"])))
    drawing.add(String(x0, 74, f"Current band: {label}", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor(BRAND["primary"])))
    return drawing


def build_domain_score_chart(domain_results):
    ranked = sorted(domain_results, key=lambda item: item["average"], reverse=True)
    drawing = Drawing(355, 250)
    drawing.add(String(0, 235, "Domain score profile", fontName="Helvetica-Bold", fontSize=10, fillColor=colors.HexColor(BRAND["navy"])))
    drawing.add(String(0, 223, "Higher scores indicate more integrated and enterprise-scale capability.", fontName="Helvetica", fontSize=7.5, fillColor=colors.HexColor("#5D738A")))
    left, top_y, rail_width = 116, 196, 170
    for idx, item in enumerate(ranked):
        y = top_y - (idx * 17)
        drawing.add(String(0, y, chart_domain_label(item), fontName="Helvetica", fontSize=7.4, fillColor=colors.HexColor(BRAND["navy"])))
        drawing.add(Rect(left, y - 4, rail_width, 8, fillColor=colors.HexColor("#EAF1F7"), strokeColor=colors.HexColor("#EAF1F7")))
        drawing.add(Rect(left, y - 4, rail_width * (item["average"] / 5.0), 8, fillColor=score_fill(item["average"]), strokeColor=score_fill(item["average"])))
        drawing.add(String(left + rail_width + 8, y - 0.5, f"{item['average']:.2f}", fontName="Helvetica-Bold", fontSize=7.5, fillColor=colors.HexColor(BRAND["navy"])))
    for tick in range(1, 6):
        x = left + (rail_width * tick / 5.0)
        drawing.add(Line(x, 20, x, 210, strokeColor=colors.HexColor("#DCE7F1"), strokeWidth=0.35))
        drawing.add(String(x, 8, str(tick), fontName="Helvetica", fontSize=7, fillColor=colors.HexColor("#70869B"), textAnchor="middle"))
    return drawing


def build_distribution_chart(domain_results):
    drawing = Drawing(190, 250)
    drawing.add(String(0, 235, "Maturity distribution", fontName="Helvetica-Bold", fontSize=10, fillColor=colors.HexColor(BRAND["navy"])))
    counts = {"Ad Hoc": 0, "Emerging": 0, "Defined": 0, "Integrated": 0, "Optimized / Intelligent": 0}
    for item in domain_results:
        counts[maturity_label(item["average"] if item["average"] else 1)] += 1
    if not any(counts.values()):
        counts["Ad Hoc"] = 1
    pie = Pie()
    pie.x = 8
    pie.y = 98
    pie.width = 100
    pie.height = 100
    pie.data = list(counts.values())
    pie.labels = [str(value) if value else "" for value in counts.values()]
    pie.slices.strokeWidth = 0.5
    pie.slices[0].fillColor = colors.HexColor("#C64756")
    pie.slices[1].fillColor = colors.HexColor("#E58A2B")
    pie.slices[2].fillColor = colors.HexColor("#D7A91A")
    pie.slices[3].fillColor = colors.HexColor(BRAND["accent"])
    pie.slices[4].fillColor = colors.HexColor(BRAND["primary"])
    drawing.add(pie)
    legend_y = 82
    legend_colors = [
        colors.HexColor("#C64756"),
        colors.HexColor("#E58A2B"),
        colors.HexColor("#D7A91A"),
        colors.HexColor(BRAND["accent"]),
        colors.HexColor(BRAND["primary"]),
    ]
    for idx, ((band, count), fill) in enumerate(zip(counts.items(), legend_colors)):
        y = legend_y - (idx * 14)
        drawing.add(Rect(0, y, 8, 8, fillColor=fill, strokeColor=fill))
        drawing.add(String(13, y + 1, f"{band} ({count})", fontName="Helvetica", fontSize=6.8, fillColor=colors.HexColor(BRAND["navy"])))
    return drawing


def build_opportunity_chart(low_domains):
    ranked = sorted(low_domains, key=lambda item: item["average"])
    drawing = Drawing(500, 128)
    drawing.add(String(0, 116, "Improvement headroom across lowest-scoring domains", fontName="Helvetica-Bold", fontSize=10, fillColor=colors.HexColor(BRAND["navy"])))
    left, top_y, rail_width = 152, 84, 260
    for idx, item in enumerate(ranked):
        y = top_y - (idx * 22)
        gap = 5.0 - item["average"]
        fill = colors.HexColor("#C64756") if item["average"] < 2.6 else colors.HexColor("#E58A2B")
        drawing.add(String(0, y, chart_domain_label(item), fontName="Helvetica", fontSize=7.6, fillColor=colors.HexColor(BRAND["navy"])))
        drawing.add(Rect(left, y - 5, rail_width, 10, fillColor=colors.HexColor("#EEF4F9"), strokeColor=colors.HexColor("#EEF4F9")))
        drawing.add(Rect(left, y - 5, rail_width * (gap / 5.0), 10, fillColor=fill, strokeColor=fill))
        drawing.add(String(left + rail_width + 8, y - 1, f"Headroom {gap:.2f}", fontName="Helvetica-Bold", fontSize=7.2, fillColor=colors.HexColor(BRAND["navy"])))
    return drawing


def heatmap_fill(score):
    if score < 2.6:
        return colors.HexColor("#F9D6DB")
    if score < 3.8:
        return colors.HexColor("#FFF0BF")
    return colors.HexColor("#DDF3E7")


def heatmap_text_color(score):
    if score < 2.6:
        return colors.HexColor("#A32035")
    if score < 3.8:
        return colors.HexColor("#8C6200")
    return colors.HexColor("#1F6C49")


def build_heatmap_table(domain_results):
    rows = [["Domain", "Score", "Maturity Signal", "Budget", "Effort", "Recommended Action"]]
    ranked = sorted(domain_results, key=lambda item: item["average"])
    for item in ranked:
        maturity_signal = "Needs immediate stabilization" if item["average"] < 2.6 else "Build toward integration" if item["average"] < 3.8 else "Scale and optimize"
        phase_name = "quick"
        if item["phase"] == "mid":
            phase_name = "twelve"
        elif item["phase"] == "long":
            phase_name = "twenty_four"
        budget, effort = budget_effort_for_item(item, phase_name)
        rows.append([
            chart_domain_label(item),
            f"{item['average']:.2f}",
            maturity_signal,
            budget,
            effort,
            truncate_text(item["recommendations"][item["phase"]], 56),
        ])
    table = Table(rows, colWidths=[1.45 * inch, 0.55 * inch, 1.15 * inch, 0.72 * inch, 0.82 * inch, 2.06 * inch])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND["navy"])),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.1),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8D8E8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for idx, item in enumerate(ranked, start=1):
        fill = heatmap_fill(item["average"])
        txt = heatmap_text_color(item["average"])
        style_cmds.extend([
            ("BACKGROUND", (0, idx), (-1, idx), fill),
            ("TEXTCOLOR", (1, idx), (2, idx), txt),
            ("FONTNAME", (1, idx), (2, idx), "Helvetica-Bold"),
        ])
    table.setStyle(TableStyle(style_cmds))
    return table


def build_roadmap_groups(domain_results):
    ranked = sorted(domain_results, key=lambda item: item["average"])
    quick = [item for item in ranked if item["average"] < 2.6]
    twelve = [item for item in ranked if 2.6 <= item["average"] < 3.8]
    twenty_four = [item for item in ranked if item["average"] >= 3.8]

    if not quick:
        quick = ranked[:3]
    if not twelve:
        twelve = ranked[len(quick):len(quick) + 3] or ranked[:3]
    if not twenty_four:
        twenty_four = list(reversed(sorted(domain_results, key=lambda item: item["average"])))[:3]

    return {
        "quick": quick[:4],
        "twelve": twelve[:4],
        "twenty_four": twenty_four[:4],
    }


def roadmap_intro(phase_name):
    mapping = {
        "quick": "Near-term actions should reduce operational friction, establish trust, and address the most visible CRM coordination failures.",
        "twelve": "The 12-month horizon should shift the institution from isolated fixes to cross-functional capability building and measurable governance discipline.",
        "twenty_four": "The 24-month horizon should focus on scaling integrated capabilities, analytics maturity, and long-term value realization across the enterprise lifecycle.",
    }
    return mapping[phase_name]


def budget_effort_for_item(item, phase_name):
    baseline = {
        "quick": ("Low–Medium", "Medium"),
        "twelve": ("Medium", "Medium–High"),
        "twenty_four": ("High", "High"),
    }
    budget, effort = baseline[phase_name]

    if item["id"] in {"data", "technology", "analytics", "lifecycle"}:
        if phase_name == "quick":
            budget, effort = ("Medium", "Medium–High")
        elif phase_name == "twelve":
            budget, effort = ("Medium–High", "High")
        else:
            budget, effort = ("High", "High")
    elif item["id"] in {"governance", "strategy", "adoption", "outcomes", "security"}:
        if phase_name == "quick":
            budget, effort = ("Low", "Medium")
        elif phase_name == "twelve":
            budget, effort = ("Medium", "Medium")
        else:
            budget, effort = ("Medium", "Medium–High")
    elif item["id"] == "process":
        if phase_name == "quick":
            budget, effort = ("Low–Medium", "Medium")
        elif phase_name == "twelve":
            budget, effort = ("Medium", "Medium–High")
        else:
            budget, effort = ("Medium–High", "High")

    return budget, effort


def build_budget_effort_legend(styles):
    legend_rows = [
        ["Indicator", "Meaning"],
        ["Low", "Operating-model, governance, training, or policy work with limited technology spend."],
        ["Low–Medium", "Targeted workflow changes, enablement, and selective configuration effort."],
        ["Medium", "Cross-functional process redesign, integrations, or moderate platform investment."],
        ["Medium–High", "Significant design, integration, data remediation, or multi-team delivery effort."],
        ["High", "Enterprise-scale transformation, platform modernization, or major data/AI investment."],
    ]
    legend = Table(legend_rows, colWidths=[1.0 * inch, 5.15 * inch])
    legend.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND["primary"])),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.8),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8D8E8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FBFE")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return legend


def build_roadmap_page(title, phase_name, items, styles):
    elements = [
        Paragraph(title, styles["HeadingBlue"]),
        Paragraph(roadmap_intro(phase_name), styles["BodySmall"]),
        Paragraph("Budget and effort indicators are directional planning signals intended to support client prioritization conversations rather than replace formal business cases.", styles["BodyTiny"]),
    ]
    for item in items:
        subtitle = "Quick win" if phase_name == "quick" else "12-month move" if phase_name == "twelve" else "24-month move"
        budget, effort = budget_effort_for_item(item, phase_name)
        indicator_table = Table(
            [[
                Paragraph(f"<b>Budget indicator</b><br/>{budget}", styles["BodySmall"]),
                Paragraph(f"<b>Effort indicator</b><br/>{effort}", styles["BodySmall"]),
            ]],
            colWidths=[2.95 * inch, 2.95 * inch],
        )
        indicator_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#EEF6FC")),
                    ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F5F9FC")),
                    ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8D8E8")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8D8E8")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        block = Table(
            [[
                Paragraph(
                    f"<b>{chart_domain_label(item)}</b> · current score {item['average']:.2f}<br/>"
                    f"<font color='{BRAND['primary']}'><b>{subtitle} objective:</b></font> {truncate_text(item['weak_signal'], 140)}<br/>"
                    f"<b>Recommended initiative:</b> {truncate_text(item['recommendations']['quick' if phase_name == 'quick' else 'mid' if phase_name == 'twelve' else 'long'], 190)}<br/>"
                    f"<b>Consulting support:</b><br/>• {truncate_text(item['consultant_actions'][0], 135)}<br/>• {truncate_text(item['consultant_actions'][1], 135)}<br/>• {truncate_text(item['consultant_actions'][2], 135)}",
                    styles["BodySmall"],
                )
            ], [indicator_table]],
            colWidths=[6.15 * inch],
        )
        block.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.55, score_fill(item["average"])),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(block)
        elements.append(Spacer(1, 0.10 * inch))
    elements.append(Spacer(1, 0.04 * inch))
    elements.append(build_budget_effort_legend(styles))
    return elements


def upsert_assessment(token, payload, status="draft"):
    results = compute_results(payload)
    context = payload.get("context", {})
    now = utc_now_iso()
    conn = get_conn()
    existing = conn.execute("SELECT id, created_at FROM assessments WHERE token = ?", (token,)).fetchone()
    if existing:
        created_at = existing["created_at"]
        conn.execute(
            """
            UPDATE assessments
            SET institution_name = ?, institution_type = ?, status = ?, overall_score = ?, overall_label = ?, payload = ?, updated_at = ?
            WHERE token = ?
            """,
            (
                context.get("institutionName", ""),
                context.get("institutionType", ""),
                status,
                results["overall_score"],
                results["overall_label"],
                json.dumps(payload),
                now,
                token,
            ),
        )
    else:
        created_at = now
        conn.execute(
            """
            INSERT INTO assessments (token, institution_name, institution_type, status, overall_score, overall_label, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                token,
                context.get("institutionName", ""),
                context.get("institutionType", ""),
                status,
                results["overall_score"],
                results["overall_label"],
                json.dumps(payload),
                created_at,
                now,
            ),
        )
    conn.commit()
    conn.close()
    return results


def fetch_assessment(token):
    conn = get_conn()
    row = conn.execute("SELECT * FROM assessments WHERE token = ?", (token,)).fetchone()
    conn.close()
    return row


def build_bootstrap_payload(token=None):
    return {
        "token": token,
        "brand": BRAND,
        "step_titles": STEP_TITLES,
        "domains": DOMAINS,
    }


@app.route("/")
def index():
    return render_template("index.html", bootstrap=build_bootstrap_payload())


@app.get("/api/assessment/<token>")
def api_get_assessment(token):
    row = fetch_assessment(token)
    if not row:
        abort(404)
    payload = json.loads(row["payload"])
    results = compute_results(payload)
    return jsonify(
        {
            "token": token,
            "status": row["status"],
            "saved_at": row["updated_at"],
            "payload": payload,
            "results": results,
        }
    )


@app.post("/api/assessment/save")
def api_save_assessment():
    incoming = request.get_json(force=True, silent=True) or {}
    token = incoming.get("token") or uuid.uuid4().hex[:12]
    payload = normalize_payload(incoming)
    results = upsert_assessment(token, payload, status=incoming.get("status", "draft") or "draft")
    return jsonify({"ok": True, "token": token, "status": incoming.get("status", "draft") or "draft", "results": results, "report_url": url_for("download_report", token=token)})


@app.post("/api/assessment/<token>/submit")
def api_submit_assessment(token):
    incoming = request.get_json(force=True, silent=True) or {}
    payload = normalize_payload(incoming)
    results = upsert_assessment(token, payload, status="submitted")
    return jsonify({"ok": True, "token": token, "status": "submitted", "results": results, "report_url": url_for("download_report", token=token)})


@app.route("/report/<token>.pdf")
def download_report(token):
    row = fetch_assessment(token)
    if not row:
        abort(404)
    payload = json.loads(row["payload"])
    results = compute_results(payload)
    context = payload.get("context", {})

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.62 * inch, bottomMargin=0.55 * inch, leftMargin=0.62 * inch, rightMargin=0.62 * inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleNavy", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, textColor=colors.HexColor(BRAND["navy"]), alignment=TA_LEFT, leading=23, spaceAfter=8))
    styles.add(ParagraphStyle(name="HeadingBlue", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, textColor=colors.HexColor(BRAND["primary"]), leading=14, spaceAfter=6, spaceBefore=6))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=12.5, textColor=colors.HexColor(BRAND["navy"]), spaceAfter=6))
    styles.add(ParagraphStyle(name="BodyTiny", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.1, leading=10.5, textColor=colors.HexColor("#5B748B"), spaceAfter=4))
    styles.add(ParagraphStyle(name="CardMetric", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.2, alignment=TA_CENTER, leading=10.4, textColor=colors.white))

    story = []
    title_table_data = []
    logo_cell = ""
    if LOGO_PATH.exists():
        logo_cell = Image(str(LOGO_PATH), width=2.0 * inch, height=0.66 * inch)
    title_table_data.append(
        [
            logo_cell,
            Paragraph("Higher Education CRM Maturity Assessment", styles["TitleNavy"]),
        ]
    )
    title_table = Table(title_table_data, colWidths=[2.05 * inch, 4.15 * inch])
    title_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(title_table)
    story.append(Paragraph(f"Executive report generated {utc_now_iso()} · Assessment token {token}", styles["BodyTiny"]))
    story.append(Spacer(1, 0.04 * inch))
    story.append(build_metric_cards(results, styles))
    story.append(Spacer(1, 0.16 * inch))

    context_table = Table(
        [
            ["Institution", context.get("institutionName", "Not provided"), "Type", context.get("institutionType", "Not provided")],
            ["Enrollment", context.get("enrollmentSize", "Not provided"), "Decentralization", context.get("decentralization", "Not provided")],
            ["CRM landscape", truncate_text(context.get("crmLandscape", "Not provided"), 74), "Strategic priorities", truncate_text(context.get("strategicPriorities", "Not provided"), 74)],
        ],
        colWidths=[1.05 * inch, 2.05 * inch, 1.2 * inch, 2.0 * inch],
    )
    context_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F9FC")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(BRAND["navy"])),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8D8E8")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.7),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(KeepTogether([
        Paragraph("Executive Summary", styles["HeadingBlue"]),
        Paragraph(results["executive_summary"], styles["BodySmall"]),
        Paragraph(results["overall_narrative"], styles["BodySmall"]),
        context_table,
    ]))
    story.append(Spacer(1, 0.16 * inch))

    story.append(Paragraph("Visual Analytics", styles["HeadingBlue"]))
    story.append(build_maturity_spectrum(results["overall_score"], results["overall_label"]))
    story.append(Spacer(1, 0.10 * inch))
    chart_table = Table(
        [[build_domain_score_chart(results["domain_results"]), build_distribution_chart(results["domain_results"]) ]],
        colWidths=[3.95 * inch, 2.15 * inch],
    )
    chart_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(chart_table)
    story.append(Spacer(1, 0.10 * inch))
    story.append(build_opportunity_chart(results["low_domains"]))
    story.append(Spacer(1, 0.16 * inch))

    domain_rows = [["Domain", "Weight", "Score", "Recommended next move"]]
    for domain in sorted(results["domain_results"], key=lambda item: item["average"]):
        domain_rows.append([
            domain["title"],
            f"{domain['weight']}%",
            f"{domain['average']:.2f}",
            truncate_text(domain["recommendations"][domain["phase"]], 92),
        ])
    domain_table = Table(domain_rows, colWidths=[2.18 * inch, 0.6 * inch, 0.62 * inch, 2.8 * inch])
    domain_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND["primary"])),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.15),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8D8E8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F9FC")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(Paragraph("Domain Scorecard", styles["HeadingBlue"]))
    story.append(domain_table)
    story.append(Spacer(1, 0.12 * inch))
    story.append(Paragraph("Heatmap Prioritization Table", styles["HeadingBlue"]))
    story.append(Paragraph("This heatmap uses red, yellow, and green maturity coloring to highlight stabilization priorities, build priorities, and scale opportunities across the CRM capability stack.", styles["BodySmall"]))
    story.append(build_heatmap_table(results["domain_results"]))
    story.append(Spacer(1, 0.14 * inch))

    story.append(Paragraph("Consultant-Facing Recommendations", styles["HeadingBlue"]))
    for item in results["consultant_recommendations"]:
        recommendation_box = Table(
            [[
                Paragraph(
                    f"<b>{item['domain']}</b><br/>Score {item['score']:.2f} · {item['priority']} priority<br/>{truncate_text(item['engagement_play'], 130)}<br/>"
                    + "<br/>".join([f"• {truncate_text(action, 120)}" for action in item["consultant_actions"]]),
                    styles["BodySmall"],
                )
            ]],
            colWidths=[6.15 * inch],
        )
        recommendation_box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FBFE")),
                    ("BOX", (0, 0), (-1, -1), 0.45, score_fill(item["score"])),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(recommendation_box)
        story.append(Spacer(1, 0.08 * inch))

    roadmap_groups = build_roadmap_groups(results["domain_results"])
    story.append(PageBreak())
    story.extend(build_roadmap_page("Client Roadmap — Quick Wins", "quick", roadmap_groups["quick"], styles))
    story.append(PageBreak())
    story.extend(build_roadmap_page("Client Roadmap — 12-Month Plan", "twelve", roadmap_groups["twelve"], styles))
    story.append(PageBreak())
    story.extend(build_roadmap_page("Client Roadmap — 24-Month Plan", "twenty_four", roadmap_groups["twenty_four"], styles))

    doc.build(story, onFirstPage=report_chrome, onLaterPages=report_chrome)
    buffer.seek(0)
    filename = f"crm-maturity-report-{token}.pdf"
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)


@app.route("/admin")
def admin():
    code = request.args.get("code", "")
    authorized = code == ADMIN_CODE
    selected_token = request.args.get("token", "")
    assessments = []
    selected = None

    if authorized:
        conn = get_conn()
        rows = conn.execute(
            "SELECT token, institution_name, institution_type, status, overall_score, overall_label, created_at, updated_at, payload FROM assessments ORDER BY updated_at DESC"
        ).fetchall()
        conn.close()
        for row in rows:
            assessments.append({
                "token": row["token"],
                "institution_name": row["institution_name"] or "Unnamed institution",
                "institution_type": row["institution_type"] or "Unknown",
                "status": row["status"],
                "overall_score": row["overall_score"],
                "overall_label": row["overall_label"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })
        if selected_token:
            row = fetch_assessment(selected_token)
            if row:
                payload = json.loads(row["payload"])
                selected = {
                    "token": row["token"],
                    "status": row["status"],
                    "payload": payload,
                    "results": compute_results(payload),
                    "updated_at": row["updated_at"],
                }
        elif assessments:
            row = fetch_assessment(assessments[0]["token"])
            payload = json.loads(row["payload"])
            selected = {
                "token": row["token"],
                "status": row["status"],
                "payload": payload,
                "results": compute_results(payload),
                "updated_at": row["updated_at"],
            }

    return render_template(
        "admin.html",
        authorized=authorized,
        admin_code=code,
        expected_code=ADMIN_CODE,
        assessments=assessments,
        selected=selected,
        brand=BRAND,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=True)
