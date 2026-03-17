import base64
import re
from html import escape as esc
from pathlib import Path


def render_report_html(text: str) -> str:
    """Convert synthesizer markdown-like output to styled HTML for PDF rendering."""

    def inline(s: str) -> str:
        s = esc(s)
        s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
        s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
        s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)
        return s

    def parse_pipe_cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip('|').split('|')]

    def is_pipe_row(line: str) -> bool:
        s = line.strip()
        if not s:
            return False
        return s.startswith('|') or s.count('|') >= 2

    def is_md_separator(line: str) -> bool:
        s = line.strip()
        return bool(s) and bool(re.match(r'^[\|\ \-:]+$', s)) and '-' in s and '|' in s

    KV_KEYS = (
        'Action', 'Tool', 'Time to set up', 'Why now', 'Expected value',
        'One-time setup cost', 'Ongoing cost', 'Total setup time', 'Rating',
    )
    kv_pattern = re.compile(r'^(' + '|'.join(re.escape(k) for k in KV_KEYS) + r'):\s*(.*)')

    lines = text.split('\n')
    n = len(lines)
    out: list[str] = []
    i = 0

    while i < n:
        raw = lines[i]
        line = raw.strip()

        # ── horizontal separators (─────) ──────────────────────────────────
        if re.match(r'^[─\-]{4,}$', line):
            i += 1
            continue

        # ── markdown headings (## / ###) ───────────────────────────────────
        m = re.match(r'^(#{1,3})\s+(.+)', line)
        if m:
            lvl = min(len(m.group(1)) + 1, 4)
            out.append(f'<h{lvl}>{inline(m.group(2))}</h{lvl}>')
            i += 1
            continue

        # ── numbered section headings: "1. PROCESS OVERVIEW" ───────────────
        if re.match(r'^\d+\.\s+[A-Z][A-Z &]+$', line):
            out.append(f'<h2>{inline(line)}</h2>')
            i += 1
            continue

        # ── health rating line starting with colored circle ─────────────────
        if line and line[0] in '🟢🟡🔴':
            color_map = {'🟢': '#15803d', '🟡': '#b45309', '🔴': '#b91c1c'}
            col = color_map.get(line[0], '#374151')
            out.append(f'<p class="health" style="color:{col}">{inline(line)}</p>')
            i += 1
            continue

        # ── pipe table (collects rows + interleaved → recommendation lines) ─
        if is_pipe_row(raw) or is_md_separator(raw):
            rows: list[tuple[list[str], list[str]]] = []
            header_cells: list[str] | None = None

            while i < n:
                l = lines[i]
                ls = l.strip()
                if is_md_separator(l):
                    if rows:
                        header_cells = rows[-1][0]
                        rows = []
                    i += 1
                    continue
                if is_pipe_row(l):
                    rows.append((parse_pipe_cells(l), []))
                    i += 1
                    continue
                if ls.startswith('→ ') and rows:
                    rows[-1][1].append(ls[2:])
                    i += 1
                    continue
                break

            if header_cells is None and rows:
                first = rows[0][0]
                has_emoji = any(any(ord(ch) > 0x25FF for ch in c) for c in first)
                if not has_emoji:
                    header_cells = first
                    rows = rows[1:]

            ncols = len(header_cells) if header_cells else (len(rows[0][0]) if rows else 1)

            tbl = ['<table><thead><tr>']
            for c in (header_cells or []):
                tbl.append(f'<th>{inline(c)}</th>')
            tbl.append('</tr></thead><tbody>')
            for cells, recs in rows:
                tbl.append('<tr>')
                for c in cells:
                    tbl.append(f'<td>{inline(c)}</td>')
                tbl.append('</tr>')
                if recs:
                    rec_html = ' &nbsp;·&nbsp; '.join(
                        f'<span class="rec-arrow">→</span> {inline(r)}' for r in recs
                    )
                    tbl.append(f'<tr class="rec-row"><td colspan="{ncols}">{rec_html}</td></tr>')
            tbl.append('</tbody></table>')
            out.append(''.join(tbl))
            continue

        # ── standalone → recommendation lines ──────────────────────────────
        if line.startswith('→ '):
            parts = []
            while i < n and lines[i].strip().startswith('→ '):
                parts.append(
                    f'<div class="rec-line">'
                    f'<span class="rec-arrow">→</span> {inline(lines[i].strip()[2:])}'
                    f'</div>'
                )
                i += 1
            out.append(f'<div class="rec">{"".join(parts)}</div>')
            continue

        # ── key: value definition lines ─────────────────────────────────────
        if kv_pattern.match(line):
            items = []
            while i < n:
                m2 = kv_pattern.match(lines[i].strip())
                if m2:
                    items.append(
                        f'<div class="kv">'
                        f'<span class="kv-key">{esc(m2.group(1))}</span>'
                        f'<span class="kv-val">{inline(m2.group(2))}</span>'
                        f'</div>'
                    )
                    i += 1
                else:
                    break
            out.append(f'<div class="kv-block">{"".join(items)}</div>')
            continue

        # ── bullet list (-, *, •) ───────────────────────────────────────────
        if re.match(r'^[-*•]\s', line):
            items = []
            while i < n and re.match(r'^[-*•]\s', lines[i].strip()):
                items.append(f'<li>{inline(lines[i].strip()[2:])}</li>')
                i += 1
            out.append(f'<ul>{"".join(items)}</ul>')
            continue

        # ── numbered list (not section headings) ────────────────────────────
        m = re.match(r'^(\d+)[.)]\s+(.+)', line)
        if m and not re.match(r'^\d+\.\s+[A-Z][A-Z &]+$', line):
            items = []
            while i < n:
                m2 = re.match(r'^\d+[.)]\s+(.+)', lines[i].strip())
                if m2 and not re.match(r'^\d+\.\s+[A-Z][A-Z &]+$', lines[i].strip()):
                    items.append(f'<li>{inline(m2.group(1))}</li>')
                    i += 1
                else:
                    break
            out.append(f'<ol>{"".join(items)}</ol>')
            continue

        # ── Verdicts legend line ─────────────────────────────────────────────
        if line.startswith('Verdicts:'):
            out.append(f'<p class="legend">{inline(line)}</p>')
            i += 1
            continue

        # ── empty line → spacing ─────────────────────────────────────────────
        if not line:
            out.append('<div class="vspace"></div>')
            i += 1
            continue

        # ── default: paragraph ───────────────────────────────────────────────
        out.append(f'<p>{inline(line)}</p>')
        i += 1

    return '\n'.join(out)


PDF_CSS = """
  @page { size: A4; margin: 1.5cm; }
  @page diagram { size: A4 landscape; margin: 1cm; }

  body {
    font-family: DejaVu Sans, sans-serif;
    font-size: 10pt;
    line-height: 1.55;
    color: #1f2937;
    margin: 0;
  }

  .cover {
    height: 264mm;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  .cover-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
  }
  h1 { font-size: 22pt; color: #1e1b4b; margin: 0 0 8pt; }
  .meta { color: #6b7280; font-size: 11pt; margin: 0; }
  .cover-brand { padding-bottom: 4pt; text-align: center; }
  .cover-brand img { height: 28pt; display: block; margin: 0 auto 5pt; }
  .cover-brand p { font-size: 8.5pt; color: #9ca3af; margin: 0; }
  .diagram-page { page: diagram; break-inside: avoid; }
  .diagram-page h2 { font-size: 12pt; color: #4338ca; margin: 0 0 6pt;
                     border-bottom: 1px solid #e0e7ff; padding-bottom: 3pt;
                     break-after: avoid; }
  .diagram-page svg { width: 100%; height: 172mm; display: block; }

  .report-body h2 {
    font-size: 11pt; font-weight: 700; color: #4338ca;
    margin: 18pt 0 5pt; padding-bottom: 3pt;
    border-bottom: 1px solid #e0e7ff; page-break-after: avoid;
  }
  .report-body h3 {
    font-size: 10.5pt; font-weight: 600; color: #374151;
    margin: 12pt 0 4pt; page-break-after: avoid;
  }
  .report-body h4 {
    font-size: 10pt; font-weight: 600; color: #374151;
    margin: 8pt 0 3pt; page-break-after: avoid;
  }
  .report-body p { margin: 0 0 6pt; }
  .report-body code {
    font-family: DejaVu Sans Mono, monospace; font-size: 8.5pt;
    background: #f3f4f6; padding: 1pt 3pt; border-radius: 2pt;
  }

  .report-body table {
    width: 100%; border-collapse: collapse; font-size: 9pt;
    margin: 6pt 0 10pt; page-break-inside: auto;
  }
  .report-body th {
    background: #4338ca; color: #ffffff; font-weight: 600;
    text-align: left; padding: 5pt 7pt; border: 1px solid #4338ca;
  }
  .report-body td { padding: 4pt 7pt; border: 1px solid #e5e7eb; vertical-align: top; }
  .report-body tr:nth-child(even) td { background: #f9fafb; }
  .report-body tr.rec-row td {
    background: #f0fdf4; color: #166534; font-size: 8.5pt;
    padding: 3pt 7pt 3pt 14pt; border-top: none;
  }
  .rec-arrow { color: #16a34a; font-weight: 700; }

  .rec {
    background: #f0fdf4; border-left: 3pt solid #16a34a;
    padding: 5pt 8pt; margin: 4pt 0 8pt; font-size: 9pt; color: #166534;
  }
  .rec-line { margin: 1pt 0; }

  .kv-block {
    background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 4pt;
    padding: 7pt 10pt; margin: 6pt 0 10pt; font-size: 9.5pt;
  }
  .kv { display: block; margin: 2pt 0; }
  .kv-key { font-weight: 700; color: #374151; min-width: 110pt; display: inline-block; }
  .kv-val { color: #1f2937; }

  .health { font-size: 11pt; font-weight: 700; margin: 4pt 0 8pt; }

  .report-body ul, .report-body ol { margin: 4pt 0 8pt 16pt; padding: 0; }
  .report-body li { margin: 2pt 0; }

  .legend { font-size: 8.5pt; color: #6b7280; margin: 2pt 0 6pt; }
  .vspace { height: 6pt; }
"""


def normalize_svg(svg: str) -> str:
    """Strip fixed width/height so CSS can control the size."""
    if not svg:
        return svg
    svg = re.sub(r'\s+width="[^"]*"', '', svg, count=1)
    svg = re.sub(r'\s+height="[^"]*"', '', svg, count=1)
    if 'preserveAspectRatio' not in svg:
        svg = svg.replace('<svg', '<svg preserveAspectRatio="xMidYMid meet"', 1)
    return svg


def build_pdf(
    diagram_asis: str,
    diagram_improved: str,
    report: str,
    business_type: str,
    process_name: str,
) -> bytes:
    from weasyprint import HTML

    diagram_asis = normalize_svg(diagram_asis)
    diagram_improved = normalize_svg(diagram_improved)
    report_html = render_report_html(report)

    meta = business_type + (' · ' + process_name if process_name else '')
    no_diagram = '<p style="color:#9ca3af">No diagram available.</p>'

    logo_path = Path(__file__).parent.parent / "static" / "assets" / "logo.png"
    logo_data = base64.b64encode(logo_path.read_bytes()).decode() if logo_path.exists() else ""
    logo_src = f"data:image/png;base64,{logo_data}" if logo_data else ""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>{PDF_CSS}</style></head><body>
  <div class="cover">
    <div class="cover-main">
      <h1>Operational Assessment</h1>
      <div class="meta">{meta}</div>
    </div>
    <div class="cover-brand">
      {'<img src="' + logo_src + '" alt="FlowNext">' if logo_src else ''}
      <p>Prepared by <a href="https://flownext.co" style="color:#9ca3af">flownext.co</a></p>
    </div>
  </div>

  <div class="diagram-page">
    <h2>Current Process Flow</h2>
    {diagram_asis if diagram_asis else no_diagram}
  </div>

  <div class="diagram-page">
    <h2>Improved Process Flow</h2>
    {diagram_improved if diagram_improved else no_diagram}
  </div>

  <div class="report-body">
    {report_html}
  </div>
</body></html>"""

    return HTML(string=html).write_pdf()
