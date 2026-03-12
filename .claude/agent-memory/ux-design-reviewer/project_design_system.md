---
name: Design system conventions
description: Color palette, typography, component patterns, and layout conventions observed in the codebase
type: project
---

## Color palette

- Primary: indigo-600 (#6366f1) for CTAs, active states, and accent icons
- Primary light: indigo-100 / indigo-50 / #eef2ff for hover states, badges, backgrounds
- Secondary accent icons: green-600, violet-600, amber-600 (used for feature card icons only)
- Backgrounds: white, gray-50 (alternating sections), gradient-hero (#eef2ff → #f8fafc → #f0fdf4)
- Borders: gray-100 (cards, section dividers), border-indigo-200 (hover)
- Text hierarchy: gray-900 (headings), gray-700 (body medium), gray-500 (body light / helper), gray-400 (meta/footer)
- Error: red-400 / #f87171

## Typography

- Font: Inter (Google Fonts, weights 400/500/600/700/800)
- H1: text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-tight
- H2 (section headers): text-2xl font-bold
- H3 (card titles): font-semibold text-gray-900
- Body: text-sm text-gray-500 leading-relaxed (cards); text-lg sm:text-xl text-gray-500 (hero subheadline)
- Meta/labels: text-xs text-gray-400 / text-xs font-medium text-gray-600

## Buttons

- Primary CTA: rounded-lg bg-indigo-600 px-6 py-3 text-base font-semibold text-white shadow-sm hover:bg-indigo-500 transition-colors
- Nav CTA (small): rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors

## Cards

- Feature cards: bg-gray-50 rounded-xl p-6 border border-gray-100
- Testimonial cards: bg-white rounded-xl p-6 border border-gray-100 shadow-sm
- App glass card: background rgba(255,255,255,0.85), backdrop-filter blur(12px), custom shadow

## Layout

- Max widths: max-w-6xl (wide sections), max-w-4xl (hero), max-w-3xl (how-it-works), max-w-2xl (FAQ, final CTA)
- Padding: px-4 sm:px-6 lg:px-8 consistently
- Section vertical rhythm: py-16 (standard), py-20 or py-28 (hero/final CTA)
- Grid: grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 (feature cards), sm:grid-cols-3 (testimonials)

## App-specific patterns (index.html)

- gradient-bg: 135deg, #eef2ff → #f8fafc → #f0fdf4 → #faf5ff, full min-height
- Glass card: semi-transparent white with backdrop blur for the main app panel
- Chat bubbles: agent = indigo gradient bg, user = white with border
- Wizard dots: indigo for active/reached states
- Custom animations: fade-in, streaming cursor blink (indigo), typing bounce dots (a5b4fc)

## Why:** These conventions come from the existing codebase — they define what "on-brand" looks like for this project.
## How to apply:** Any new UI elements must use these tokens. Flag deviations in reviews.
