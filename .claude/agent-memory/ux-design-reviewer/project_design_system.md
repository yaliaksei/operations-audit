---
name: Design system conventions
description: Color palette, typography, component patterns, and layout conventions observed in index.html (amber theme, current state)
type: project
---

## Color palette

- Primary: amber-600 (#d97706) for CTAs, active wizard dots, active pipeline steps, send button
- Primary light: amber-50 / amber-100 / #fffbeb for badge backgrounds, bubble gradients, chip fills
- Secondary: green-500/green-50 (automate verdict), blue-400/blue-50 (replace verdict)
- Background: gradient-bg (#fdfaf6), min-height: 100vh
- Glass card: rgba(255,255,255,0.9) + backdrop-blur(12px) + border amber-100/15 + custom box-shadow
- Borders: gray-200 / #e2e8f0 (inputs, cards), gray-200/60 (nav bottom, chat divider)
- Text hierarchy: gray-900 (headings/labels), gray-700 (body medium), gray-500 (helper/subtitle), gray-400 (meta/placeholder), amber-700 (active pipeline text)
- Error: red-500 (text), red-400 (#f87171 border), ring-red-100
- Chat agent bubble: linear-gradient(135deg, #fffbeb, #fef3c7), border-radius 1rem 1rem 1rem 0.25rem
- Chat user bubble: white + border gray-200, border-radius 1rem 1rem 0.25rem 1rem
- Typing/streaming dots: amber (#fbbf24)

## Typography — current (as-built)

- Font: Inter (Google Fonts, weights 400/500/600/700/800)
- Nav brand name: text-sm font-semibold text-gray-900
- Nav badge: text-xs font-medium text-amber-700
- Step 0 H1 (hero): text-2xl sm:text-3xl font-extrabold text-gray-900 tracking-tight
- Step 1/2 H2 (sub-pages): text-xl sm:text-2xl font-bold text-gray-900
- Phase headings (Interview, Processing, Verify, Report): text-xl font-bold text-gray-900
- Section card sub-heading (e.g. "Current Process"): text-sm font-semibold text-gray-700
- Form labels: text-sm font-semibold text-gray-700
- Body/subtitle (hero): text-base leading-relaxed text-gray-500
- Body/subtitle (sub-steps): text-sm text-gray-500
- Input text: font-size 0.95rem (#modern-input custom CSS), color #1e293b
- Input placeholder: color #94a3b8
- Buttons (primary + secondary): text-sm font-semibold
- Chat messages: text-sm text-gray-700 leading-relaxed
- Chat sender label: text-[11px] font-medium (amber-500 for agent, gray-400 for user)
- Final report pre: text-sm text-gray-800 leading-7
- Helper/legal text: text-xs text-gray-400
- Error text: text-xs text-red-500
- Sidebar nav labels: text-sm font-medium text-gray-700; sub-labels text-xs text-gray-400
- Sidebar section title: text-xs font-semibold text-gray-400 uppercase tracking-wider
- Detail panel metadata labels: text-[10px] font-medium text-gray-400 uppercase tracking-wide
- Detail panel content: text-xs text-gray-700
- Wizard dots: font-size 0.75rem font-weight 600

## Buttons

- Primary CTA: rounded-xl bg-amber-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-amber-500 transition-all active:scale-[0.98]
- Secondary/ghost: rounded-xl bg-white px-5 py-3 text-sm font-semibold text-gray-600 ring-1 ring-inset ring-gray-200 hover:bg-gray-50
- Compact action (report page): px-4 py-2 (not py-3)
- Chat send button: px-4 py-2.5 text-sm

## Form inputs

- .modern-input custom CSS: font-size 0.95rem; padding 0.75rem 1rem (left 2.75rem for icon); border 1.5px #e2e8f0; border-radius 0.75rem; color #1e293b
- Focus: border-color #d97706; box-shadow 0 0 0 3px rgba(217,119,6,0.12)
- Chat input: rounded-xl border border-gray-200 px-4 py-2.5 text-sm
- Textarea (paste mode): rounded-xl border-1.5 border-gray-200 px-4 py-3 text-sm
- Textarea (detail panel): resize-y

## Cards / panels

- Glass card: .glass-card class (see above) + rounded-2xl; padding p-6 sm:p-8
- Detail panel (node info): bg-white shadow-sm ring-1 ring-gray-200 rounded-lg p-4 text-sm; width w-72

## Layout

- Setup wizard: max-w-xl px-4 sm:px-6 pt-12 pb-20
- Pipeline layout: max-w-5xl px-4 sm:px-6 lg:px-8 py-8; lg:grid-cols-12 (sidebar col-3, main col-9)
- Nav: max-w-5xl px-4 sm:px-6 lg:px-8; height h-14; sticky top-0 z-20

## Animations / interactions

- fade-in: opacity 0→1, translateY 8px→0, 0.3s ease
- wizIn: opacity 0→1, translateY 16px→0, 0.35s ease
- phaseIn: opacity 0→1, translateY 12px→0, 0.35s ease
- streaming cursor: amber (#d97706) blinking dot after text
- typing indicator: 3 amber dots with bounce animation
- pulse-ring: amber glow ring on processing spinner
- Active wizard dot: amber-600 background with 4px amber glow ring
- Mic recording: red bg + red pulsing icon

## SVG diagram text sizes (inline, not Tailwind)

- Node label: font-size 11.5, font-weight 500
- Node sublabel: font-size 9.5, opacity 0.6
- Node number badge: font-size 9, font-weight 700
- Decision node text: font-size 11, font-weight 500
- Start/end node text: font-size 12, font-weight 600
- Edge label: font-size 9
- Verdict badge: font-size 7.5, font-weight 700

## Why
These conventions come from reading the current index.html (amber theme, as of March 2026). They supersede the older indigo-theme memory.

## How to apply
Any new UI elements must use amber-600 as the primary color, text-sm for most interactive elements, and glass-card pattern for content panels.
