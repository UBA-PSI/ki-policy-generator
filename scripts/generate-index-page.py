#!/usr/bin/env python3
"""
Generate the overview page for /p/index.html listing all presets.

Includes: branding bar, decision tree (expanded), comparison table (A/B/C model),
preset cards, bilingual DE/EN toggle, and responsive design.
"""

import html
import os
import re
import sys

import yaml


def escape(text):
    return html.escape(text, quote=True)


def parse_inline_md(text):
    """Minimal inline markdown: **bold** only."""
    text = escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return text


# ---------------------------------------------------------------------------
# Decision tree data (structural, not content — hardcoded in both languages)
# ---------------------------------------------------------------------------

DECISION_TREE = {
    'de': {
        'q1': {
            'question': 'Soll KI zum Lernen im Semester erlaubt sein?',
            'hint': None,
            'options': [
                {'label': 'Nein', 'next': 'r-none'},
                {'label': 'Ja', 'next': 'q2'},
            ],
        },
        'q2': {
            'question': 'Gibt es bewertete Arbeiten, die ohne Aufsicht erstellt werden?',
            'hint': 'z.\u202fB. Hausaufgaben, Seminararbeiten, Projektabgaben, Folienvorbereitung f\u00fcr Referate',
            'options': [
                {'label': 'Nein', 'next': 'r-learn-1'},
                {'label': 'Ja', 'next': 'q3'},
            ],
        },
        'q3': {
            'question': 'Soll KI bei diesen Arbeiten erlaubt sein?',
            'hint': None,
            'options': [
                {'label': 'Nein', 'next': 'r-learn-2'},
                {'label': 'Ja', 'next': 'q4'},
            ],
        },
        'q4': {
            'question': 'Wie wird sichergestellt, dass Studierende die Inhalte beherrschen?',
            'hint': None,
            'options': [
                {'label': 'Einfache Kennzeichnung (Tool + Zweck)', 'next': 'r-docshort'},
                {'label': 'Ausf\u00fchrliche Dokumentation (Prompt-Protokoll + Reflexion)', 'next': 'r-doclog'},
                {'label': 'Pr\u00fcfung unter Aufsicht (m\u00fcndlich oder schriftlich)', 'next': 'r-defend'},
                {'label': 'KI-Kompetenz ist selbst Lernziel', 'next': 'r-skill'},
            ],
        },
        'results': {
            'r-none': {'preset': 'ai-none', 'desc': 'KI-Werkzeuge sind nicht erlaubt \u2013 weder zum Lernen noch bei Abgaben.'},
            'r-learn-1': {'preset': 'ai-learn', 'desc': 'KI darf frei zum Lernen genutzt werden. Die Pr\u00fcfung erfolgt unter Aufsicht ohne KI.'},
            'r-learn-2': {'preset': 'ai-learn', 'desc': 'KI darf zum Lernen genutzt werden, aber nicht bei bewerteten Arbeiten. Die Pr\u00fcfung erfolgt unter Aufsicht ohne KI.'},
            'r-docshort': {'preset': 'ai-docshort', 'desc': 'KI bei Abgaben erlaubt. Einfache Kennzeichnung (Tool + Zweck).'},
            'r-doclog': {'preset': 'ai-doclog', 'desc': 'KI bei Abgaben erlaubt. Prompt-Protokoll und Reflexion erforderlich.'},
            'r-defend': {'preset': 'ai-defend', 'desc': 'KI ohne Einschr\u00e4nkung. Kompetenznachweis durch Pr\u00fcfung unter Aufsicht.'},
            'r-skill': {'preset': 'ai-skill', 'desc': 'KI-Kompetenz ist Lernziel. Prozess und Ergebnis werden bewertet.'},
        },
        'restart': 'Neu starten',
    },
    'en': {
        'q1': {
            'question': 'Should AI be allowed for learning during the semester?',
            'hint': None,
            'options': [
                {'label': 'No', 'next': 'r-none'},
                {'label': 'Yes', 'next': 'q2'},
            ],
        },
        'q2': {
            'question': 'Are there graded assignments produced without supervision?',
            'hint': 'e.g., homework, term papers, project deliverables, slide preparation for presentations',
            'options': [
                {'label': 'No', 'next': 'r-learn-1'},
                {'label': 'Yes', 'next': 'q3'},
            ],
        },
        'q3': {
            'question': 'Should AI be allowed for these assignments?',
            'hint': None,
            'options': [
                {'label': 'No', 'next': 'r-learn-2'},
                {'label': 'Yes', 'next': 'q4'},
            ],
        },
        'q4': {
            'question': 'How do you ensure students master the content?',
            'hint': None,
            'options': [
                {'label': 'Simple labeling (tool + purpose)', 'next': 'r-docshort'},
                {'label': 'Detailed documentation (prompt log + reflection)', 'next': 'r-doclog'},
                {'label': 'Supervised exam (oral or written)', 'next': 'r-defend'},
                {'label': 'AI competence is itself a learning goal', 'next': 'r-skill'},
            ],
        },
        'results': {
            'r-none': {'preset': 'ai-none', 'desc': 'AI tools are not permitted \u2013 neither for learning nor for submissions.'},
            'r-learn-1': {'preset': 'ai-learn', 'desc': 'AI may be used freely for learning. The exam is supervised without AI.'},
            'r-learn-2': {'preset': 'ai-learn', 'desc': 'AI may be used for learning but not for graded work. The exam is supervised without AI.'},
            'r-docshort': {'preset': 'ai-docshort', 'desc': 'AI permitted for submissions. Simple labeling (tool + purpose).'},
            'r-doclog': {'preset': 'ai-doclog', 'desc': 'AI permitted for submissions. Prompt log and reflection required.'},
            'r-defend': {'preset': 'ai-defend', 'desc': 'AI without restrictions. Competence verified through supervised exam.'},
            'r-skill': {'preset': 'ai-skill', 'desc': 'AI competence is a learning goal. Process and result are assessed.'},
        },
        'restart': 'Start over',
    },
}

# Comparison table data
COMPARISON_TABLE = {
    'de': {
        'headers': ['Preset', 'A: KI zum Lernen', 'B: KI bei Arbeiten ohne Aufsicht', 'C: Pr\u00fcfung unter Aufsicht', 'Kennzeichnung'],
        'rows': [
            {'preset': 'ai-none', 'name': 'AI-None', 'cells': ['\u2717 Nicht erlaubt', '\u2717 Nicht erlaubt', 'Ohne KI', '\u2013'], 'classes': ['c-no', 'c-no', '', '']},
            {'preset': 'ai-learn', 'name': 'AI-Learn', 'cells': ['\u2713 Erlaubt', '\u2717 Nicht erlaubt', 'Ohne KI', 'Nicht erforderlich'], 'classes': ['c-yes', 'c-no', '', '']},
            {'preset': 'ai-docshort', 'name': 'AI-DocShort', 'cells': ['\u2713 Erlaubt', '\u2713 Erlaubt', 'Ohne KI', 'Einfach (Tool + Zweck)'], 'classes': ['c-yes', 'c-yes', '', '']},
            {'preset': 'ai-doclog', 'name': 'AI-DocLog', 'cells': ['\u2713 Erlaubt', '\u2713 Erlaubt', 'Ohne KI', 'Ausf\u00fchrlich (Protokoll + Reflexion)'], 'classes': ['c-yes', 'c-yes', '', '']},
            {'preset': 'ai-defend', 'name': 'AI-Defend', 'cells': ['\u2713 Erlaubt', '\u2713 Ohne Einschr\u00e4nkung', 'Ohne KI', 'Nicht erforderlich'], 'classes': ['c-yes', 'c-yes', '', '']},
            {'preset': 'ai-skill', 'name': 'AI-Skill', 'cells': ['\u2713 Erlaubt', '\u2713 KI-Kompetenz ist Lernziel', 'KI-Kompetenz wird gepr\u00fcft', 'Protokoll + Reflexion (benotet)'], 'classes': ['c-yes', 'c-yes', '', '']},
        ],
        'hint': '\u2191 Restriktiv \u00b7 Permissiv \u2193',
    },
    'en': {
        'headers': ['Preset', 'A: AI for Learning', 'B: AI for Unsupervised Work', 'C: Supervised Assessment', 'Documentation'],
        'rows': [
            {'preset': 'ai-none', 'name': 'AI-None', 'cells': ['\u2717 Not allowed', '\u2717 Not allowed', 'Without AI', '\u2013'], 'classes': ['c-no', 'c-no', '', '']},
            {'preset': 'ai-learn', 'name': 'AI-Learn', 'cells': ['\u2713 Allowed', '\u2717 Not allowed', 'Without AI', 'Not required'], 'classes': ['c-yes', 'c-no', '', '']},
            {'preset': 'ai-docshort', 'name': 'AI-DocShort', 'cells': ['\u2713 Allowed', '\u2713 Allowed', 'Without AI', 'Simple (tool + purpose)'], 'classes': ['c-yes', 'c-yes', '', '']},
            {'preset': 'ai-doclog', 'name': 'AI-DocLog', 'cells': ['\u2713 Allowed', '\u2713 Allowed', 'Without AI', 'Detailed (log + reflection)'], 'classes': ['c-yes', 'c-yes', '', '']},
            {'preset': 'ai-defend', 'name': 'AI-Defend', 'cells': ['\u2713 Allowed', '\u2713 Without restrictions', 'Without AI', 'Not required'], 'classes': ['c-yes', 'c-yes', '', '']},
            {'preset': 'ai-skill', 'name': 'AI-Skill', 'cells': ['\u2713 Allowed', '\u2713 AI competence is learning goal', 'AI competence assessed', 'Log + reflection (graded)'], 'classes': ['c-yes', 'c-yes', '', '']},
        ],
        'hint': '\u2191 Restrictive \u00b7 Permissive \u2193',
    },
}


def build_decision_tree_html(tree_data, presets_by_id, lang, table_data, hidden=False):
    """Build the decision tree HTML for one language."""
    back_label = 'Zurück' if lang == 'de' else 'Back'
    table_by_preset = {row['preset']: row for row in table_data['rows']}
    # Strip "A: " / "B: " / "C: " prefix from headers, skip first (Preset) column
    prop_labels = [re.sub(r'^[A-C]:\s*', '', h) for h in table_data['headers'][1:]]
    parts = []
    hide = ' style="display:none"' if hidden else ''
    parts.append(f'<div class="decision-tree" data-lang="{lang}"{hide}>')

    # Question steps
    for step_id in ['q1', 'q2', 'q3', 'q4']:
        step = tree_data[step_id]
        active = ' dt-active' if step_id == 'q1' else ''
        parts.append(f'<div class="dt-step{active}" data-step="{step_id}">')
        parts.append(f'<div class="dt-question">{escape(step["question"])}</div>')
        if step['hint']:
            parts.append(f'<div class="dt-hint">{escape(step["hint"])}</div>')
        parts.append('<div class="dt-options">')
        for opt in step['options']:
            parts.append(f'<button class="dt-option" data-next="{opt["next"]}">{escape(opt["label"])}</button>')
        parts.append('</div>')
        if step_id != 'q1':
            parts.append(f'<button class="dt-back">&larr; {escape(back_label)}</button>')
        parts.append('</div>')

    # Result steps
    for result_id, result in tree_data['results'].items():
        pid = result['preset']
        preset = presets_by_id.get(pid, {})
        color = preset.get('color', '#666')
        name = preset.get('name', pid)
        parts.append(f'<div class="dt-step dt-result" data-step="{result_id}" style="--preset-color:{color}">')
        parts.append(f'<div class="dt-result-head">')
        parts.append(f'<div class="dt-result-badge">{escape(name)}</div>')
        parts.append(f'<div class="dt-result-desc">{escape(result["desc"])}</div>')
        parts.append('</div>')
        row = table_by_preset.get(pid)
        if row:
            parts.append('<div class="dt-props">')
            for label, cell, cls in zip(prop_labels, row['cells'], row['classes']):
                cls_attr = f' {cls}' if cls else ''
                parts.append(f'<div class="dt-prop"><div class="dt-prop-label">{escape(label)}</div><div class="dt-prop-value{cls_attr}">{escape(cell)}</div></div>')
            parts.append('</div>')
        parts.append(f'<a href="{pid}/{lang}/" class="dt-view-preset">{escape(name)} ansehen &rarr;</a>' if lang == 'de' else f'<a href="{pid}/{lang}/" class="dt-view-preset">View {escape(name)} &rarr;</a>')
        parts.append('</div>')

    parts.append('</div>')
    return '\n'.join(parts)


def build_comparison_table_html(table_data, presets_by_id, lang, hidden=False):
    """Build the comparison table HTML for one language."""
    parts = []
    hide = ' style="display:none"' if hidden else ''
    parts.append(f'<div class="comparison-table-wrap" data-lang="{lang}"{hide}>')
    parts.append('<table class="comparison-table">')

    # Header
    parts.append('<thead><tr>')
    for h in table_data['headers']:
        parts.append(f'<th>{escape(h)}</th>')
    parts.append('</tr></thead>')

    # Body
    parts.append('<tbody>')
    for row in table_data['rows']:
        pid = row['preset']
        color = presets_by_id.get(pid, {}).get('color', '#666')
        parts.append('<tr>')
        parts.append(f'<td class="row-label"><a href="{pid}/{lang}/"><span class="ct-dot" style="background:{color}"></span>{escape(row["name"])}</a></td>')
        for cell, cls in zip(row['cells'], row['classes']):
            cls_attr = f' class="{cls}"' if cls else ''
            parts.append(f'<td{cls_attr}>{escape(cell)}</td>')
        parts.append('</tr>')
    parts.append('</tbody></table>')

    parts.append(f'<p class="comparison-hint">{escape(table_data["hint"])}</p>')
    parts.append('</div>')
    return '\n'.join(parts)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_dir = os.path.join(project_root, 'data')
    output_dir = os.path.join(project_root, 'p')

    presets_de = yaml.safe_load(open(os.path.join(data_dir, 'presets.yaml'), encoding='utf-8'))
    presets_en = yaml.safe_load(open(os.path.join(data_dir, 'presets-en.yaml'), encoding='utf-8'))

    # Load shared info boxes and transform for /p/ (data-ui-lang -> data-lang)
    info_boxes_path = os.path.join(data_dir, 'info-boxes.html')
    with open(info_boxes_path, encoding='utf-8') as f:
        info_boxes_html = f.read()
    info_boxes_html = info_boxes_html.replace('data-ui-lang', 'data-lang')

    presets_by_id_de = {p['id']: p for p in presets_de.get('presets', [])}
    presets_by_id_en = {p['id']: p for p in presets_en.get('presets', [])}

    # Build decision trees
    dt_de = build_decision_tree_html(DECISION_TREE['de'], presets_by_id_de, 'de', COMPARISON_TABLE['de'])
    dt_en = build_decision_tree_html(DECISION_TREE['en'], presets_by_id_en, 'en', COMPARISON_TABLE['en'], hidden=True)

    # Build comparison tables
    ct_de = build_comparison_table_html(COMPARISON_TABLE['de'], presets_by_id_de, 'de')
    ct_en = build_comparison_table_html(COMPARISON_TABLE['en'], presets_by_id_en, 'en', hidden=True)

    # Build preset cards
    cards_html = ''
    for preset in presets_de.get('presets', []):
        pid = preset['id']
        en = presets_by_id_en.get(pid, {})
        color = preset.get('color', '#666')
        name = preset.get('name', pid)
        desc_de = preset.get('description', '')
        desc_en = en.get('description', '')

        # TL;DR bullets (DE)
        bullets_de = ''
        for b in preset.get('tldr', []):
            bullets_de += f'<li>{parse_inline_md(b)}</li>\n'

        # TL;DR bullets (EN)
        bullets_en = ''
        for b in en.get('tldr', []):
            bullets_en += f'<li>{parse_inline_md(b)}</li>\n'

        cards_html += f'''
        <div class="preset-card" data-preset="{pid}">
            <div class="preset-card-header" style="background-color: {color}; color: #fff;">
                <h2 class="preset-name">{escape(name)}</h2>
            </div>
            <div class="preset-card-body">
                <p class="preset-desc" data-lang="de">{escape(desc_de)}</p>
                <p class="preset-desc" data-lang="en" style="display:none">{escape(desc_en)}</p>
                <ul class="preset-bullets" data-lang="de">{bullets_de}</ul>
                <ul class="preset-bullets" data-lang="en" style="display:none">{bullets_en}</ul>
            </div>
            <div class="preset-card-footer">
                <a href="{pid}/de/" class="preset-cta" data-lang="de">Richtlinie ansehen &rarr;</a>
                <a href="{pid}/en/" class="preset-cta" data-lang="en" style="display:none">View policy &rarr;</a>
            </div>
        </div>
'''

    page_html = f'''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KI-Policy Presets \u2013 \u00dcbersicht</title>
    <meta name="description" content="Standardisierte KI-Richtlinien f\u00fcr Hochschullehre \u2013 von AI-None bis AI-Skill.">
    <meta property="og:title" content="KI-Policy Presets">
    <meta property="og:description" content="Standardisierte KI-Richtlinien f\u00fcr Hochschullehre \u2013 6 Presets von No-AI bis KI-Kompetenz als Lernziel.">
    <style>
        @font-face {{
            font-family: 'Roboto';
            font-weight: 300;
            font-style: normal;
            src: url('/v3/fonts/Roboto-300.woff2') format('woff2');
        }}
        @font-face {{
            font-family: 'Roboto';
            font-weight: 400;
            font-style: normal;
            src: url('/v3/fonts/Roboto-400.woff2') format('woff2');
        }}
        @font-face {{
            font-family: 'Roboto';
            font-weight: 500;
            font-style: normal;
            src: url('/v3/fonts/Roboto-500.woff2') format('woff2');
        }}
        @font-face {{
            font-family: 'Roboto';
            font-weight: 700;
            font-style: normal;
            src: url('/v3/fonts/Roboto-700.woff2') format('woff2');
        }}

        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 16px;
            line-height: 1.6;
            color: #333;
            background: #fff;
        }}

        /* Branding Bar */
        .uni-branding-bar {{
            background-color: #3D3C3B;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.7rem 1.5rem;
        }}
        .uni-branding-bar a {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            text-decoration: none;
            color: white;
            font-size: 0.85rem;
            font-weight: 400;
            transition: opacity 0.2s ease;
        }}
        .uni-branding-bar a:hover {{ opacity: 0.85; }}
        .uni-branding-logo {{ height: 26px; width: auto; }}
        .uni-branding-right {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .uni-branding-right a {{
            color: rgba(255,255,255,0.75);
            font-size: 0.8rem;
        }}
        .uni-branding-right a:hover {{ color: white; }}
        .uni-branding-separator {{ color: rgba(255,255,255,0.3); font-size: 0.75rem; }}

        /* Page Header */
        .page-header {{
            background: none;
            border-bottom: none;
            padding: 2rem 1.5rem 1.5rem;
            text-align: center;
        }}
        .page-header h1 {{
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 0.3rem;
        }}
        .page-header .subtitle {{
            color: #666;
            max-width: 600px;
            margin: 0 auto 0.8rem;
        }}
        .lang-toggle {{
            display: inline-flex;
            border: 1px solid #ddd;
            border-radius: 4px;
            overflow: hidden;
            font-size: 0.85rem;
        }}
        .lang-toggle button {{
            padding: 0.3rem 0.7rem;
            border: none;
            background: #fff;
            color: #555;
            cursor: pointer;
            font-family: inherit;
            font-size: inherit;
            transition: background 0.15s;
        }}
        .lang-toggle button:not(:last-child) {{
            border-right: 1px solid #ddd;
        }}
        .lang-toggle button:hover {{ background: #f0f0f0; }}
        .lang-toggle button.active {{
            background: #333;
            color: #fff;
        }}

        /* Main content area */
        .page-main {{
            max-width: 960px;
            margin: 0 auto;
            padding: 0 1rem;
        }}

        /* Section styling */
        .content-section {{
            background: none;
            border-radius: 0;
            box-shadow: none;
            margin-top: 2.5rem;
            padding: 0;
        }}
        .content-section + .content-section {{
            border-top: 1px solid #e0e0e0;
            padding-top: 2.5rem;
        }}
        .section-title {{
            font-size: 1.05rem;
            font-weight: 400;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: #555;
            margin-bottom: 1.2rem;
            display: block;
        }}
        .section-icon {{
            font-size: 1.3rem;
        }}

        /* Decision Tree */
        .decision-tree {{ }}
        .dt-step {{
            display: none;
            animation: dtFadeIn 0.25s ease;
        }}
        .dt-step.dt-active {{
            display: block;
        }}
        @keyframes dtFadeIn {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .dt-question {{
            font-size: 1rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 0.3rem;
        }}
        .dt-hint {{
            font-size: 0.85rem;
            color: #888;
            margin-bottom: 0.6rem;
        }}
        .dt-options {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }}
        .dt-option {{
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
            font-family: inherit;
            border: 1px solid #ddd;
            border-radius: 0;
            background: #fff;
            color: #333;
            cursor: pointer;
            transition: background 0.15s, border-color 0.15s;
        }}
        .dt-option:hover {{
            background: #f8f8f8;
            border-color: #999;
        }}
        .dt-option.dt-selected {{
            background: #333;
            color: #fff;
            border-color: #333;
        }}
        .dt-dot {{
            display: none;
        }}
        .dt-result.dt-active {{
            display: block;
            background: #fff;
            border: 1px solid #ddd;
            border-top: 3px solid var(--preset-color, #999);
            border-radius: 6px;
            margin-top: 0.6rem;
            overflow: hidden;
        }}
        .dt-result-head {{
            padding: 1.4rem 1.5rem 1.2rem;
        }}
        .dt-result-badge {{
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 0.4rem;
        }}
        .dt-result-desc {{
            font-size: 0.92rem;
            font-style: italic;
            color: #666;
            line-height: 1.5;
        }}
        .dt-view-preset {{
            display: block;
            padding: 1rem 1.5rem;
            font-size: 0.9rem;
            font-weight: 500;
            background: none;
            color: #333;
            text-decoration: none;
            border-top: 1px solid #eee;
            transition: background 0.15s;
        }}
        .dt-view-preset:hover {{ background: #f8f8f6; }}
        .dt-back {{
            margin-top: 0.8rem;
            padding: 0;
            font-size: 0.82rem;
            font-family: inherit;
            border: none;
            background: none;
            color: #666;
            cursor: pointer;
            text-decoration: underline;
            text-underline-offset: 2px;
        }}
        .dt-back:hover {{ color: #333; }}
        .dt-restart {{
            margin-top: 1rem;
            padding: 0;
            font-size: 0.85rem;
            font-family: inherit;
            border: none;
            background: none;
            color: #666;
            cursor: pointer;
            text-decoration: underline;
            text-underline-offset: 2px;
        }}
        .dt-restart:hover {{ color: #333; }}
        .dt-props {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0;
            background: #fafaf8;
            border-top: 1px solid #eee;
            border-bottom: 1px solid #eee;
        }}
        .dt-prop {{
            padding: 0.8rem 1.2rem;
        }}
        .dt-prop + .dt-prop {{
            border-left: 1px solid #eee;
        }}
        .dt-prop-label {{
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #999;
            margin-bottom: 0.3rem;
        }}
        .dt-prop-value {{
            font-size: 0.88rem;
            color: #333;
            line-height: 1.4;
        }}
        .dt-prop-value.c-yes {{ color: #2e7d32; }}
        .dt-prop-value.c-no  {{ color: #aaa; }}
        .dt-breadcrumb {{
            display: none;
            flex-wrap: wrap;
            gap: 0.3rem;
            margin-bottom: 0.8rem;
            font-size: 0.8rem;
            color: #888;
        }}
        .dt-breadcrumb-item {{
            background: none;
            border: none;
            padding: 0.1rem 0;
        }}
        .dt-bc-answer {{
            font-weight: 600;
            color: #333;
        }}

        /* Comparison Table — Tufte style */
        .comparison-table-wrap {{
            overflow-x: auto;
        }}
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }}
        .comparison-table thead {{
            border-top: 2px solid #333;
            border-bottom: 1px solid #333;
        }}
        .comparison-table tbody {{
            border-bottom: 1px solid #333;
        }}
        .comparison-table th,
        .comparison-table td {{
            padding: 8px 12px;
            text-align: left;
            border-bottom: none;
        }}
        .comparison-table tbody tr:nth-child(even) {{
            background: #fafafa;
        }}
        .comparison-table th {{
            font-weight: 600;
            font-size: 0.8rem;
            color: #555;
            background: none;
            position: sticky;
            top: 0;
        }}
        .comparison-table .row-label {{
            text-align: left;
            font-weight: 500;
            white-space: normal;
            min-width: 100px;
        }}
        .comparison-table .row-label a {{
            color: #333;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .comparison-table .row-label a:hover {{ text-decoration: underline; }}
        .ct-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            flex-shrink: 0;
        }}
        .comparison-table .c-yes {{
            color: #2e7d32;
            font-weight: 400;
        }}
        .comparison-table .c-no {{
            color: #bbb;
        }}
        .comparison-hint {{
            text-align: left;
            font-size: 0.8rem;
            font-style: italic;
            color: #999;
            margin-top: 8px;
        }}

        /* Preset Cards Grid */
        .presets-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.2rem;
        }}
        .preset-card {{
            background: #fff;
            border-radius: 0;
            overflow: hidden;
            border: 1px solid #ddd;
            border-top: none;
            display: flex;
            flex-direction: column;
        }}
        .preset-card-header {{
            padding: 0.7rem 1rem;
        }}
        .preset-name {{
            font-size: 1rem;
            font-weight: 700;
            margin: 0;
        }}
        .preset-card-body {{
            padding: 0.6rem 1rem 0.4rem;
            flex: 1;
        }}
        .preset-desc {{
            font-size: 0.85rem;
            color: #555;
            margin: 0 0 0.4rem;
        }}
        .preset-bullets {{
            list-style: none;
            padding-left: 0;
            font-size: 0.82rem;
            color: #444;
            margin: 0;
        }}
        .preset-bullets li {{
            margin-bottom: 0.15rem;
            padding-left: 1.2em;
            text-indent: -1.2em;
        }}
        .preset-bullets li::before {{
            content: '\\2013\\00a0';
        }}
        .preset-card-footer {{
            padding: 0.6rem 1rem;
            border-top: none;
        }}
        .preset-cta {{
            display: block;
            text-align: left;
            padding: 0;
            font-size: 0.85rem;
            font-weight: 500;
            color: #333;
            text-decoration: none;
        }}
        .preset-cta:hover {{
            text-decoration: underline;
            text-underline-offset: 2px;
        }}

        /* Upload toggle above cards */
        .upload-toggle-bar {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 1rem;
            padding: 0;
            background: none;
            border-radius: 0;
            font-size: 0.85rem;
        }}
        .upload-toggle-bar label {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            cursor: pointer;
            font-weight: 500;
            white-space: nowrap;
        }}
        .upload-toggle-bar input[type="checkbox"] {{
            width: 16px;
            height: 16px;
            accent-color: #1a73e8;
        }}
        .upload-toggle-desc {{
            color: #777;
            font-size: 0.82rem;
        }}

        /* Info boxes */
        .info-boxes-grid {{
            display: flex;
            flex-direction: row;
            gap: 1.5rem;
        }}
        .info-boxes-grid > div {{
            display: flex;
            flex-direction: row;
            flex-wrap: wrap;
            gap: 1.5rem;
            width: 100%;
        }}
        .welcome-secondary-box {{
            flex: 1 1 0;
            min-width: calc(50% - 0.75rem);
            background: #fff;
            border-radius: 8px;
            padding: 1.2rem 1.4rem;
            border: 1px solid #e0e0e0;
            font-size: 0.9rem;
            overflow: hidden;
        }}
        .welcome-secondary-box h2 {{
            font-size: 1.05rem;
            margin: 0 0 0.7rem 0;
            padding: 0 0 0.7rem 0;
        }}
        .welcome-secondary-box ul {{
            list-style: none;
            padding-left: 0;
        }}
        .welcome-secondary-box li {{
            line-height: 1.4;
            margin-bottom: 0.7rem;
            padding-bottom: 0.7rem;
            position: relative;
        }}
        .welcome-secondary-box li:last-child {{
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }}
        .welcome-secondary-box p {{
            line-height: 1.5;
            margin-bottom: 0.6rem;
        }}
        /* Disclaimer box */
        .disclaimer-box {{
            background-color: #fefcf5;
        }}
        .disclaimer-box h2 {{
            color: #ab8b36;
            border-bottom: 1px solid #e8e0cc;
        }}
        .disclaimer-box p,
        .disclaimer-box li {{
            color: #8a6d3b;
        }}
        .disclaimer-box li {{
            border-bottom: 1px dotted rgba(138, 109, 59, 0.15);
        }}
        /* Technical notes box */
        .technical-notes {{
            background-color: #f7f9fa;
            border-color: #e2e8ed;
        }}
        .technical-notes h2 {{
            color: #456789;
            border-bottom: 1px solid #e2e8ed;
        }}
        .technical-notes li {{
            color: #555;
            border-bottom: 1px dotted rgba(100, 100, 100, 0.15);
        }}
        .disclaimer-box a {{
            color: #8b6914;
            text-decoration-color: rgba(139, 105, 20, 0.3);
        }}
        .disclaimer-box a:hover {{
            color: #6b5100;
            text-decoration-color: currentColor;
        }}
        .technical-notes a {{
            color: #456789;
            text-decoration-color: rgba(69, 103, 137, 0.3);
        }}
        .technical-notes a:hover {{
            color: #2a4d6e;
            text-decoration-color: currentColor;
        }}
        /* Related tools box */
        .related-tools-box {{
            background-color: #f5faf8;
        }}
        .related-tools-box h2 {{
            color: #2e7d5b;
            border-bottom: 1px solid #c8e0d5;
        }}
        .related-tools-box p,
        .related-tools-box li {{
            color: #3d6b56;
        }}
        .related-tools-box li {{
            border-bottom: 1px dotted rgba(46, 125, 91, 0.15);
        }}
        .related-tools-box a {{
            color: #2e7d5b;
        }}
        @media (max-width: 768px) {{
            .info-boxes-grid,
            .info-boxes-grid > div {{
                flex-direction: column;
            }}
        }}

        /* Site footer */
        .site-footer {{
            max-width: 960px;
            margin: 3rem auto 0;
            padding: 2rem 1rem 2rem;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            font-size: 0.85rem;
            color: #666;
        }}
        .site-footer h3 {{
            font-size: 0.95rem;
            margin-bottom: 8px;
            color: #333;
        }}
        .site-footer p {{
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        .site-footer a {{
            color: #555;
            text-decoration-color: rgba(85, 85, 85, 0.3);
        }}
        .site-footer a:hover {{
            color: #333;
            text-decoration-color: currentColor;
        }}
        .footer-links {{
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 12px 20px;
            margin: 12px 0;
        }}
        .footer-links a {{
            color: #333;
            text-decoration: none;
        }}
        .footer-links a:hover {{
            text-decoration: underline;
        }}
        .footer-license {{
            margin: 12px 0;
            font-size: 0.82rem;
            color: #999;
        }}
        .footer-license a {{
            color: #666;
            text-decoration: underline;
        }}
        .footer-bottom {{
            border-top: 1px solid #e0e0e0;
            padding-top: 12px;
            margin-top: 12px;
            font-size: 0.8rem;
            color: #999;
        }}
        .footer-logo {{
            margin-top: 12px;
        }}

        /* Page footer (simple) */
        .page-footer {{
            max-width: 960px;
            margin: 1.5rem auto 2rem;
            padding: 1rem;
            text-align: center;
            font-size: 0.8rem;
            color: #999;
        }}
        .page-footer a {{ color: #666; }}

        /* Mobile */
        @media (max-width: 768px) {{
            .uni-branding-bar {{ padding: 0.5rem 1rem; justify-content: center; }}
            .uni-branding-logo {{ height: 20px; }}
            .uni-branding-right {{ display: none; }}
            .page-header {{ padding: 1.5rem 1rem 1rem; }}
            .page-header h1 {{ font-size: 1.4rem; }}
            .content-section {{ margin-top: 1.5rem; }}
            .content-section + .content-section {{ padding-top: 1.5rem; }}
            .presets-grid {{ grid-template-columns: 1fr; }}
            .dt-options {{ flex-direction: column; }}
            .dt-option {{ text-align: left; }}
            .dt-result-head {{ padding: 1.1rem 1.1rem 1rem; }}
            .dt-props {{ grid-template-columns: repeat(2, 1fr); }}
            .dt-prop {{ padding: 0.65rem 0.9rem; }}
            .dt-prop:nth-child(1), .dt-prop:nth-child(2) {{ border-bottom: 1px solid #eee; }}
            .dt-view-preset {{ padding: 0.8rem 1.1rem; }}
            .comparison-table {{ font-size: 0.78rem; }}
            .comparison-table th,
            .comparison-table td {{ padding: 6px 8px; }}
        }}

        @media print {{
            .uni-branding-bar {{ display: none; }}
            .comparison-table thead {{ border-top-width: 1px; }}
            .preset-card {{ border: 1px solid #ccc; }}
        }}
    </style>
</head>
<body>
    <nav class="uni-branding-bar" aria-label="Universit\u00e4t Bamberg">
        <a href="https://www.uni-bamberg.de/" target="_blank" rel="noopener">
            <svg class="uni-branding-logo" viewBox="0 0 183 183" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><circle cx="76.6" cy="106" r="36" style="fill:none;stroke:white;stroke-width:19.84px"/><path d="M26.7,25.2C65.4,1.3 115.6,8.2 146.4,41.6C177.2,75 180.1,125.6 153.1,162.2" style="fill:none;stroke:white;stroke-width:19.84px"/><path d="M11.2,109.2C9.8,82.5 25,57.6 49.4,46.5C73.8,35.4 102.5,40.2 121.8,58.7C141.2,77.2 147.3,105.7 137.3,130.5C127.3,155.4 103.1,171.6 76.3,171.5" style="fill:none;stroke:white;stroke-width:19.84px"/></svg>
            <span>Universit\u00e4t Bamberg</span>
        </a>
        <div class="uni-branding-right">
            <a href="https://psi.uni-bamberg.de/de/ueberuns/" target="_blank" rel="noopener">Prof. Dr. Dominik Herrmann</a>
            <span class="uni-branding-separator">|</span>
            <a href="https://www.uni-bamberg.de/cio/" target="_blank" rel="noopener" data-lang="de">Sprecher des CIO</a>
            <a href="https://www.uni-bamberg.de/cio/" target="_blank" rel="noopener" data-lang="en" style="display:none">CIO Speaker</a>
        </div>
    </nav>

    <header class="page-header">
        <h1 data-lang="de">KI-Policy Presets</h1>
        <h1 data-lang="en" style="display:none">AI Policy Presets</h1>
        <p class="subtitle" data-lang="de">Standardisierte KI-Richtlinien f\u00fcr die Hochschullehre \u2013 von <em>kein KI-Einsatz</em> bis <em>KI-Kompetenz als Lernziel</em>.</p>
        <p class="subtitle" data-lang="en" style="display:none">Standardized AI policies for higher education \u2013 from <em>no AI use</em> to <em>AI competence as learning objective</em>.</p>
        <div style="margin-top: 0.6rem; display: flex; align-items: center; justify-content: center; gap: 1rem;">
            <div class="lang-toggle" role="group" aria-label="Language">
                <button data-lang-btn="de" class="active">DE</button>
                <button data-lang-btn="en">EN</button>
            </div>
            <a href="/v3/" style="color: #333; text-decoration: none; font-size: 0.9rem; border-bottom: 1px solid #999;" data-lang="de">KI-Policy-Generator &rarr;</a>
            <a href="/v3/" style="color: #333; text-decoration: none; font-size: 0.9rem; border-bottom: 1px solid #999; display:none" data-lang="en">AI Policy Generator &rarr;</a>
        </div>
    </header>

    <div class="page-main">
        <!-- Decision Tree Section -->
        <section class="content-section" id="decision-tree-section">
            <h2 class="section-title" data-lang="de">Entscheidungshilfe</h2>
            <h2 class="section-title" data-lang="en" style="display:none">Decision guide</h2>
            <div id="dt-container">
{dt_de}
{dt_en}
                <button class="dt-restart" id="dt-restart" style="display:none"><span data-lang="de">Neu starten</span><span data-lang="en" style="display:none">Start over</span></button>
            </div>
        </section>

        <!-- Comparison Table Section -->
        <section class="content-section" id="comparison-section">
            <h2 class="section-title" data-lang="de">Vergleich</h2>
            <h2 class="section-title" data-lang="en" style="display:none">Comparison</h2>
{ct_de}
{ct_en}
        </section>

        <!-- Preset Cards Section -->
        <section class="content-section" id="presets-section">
            <h2 class="section-title" data-lang="de">Presets</h2>
            <h2 class="section-title" data-lang="en" style="display:none">Presets</h2>
            <div class="upload-toggle-bar">
                <label>
                    <input type="checkbox" id="upload-toggle">
                    <span data-lang="de">Upload-Variante</span>
                    <span data-lang="en" style="display:none">Upload variant</span>
                </label>
                <span class="upload-toggle-desc" data-lang="de">Erlaubt Studierenden, gekennzeichnete Kursmaterialien in KI-Tools hochzuladen.</span>
                <span class="upload-toggle-desc" data-lang="en" style="display:none">Allows students to upload marked course materials to AI tools.</span>
            </div>
            <div class="presets-grid">
{cards_html}
            </div>
        </section>

        <!-- Info Boxes Section -->
        <section class="content-section" id="info-section">
            <h2 class="section-title" data-lang="de">Hinweise</h2>
            <h2 class="section-title" data-lang="en" style="display:none">Notes</h2>
            <div class="info-boxes-grid">
{info_boxes_html}
            </div>
        </section>
    </div>

    <footer class="site-footer">
        <div data-lang="de">
            <div class="footer-section">
                <h3>&Uuml;ber diesen Generator</h3>
                <p>Dieser KI-Policy-Generator wird vom <a href="https://www.uni-bamberg.de/cio/" target="_blank">Chief Information Office der Universit&auml;t Bamberg</a> betrieben und im Rahmen des Projekts <a href="https://projekt-bakule.de/" target="_blank">BaKuLe</a> entwickelt. BaKuLe ist ein Hochschulentwicklungsprojekt der Universit&auml;t Bamberg, gef&ouml;rdert durch die <a href="https://stiftung-hochschullehre.de/" target="_blank">Stiftung Innovation in der Hochschullehre</a>.</p>
                <p>Bei der Entwicklung der Texte und des Generators kam Generative KI zum Einsatz.</p>
                <p class="footer-logo"><a href="https://stiftung-hochschullehre.de/" target="_blank"><img src="/v3/images/logo-stil.svg" alt="Stiftung Innovation in der Hochschullehre" height="40"></a></p>
            </div>
            <div class="footer-links">
                <a href="https://www.uni-bamberg.de/cio/ki/" target="_blank">Weiterf&uuml;hrende Informationen</a>
                <a href="https://github.com/UBA-PSI/ki-policy-generator" target="_blank">GitHub</a>
                <a href="https://www.uni-bamberg.de/cio/kontaktnavigation/impressum/" target="_blank">Impressum</a>
                <a href="https://www.uni-bamberg.de/its/verfahrensweisen/datenschutz/datenschutzerklaerungen/webauftritt/" target="_blank">Datenschutz</a>
            </div>
            <div class="footer-license">
                <p>Inhalte lizenziert unter <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.de" target="_blank">CC BY-SA 4.0</a>, Code unter <a href="https://opensource.org/licenses/MIT" target="_blank">MIT-Lizenz</a></p>
            </div>
            <div class="footer-bottom">
                <p>Der KI-Policy-Generator l&auml;uft vollst&auml;ndig clientseitig. Die Inhalte, die Sie eingeben, werden nicht an den Server gesendet.</p>
            </div>
        </div>
        <div data-lang="en" style="display:none">
            <div class="footer-section">
                <h3>About this Generator</h3>
                <p>This AI Policy Generator is operated by the <a href="https://www.uni-bamberg.de/cio/" target="_blank">Chief Information Office of the University of Bamberg</a> and developed as part of the <a href="https://projekt-bakule.de/" target="_blank">BaKuLe</a> project. BaKuLe is a higher education development project at the University of Bamberg, funded by the <a href="https://stiftung-hochschullehre.de/" target="_blank">Foundation for Innovation in Higher Education Teaching</a>.</p>
                <p>Generative AI was used in the development of the texts and the generator.</p>
                <p class="footer-logo"><a href="https://stiftung-hochschullehre.de/" target="_blank"><img src="/v3/images/logo-stil.svg" alt="Foundation for Innovation in Higher Education Teaching" height="40"></a></p>
            </div>
            <div class="footer-links">
                <a href="https://www.uni-bamberg.de/cio/ki/" target="_blank">More Information</a>
                <a href="https://github.com/UBA-PSI/ki-policy-generator" target="_blank">GitHub</a>
                <a href="https://www.uni-bamberg.de/cio/kontaktnavigation/impressum/" target="_blank">Legal Notice</a>
                <a href="https://www.uni-bamberg.de/its/verfahrensweisen/datenschutz/datenschutzerklaerungen/webauftritt/" target="_blank">Privacy Policy</a>
            </div>
            <div class="footer-license">
                <p>Content licensed under <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.en" target="_blank">CC BY-SA 4.0</a>, code under <a href="https://opensource.org/licenses/MIT" target="_blank">MIT License</a></p>
            </div>
            <div class="footer-bottom">
                <p>The AI Policy Generator runs entirely client-side. The content you enter is not sent to the server.</p>
            </div>
        </div>
    </footer>

    <script>
        (function() {{
            var currentLang = 'de';
            var uploadOn = false;
            var langBtns = document.querySelectorAll('[data-lang-btn]');
            var uploadToggle = document.getElementById('upload-toggle');

            // --- Language toggle ---
            function setLang(lang) {{
                currentLang = lang;
                langBtns.forEach(function(btn) {{
                    btn.classList.toggle('active', btn.dataset.langBtn === lang);
                }});
                document.querySelectorAll('[data-lang]').forEach(function(el) {{
                    el.style.display = el.dataset.lang === lang ? '' : 'none';
                }});
                document.documentElement.lang = lang;
                updateCardLinks();
            }}

            langBtns.forEach(function(btn) {{
                btn.addEventListener('click', function() {{
                    setLang(btn.dataset.langBtn);
                }});
            }});

            // --- Upload toggle ---
            function updateCardLinks() {{
                document.querySelectorAll('.preset-card').forEach(function(card) {{
                    var pid = card.dataset.preset;
                    var suffix = uploadOn ? '/upload/' : '/';
                    card.querySelectorAll('.preset-cta').forEach(function(a) {{
                        if (a.style.display !== 'none') {{
                            a.href = pid + '/' + currentLang + suffix;
                        }}
                    }});
                    // Update hidden lang link too for when lang switches
                    card.querySelectorAll('.preset-cta').forEach(function(a) {{
                        var linkLang = a.dataset.lang;
                        if (linkLang) a.href = pid + '/' + linkLang + suffix;
                    }});
                }});
            }}

            if (uploadToggle) {{
                uploadToggle.addEventListener('change', function() {{
                    uploadOn = this.checked;
                    updateCardLinks();
                }});
            }}

            // --- Decision tree logic ---
            document.querySelectorAll('.decision-tree').forEach(function(tree) {{
                var steps = tree.querySelectorAll('.dt-step');
                var restartBtn = document.getElementById('dt-restart');
                var history = [];

                function showStep(stepId) {{
                    steps.forEach(function(s) {{ s.classList.remove('dt-active'); }});
                    var target = tree.querySelector('[data-step="' + stepId + '"]');
                    if (target) {{
                        target.classList.add('dt-active');
                        if (target.classList.contains('dt-result') && restartBtn) {{
                            restartBtn.style.display = '';
                        }}
                    }}
                    // Breadcrumb
                    var bc = tree.querySelector('.dt-breadcrumb');
                    if (!bc) {{
                        bc = document.createElement('div');
                        bc.className = 'dt-breadcrumb';
                        tree.prepend(bc);
                    }}
                    while (bc.firstChild) bc.removeChild(bc.firstChild);
                    history.forEach(function(h) {{
                        var item = document.createElement('span');
                        item.className = 'dt-breadcrumb-item';
                        item.textContent = h.q + ' \u2192 ';
                        var ans = document.createElement('span');
                        ans.className = 'dt-bc-answer';
                        ans.textContent = h.a;
                        item.appendChild(ans);
                        bc.appendChild(item);
                    }});
                    bc.style.display = history.length === 0 ? 'none' : 'flex';
                }}

                function goBack() {{
                    if (history.length === 0) return;
                    var prev = history.pop();
                    // Find the step to go back to
                    var targetStep = prev.stepId;
                    steps.forEach(function(s) {{ s.classList.remove('dt-active'); }});
                    var target = tree.querySelector('[data-step="' + targetStep + '"]');
                    if (target) {{
                        // Clear selection on that step
                        target.querySelectorAll('.dt-option').forEach(function(b) {{ b.classList.remove('dt-selected'); }});
                        target.classList.add('dt-active');
                    }}
                    if (restartBtn) restartBtn.style.display = 'none';
                    // Update breadcrumb
                    var bc = tree.querySelector('.dt-breadcrumb');
                    if (bc) {{
                        while (bc.firstChild) bc.removeChild(bc.firstChild);
                        history.forEach(function(h) {{
                            var item = document.createElement('span');
                            item.className = 'dt-breadcrumb-item';
                            item.textContent = h.q + ' \u2192 ';
                            var ans = document.createElement('span');
                            ans.className = 'dt-bc-answer';
                            ans.textContent = h.a;
                            item.appendChild(ans);
                            bc.appendChild(item);
                        }});
                        bc.style.display = history.length === 0 ? 'none' : 'flex';
                    }}
                }}

                tree.addEventListener('click', function(e) {{
                    // Option click — advance
                    var opt = e.target.closest('.dt-option');
                    if (opt) {{
                        var currentStep = opt.closest('.dt-step');
                        var stepId = currentStep.dataset.step;
                        var questionEl = currentStep.querySelector('.dt-question');
                        history.push({{ stepId: stepId, q: questionEl.textContent.substring(0, 30) + '\u2026', a: opt.textContent }});
                        currentStep.querySelectorAll('.dt-option').forEach(function(b) {{ b.classList.remove('dt-selected'); }});
                        opt.classList.add('dt-selected');
                        showStep(opt.dataset.next);
                        return;
                    }}
                    // Back button click
                    var backBtn = e.target.closest('.dt-back');
                    if (backBtn) {{
                        goBack();
                        return;
                    }}
                }});

                if (restartBtn) {{
                    restartBtn.addEventListener('click', function() {{
                        history.length = 0;
                        steps.forEach(function(s) {{ s.classList.remove('dt-active'); }});
                        tree.querySelector('[data-step="q1"]').classList.add('dt-active');
                        restartBtn.style.display = 'none';
                        var bc = tree.querySelector('.dt-breadcrumb');
                        if (bc) {{ while (bc.firstChild) bc.removeChild(bc.firstChild); bc.style.display = 'none'; }}
                    }});
                }}
            }});
        }})();
    </script>
</body>
</html>'''

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page_html)

    print(f'Generated {os.path.join(output_dir, "index.html")}')


if __name__ == '__main__':
    main()
