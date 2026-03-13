---
name: FlowNext product context
description: Core product details, target audience, and content strategy context for FlowNext — the AI workflow audit tool this user is building
type: project
---

FlowNext is a free Flask web app ("AI operations advisor") that interviews SMB owners about a business workflow, runs a 7-stage AI pipeline audit, and delivers a PDF report with flow diagrams and ROI-based recommendations.

**Why:** The product is positioned as a free, instant alternative to hiring a process consultant ($150–$400/hr, weeks of turnaround). It takes 10 minutes, requires no signup, and outputs a downloadable PDF with step-by-step verdicts (keep/improve/replace/automate) and ROI math.

**Target audience:** SMB owners with 5–50 employees who are drowning in manual work and haven't thought systematically about their operations. Decision-makers who wear multiple hats and are time-poor.

**How to apply:** All content should speak directly to this owner's lived experience. Lead with their pain, not the product. Use ROI and time-as-money framing. Avoid buzzwords.

**Tone reference:** Basecamp, Hey.com, Fizzy.do — direct, human, opinionated, no corporate jargon, talks to the owner not the enterprise.

**Pages and templates:**
- `templates/landing.html` — main marketing page (already strong; hero copy excellent, FAQs, social proof, process grid)
- `templates/for.html` — Jinja2 template for 12 process-specific landing pages, data-driven from `seo/*.yaml`
- `templates/contact.html` — contact form page
- `seo/*.yaml` — 12 files with per-process SEO data (title, meta, h1, subtitle, pain points, cta_text, related)

**SEO work completed (2026-03-13):**
- Added FAQ structured data (FAQPage schema) to landing.html
- Sharpened H2s on landing.html ("How it works: four steps, then you have a plan", "Any process that repeats is worth auditing", "Questions you probably have")
- Tightened "What you get" section subheading
- Updated FAQ answers to remove "no catch" phrasing → "no upsell waiting at the end"
- Honest consultant comparison answer now names FlowNext explicitly
- for.html: pain points H2 now "Sound familiar? These are the most common X problems"
- for.html: audit gives you section H2 changed from "reveals" to "gives you"
- for.html: CTA H2 changed from "Ready to fix your X?" to "You already know something's wrong. Now find out exactly what."
- for.html: related section label changed from "Also worth auditing" to "Once you've fixed this one, these are next"
- contact.html: added meta title and description, rewrote H1 to "We read every message", rewrote intro paragraph, fixed "AI AI" footer typo, improved form placeholders
