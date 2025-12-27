# report.py
import os

def generate_report(project, score, breakdown, suggestions):
    project_name = os.path.basename(os.path.abspath(project))
    report_name = f"report_{project_name}.md"

    lines = []
    lines.append("# Codebase Health Report\n")
    lines.append(f"**Project:** {project}\n")
    lines.append(f"**Health Score:** {score}/100\n")

    # Score breakdown
    lines.append("## Score Breakdown\n")
    for k, v in breakdown.items():
        lines.append(f"- **{k.capitalize()}**: {v}")
    lines.append("")

    # Detailed findings
    lines.append("## Detailed Findings\n")
    if not suggestions:
        lines.append("No significant issues detected ✅")
        lines.append("")
    else:
        for s in suggestions:
            lines.append(f"### {s['severity']} — {s['title']}\n")
            lines.append(f"**What was found**  \n{s['what']}\n")
            lines.append(f"**Why this matters**  \n{s['why']}\n")
            lines.append(f"**Recommended improvement**  \n{s['how']}\n")
            lines.append("---\n")

    # Recommended actions summary (priority order)
    lines.append("## Recommended Actions (Priority Order)\n")
    if not suggestions:
        lines.append("No immediate action required.")
    else:
        # High -> Medium -> Low
        priority = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_suggestions = sorted(suggestions, key=lambda s: priority.get(s["severity"], 3))

        for i, s in enumerate(sorted_suggestions, start=1):
            lines.append(f"{i}. {s['how']}")

    content = "\n".join(lines)

    with open(report_name, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"📄 Report generated: {report_name}")
