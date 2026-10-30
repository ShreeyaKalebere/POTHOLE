"""CSV and PDF reports for the municipal corporation."""
import csv
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

CSV_FIELDS = ["incident_code", "damage_type", "severity", "status", "zone", "latitude",
              "longitude", "confidence", "reports_count", "assigned_to", "detected_at", "updated_at"]


def _row(inc):
    lng, lat = (inc.get("location") or {}).get("coordinates", [None, None])
    return {
        "incident_code": inc["incident_code"],
        "damage_type": "Pothole" if inc["damage_type"] == "pothole" else "Alligator Crack",
        "severity": inc["severity"], "status": inc["status"], "zone": inc.get("zone", ""),
        "latitude": lat, "longitude": lng, "confidence": inc.get("confidence"),
        "reports_count": inc.get("reports_count", 1), "assigned_to": inc.get("assigned_to") or "",
        "detected_at": inc["detected_at"].strftime("%Y-%m-%d %H:%M"),
        "updated_at": inc["updated_at"].strftime("%Y-%m-%d %H:%M"),
    }


def to_csv(items):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    w.writeheader()
    for inc in items:
        w.writerow(_row(inc))
    return buf.getvalue().encode("utf-8-sig")       # BOM so Excel opens it correctly


def to_pdf(items, stats, filters_text):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm,
                            title="Road Damage Report - Kolhapur")
    ss = getSampleStyleSheet()
    el = [Paragraph("Road Damage Report &mdash; Kolhapur Municipal Corporation", ss["Title"]),
          Paragraph(f"Generated {datetime.now():%d %b %Y, %H:%M} &nbsp;|&nbsp; Filters: {filters_text}",
                    ss["Normal"]), Spacer(1, 6 * mm)]

    summary = [["Total", "Potholes", "Alligator cracks", "High severity", "Reported", "In Progress", "Repaired"],
               [stats["total"], stats["by_type"].get("pothole", 0), stats["by_type"].get("alligator_crack", 0),
                stats["by_severity"].get("High", 0), stats["by_status"].get("Reported", 0),
                stats["by_status"].get("In Progress", 0), stats["by_status"].get("Repaired", 0)]]
    t = Table(summary, hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                           ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 0), (-1, -1), 10)]))
    el += [t, Spacer(1, 6 * mm), Paragraph("Incident list (High severity first)", ss["Heading2"])]

    head = ["Code", "Type", "Severity", "Status", "Zone", "Lat, Lng", "Reports", "Assigned", "Detected"]
    rows = [head]
    sev_color = {"High": "#f44336", "Medium": "#ff9800", "Low": "#4caf50"}
    for inc in items:
        r = _row(inc)
        rows.append([r["incident_code"], r["damage_type"], r["severity"], r["status"], r["zone"],
                     f"{r['latitude']:.5f}, {r['longitude']:.5f}" if r["latitude"] is not None else "-",
                     r["reports_count"], r["assigned_to"] or "-", r["detected_at"]])
    t = Table(rows, repeatRows=1, hAlign="LEFT")
    style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
             ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTSIZE", (0, 0), (-1, -1), 8),
             ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")])]
    for i, inc in enumerate(items, start=1):
        style.append(("TEXTCOLOR", (2, i), (2, i), colors.HexColor(sev_color[inc["severity"]])))
    t.setStyle(TableStyle(style))
    el.append(t)
    doc.build(el)
    return buf.getvalue()
