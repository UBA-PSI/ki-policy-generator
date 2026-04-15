#!/usr/bin/env python3
"""
Generate static HTML pages for all presets.

Reads the YAML data files and generates one HTML page per preset/language/upload
combination, mirroring the live preview from the generator.

Usage:
    python3 scripts/generate-preset-pages.py
    python3 scripts/generate-preset-pages.py --output /var/www/ki-policy.org/v3/p
"""

import argparse
import html
import os
import re
import sys

import yaml


# ---------------------------------------------------------------------------
# Markdown parser (port of parseMarkdown from index.html)
# ---------------------------------------------------------------------------

def escape_html(text):
    """Escape HTML entities to prevent XSS."""
    if not text:
        return ''
    return html.escape(text, quote=True)


def parse_markdown(text):
    """Convert simple Markdown to HTML, matching the JS parseMarkdown."""
    if not text:
        return ''

    text = escape_html(text)

    # Bold: **text** -> <strong>text</strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    # Italic: *text* -> <em>text</em>
    text = re.sub(r'\*([^*]+?)\*', r'<em>\1</em>', text)

    # URLs: http(s)://... -> <a href="...">...</a>
    text = re.sub(
        r'(?<!href=["\'])(https?://[^\s<]+)',
        r'<a href="\1" target="_blank">\1</a>',
        text,
    )

    # Bullet lists (lines starting with - or *)
    def replace_bullet_list(m):
        block = m.group(0)
        items = []
        for line in block.split('\n'):
            line_stripped = line.strip()
            if re.match(r'^[-*]\s+', line_stripped):
                content = re.sub(r'^[-*]\s+', '', line_stripped)
                items.append(f'<li>{content}</li>')
        if items:
            return '<ul>\n' + '\n'.join(items) + '\n</ul>'
        return block

    text = re.sub(r'(?:^|\n)((?:[-*]\s+.+(?:\n|$))+)', replace_bullet_list, text)

    # Numbered lists (lines starting with 1., 2., etc)
    def replace_numbered_list(m):
        block = m.group(0)
        items = []
        for line in block.split('\n'):
            line_stripped = line.strip()
            if re.match(r'^\d+\.\s+', line_stripped):
                content = re.sub(r'^\d+\.\s+', '', line_stripped)
                items.append(f'<li>{content}</li>')
        if items:
            return '<ol>\n' + '\n'.join(items) + '\n</ol>'
        return block

    text = re.sub(r'(?:^|\n)((?:\d+\.\s+.+(?:\n|$))+)', replace_numbered_list, text)

    # Bullet character lists (•)
    if '•' in text:
        def replace_bullet_char_list(m):
            block = m.group(0)
            lines = block.split('\n')
            heading = ''
            if lines and not lines[0].strip().startswith('•'):
                heading = lines.pop(0)
            items = []
            for line in lines:
                if line.strip().startswith('•'):
                    content = re.sub(r'^•\s+', '', line.strip())
                    if content:
                        items.append(f'<li>{content}</li>')
            if items:
                result = heading + '\n<ul>\n' if heading else '<ul>\n'
                result += '\n'.join(items) + '\n</ul>'
                return result
            return block

        text = re.sub(r'(?:^|\n)?(.+\n(?:•\s+.+(?:\n|$))+)', replace_bullet_char_list, text)

    # Paragraphs
    text = '<p>' + re.sub(r'\n\n+', '</p>\n\n<p>', text) + '</p>'

    # Fix lists wrapped in paragraphs
    text = re.sub(r'<p><([ou]l)>', r'<\1>', text)
    text = re.sub(r'</([ou]l)></p>', r'</\1>', text)
    text = re.sub(r'<li><p>(.*?)</p></li>', r'<li>\1</li>', text)

    return text


def parse_markdown_inline(text):
    """Parse markdown but strip outer <p> tags (for inline use like TL;DR bullets)."""
    result = parse_markdown(text)
    return re.sub(r'</?p>', '', result)


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------

def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Build item lookup map from policy-data
# ---------------------------------------------------------------------------

def build_item_map(policy_data):
    """Build {item_id: {text, category_title, subcategory_title, category_id, subcategory_id}} map."""
    item_map = {}
    for cat in policy_data.get('categories', []):
        cat_title = cat.get('title', '')
        cat_id = cat.get('id', '')
        for sub in cat.get('subcategories', []):
            sub_title = sub.get('title', '')
            sub_id = sub.get('id', '')
            for item in sub.get('items', []):
                item_id = item.get('id', '')
                item_map[item_id] = {
                    'text': item.get('text', '').strip(),
                    'category_title': cat_title,
                    'subcategory_title': sub_title,
                    'category_id': cat_id,
                    'subcategory_id': sub_id,
                }
    return item_map


# ---------------------------------------------------------------------------
# Resolve preset items
# ---------------------------------------------------------------------------

def resolve_preset_items(preset, item_map, upload):
    """Resolve items for a preset, returning list of {id, text, category_title, subcategory_title}."""
    resolved = []

    for item_ref in preset.get('items', []):
        if isinstance(item_ref, str):
            # String reference -> look up in policy-data
            if item_ref in item_map:
                info = item_map[item_ref]
                resolved.append({
                    'id': item_ref,
                    'text': info['text'],
                    'category_title': info['category_title'],
                    'subcategory_title': info['subcategory_title'],
                })
        elif isinstance(item_ref, dict):
            # Object {id, text} -> custom text, but look up category from policy-data
            item_id = item_ref.get('id', '')
            custom_text = item_ref.get('text', '').strip()
            if item_id in item_map:
                info = item_map[item_id]
                resolved.append({
                    'id': item_id,
                    'text': custom_text,
                    'category_title': info['category_title'],
                    'subcategory_title': info['subcategory_title'],
                })
            else:
                resolved.append({
                    'id': item_id,
                    'text': custom_text,
                    'category_title': '',
                    'subcategory_title': '',
                })

    # Add upload/no_upload item
    upload_item = preset.get('upload_item') if upload else preset.get('no_upload_item')
    if upload_item:
        if isinstance(upload_item, str):
            if upload_item in item_map:
                info = item_map[upload_item]
                resolved.append({
                    'id': upload_item,
                    'text': info['text'],
                    'category_title': info['category_title'],
                    'subcategory_title': info['subcategory_title'],
                })
        elif isinstance(upload_item, dict):
            item_id = upload_item.get('id', '')
            custom_text = upload_item.get('text', '').strip()
            if item_id in item_map:
                info = item_map[item_id]
                resolved.append({
                    'id': item_id,
                    'text': custom_text,
                    'category_title': info['category_title'],
                    'subcategory_title': info['subcategory_title'],
                })
            else:
                resolved.append({
                    'id': item_id,
                    'text': custom_text,
                    'category_title': '',
                    'subcategory_title': '',
                })

    return resolved


# ---------------------------------------------------------------------------
# Group items by category / subcategory (preserving order)
# ---------------------------------------------------------------------------

def group_items_by_category(items):
    """Group items into ordered categories/subcategories, preserving item order."""
    from collections import OrderedDict
    categories = OrderedDict()
    for item in items:
        cat = item['category_title'] or 'Unkategorisiert'
        sub = item['subcategory_title'] or 'Allgemein'
        if cat not in categories:
            categories[cat] = OrderedDict()
        if sub not in categories[cat]:
            categories[cat][sub] = []
        categories[cat][sub].append(item)
    return categories


# ---------------------------------------------------------------------------
# Generate policy HTML content
# ---------------------------------------------------------------------------

def generate_policy_content(preset, items_grouped, upload, lang, ui_strings):
    """Generate the inner policy HTML content."""
    date_label = ui_strings.get('date_label', 'Stand')
    preset_color = preset.get('color', '#666')

    parts = []

    # Title
    doc_title = escape_html(preset.get('document_title', ''))
    parts.append(f'<h1>{doc_title}</h1>')

    # Date
    parts.append(f'<div class="policy-date">{escape_html(date_label)}: <span id="policy-date"></span></div>')

    # Intro
    intro_text = preset.get('document_intro', '').strip()
    parts.append(f'<div class="policy-intro">{parse_markdown(intro_text)}</div>')

    # TL;DR section
    tldr_title = ui_strings.get('preset_tldr_title', 'Zusammenfassung (TL;DR)')
    upload_suffix = '-Upload' if upload else '-NoUpload'
    display_name = preset.get('name', '') + upload_suffix
    upload_bullet = preset.get('tldr_upload') if upload else preset.get('tldr_no_upload')
    all_bullets = list(preset.get('tldr', [])) + ([upload_bullet] if upload_bullet else [])

    parts.append('<div class="policy-tldr-section">')
    parts.append(f'<h2>{escape_html(display_name)} – {escape_html(tldr_title)}</h2>')
    parts.append('<ul>')
    for bullet in all_bullets:
        parts.append(f'<li>{parse_markdown_inline(bullet)}</li>')
    parts.append('</ul></div>')

    # Subcategory titles that get visual highlighting
    highlight_titles = {'Prüfungsgrundsätze und KI-Nutzung', 'Examination Principles and AI Use'}

    # Policy content by category / subcategory
    parts.append('<div class="policy-content">')
    for cat_title, subcategories in items_grouped.items():
        clean_cat = re.sub(r'^\d+\.\s*', '', cat_title)
        parts.append(f'<div class="policy-category"><h2 class="category-title">{escape_html(clean_cat)}</h2>')
        for sub_title, items in subcategories.items():
            is_highlight = sub_title in highlight_titles
            sub_class = 'policy-subcategory policy-distinguishing-section' if is_highlight else 'policy-subcategory'
            style_attr = f' style="border-top-color: {preset_color}; background: color-mix(in oklch, {preset_color} 6%, white);"' if is_highlight else ''
            parts.append(f'<div class="{sub_class}"{style_attr}><h3 class="subcategory-title">{escape_html(sub_title)}</h3>')
            for item in items:
                content = parse_markdown(item['text'])
                parts.append(f'<div class="policy-item-result"><div class="policy-item-text">{content}</div></div>')
            parts.append('</div>')
        parts.append('</div>')
    parts.append('</div>')

    # Policy card
    upload_label = ui_strings.get('preset_upload_label', 'Upload erlaubt') if upload else ui_strings.get('preset_no_upload_label', 'Kein Upload')
    card_footer = ui_strings.get('preset_card_footer', 'Erstellt mit dem KI-Policy-Generator')

    parts.append('<div class="policy-card">')
    parts.append('<div class="policy-card-header">')
    parts.append(f'<span class="policy-card-dot" style="background-color: {preset.get("color", "#666")}"></span>')
    parts.append(f'<span class="policy-card-title">{escape_html(display_name)}</span>')
    parts.append(f'<span class="policy-card-upload-badge">{escape_html(upload_label)}</span>')
    parts.append('</div>')
    parts.append('<ul class="policy-card-tldr">')
    for bullet in all_bullets:
        plain = re.sub(r'\*\*', '', bullet)
        parts.append(f'<li>{escape_html(plain)}</li>')
    parts.append('</ul>')
    parts.append(f'<div class="policy-card-footer">{escape_html(card_footer)}</div>')
    parts.append('</div>')

    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# Full page HTML template
# ---------------------------------------------------------------------------

def generate_full_page(preset, policy_content, upload, lang, other_lang, ui_strings, preset_id, generator_base_url):
    """Generate a complete HTML page."""
    doc_title = preset.get('document_title', '')
    description = preset.get('description', '')
    preset_name = preset.get('name', '')
    upload_suffix = '-Upload' if upload else '-NoUpload'
    display_name = preset_name + upload_suffix

    # Navigation URLs (absolute, server-rooted)
    preset_root = f'/p/{preset_id}'
    upload_seg = 'upload/' if upload else ''
    de_url = f'{preset_root}/de/{upload_seg}'
    en_url = f'{preset_root}/en/{upload_seg}'
    no_upload_url = f'{preset_root}/{lang}/'
    upload_url = f'{preset_root}/{lang}/upload/'
    presets_index_url = '/p/'

    # Generator link
    generator_url = f'{generator_base_url}?preset={preset_id}&upload={"true" if upload else "false"}&lang={lang}'

    # Canonical and alternate URLs
    base_url = f'https://ki-policy.org/p/{preset_id}'
    canonical = f'{base_url}/{lang}/' + ('upload/' if upload else '')
    alt_lang = 'en' if lang == 'de' else 'de'
    alternate = f'{base_url}/{alt_lang}/' + ('upload/' if upload else '')

    # Labels
    if lang == 'de':
        customize_label = 'Im Generator anpassen'
        upload_nav_label = 'Upload erlaubt' if upload else 'Kein Upload'
        upload_toggle_label = 'Kein Upload' if upload else 'Upload erlaubt'
        license_text = 'Inhalte lizenziert unter'
        created_with = 'Erstellt mit dem'
        generator_name = 'KI-Policy-Generator'
        cio_label = 'Sprecher des CIO'
    else:
        customize_label = 'Customize in Generator'
        upload_nav_label = 'Upload allowed' if upload else 'No upload'
        upload_toggle_label = 'No upload' if upload else 'Upload allowed'
        license_text = 'Content licensed under'
        created_with = 'Created with the'
        generator_name = 'AI Policy Generator'
        cio_label = 'CIO Speaker'

    date_locale = 'de-DE' if lang == 'de' else 'en-US'

    return f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(display_name)} – {escape_html(doc_title)}</title>
    <meta name="description" content="{escape_html(description)}">
    <meta property="og:title" content="{escape_html(display_name)} – {escape_html(doc_title)}">
    <meta property="og:description" content="{escape_html(description)}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{canonical}">
    <link rel="canonical" href="{canonical}">
    <link rel="alternate" hreflang="{alt_lang}" href="{alternate}">
    <link rel="alternate" hreflang="{lang}" href="{canonical}">
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
            background: #f5f5f5;
        }}

        /* University Branding Bar */
        .uni-branding-bar {{
            background-color: #3D3C3B;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.7rem 1.5rem;
            z-index: 200;
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
        .branding-back {{
            color: white;
            font-size: 0.85rem;
            text-decoration: none;
        }}

        /* Navigation */
        .page-nav {{
            background: #fff;
            border-bottom: 1px solid #e0e0e0;
            padding: 0.7rem 1.5rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .nav-group {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .nav-btn {{
            display: inline-block;
            padding: 0.3rem 0.7rem;
            font-size: 0.85rem;
            border-radius: 4px;
            text-decoration: none;
            color: #555;
            border: 1px solid #ddd;
            background: #fff;
            transition: background 0.15s;
            white-space: nowrap;
        }}
        .nav-btn:hover {{ background: #f0f0f0; }}
        .nav-btn.active {{
            background: #333;
            color: #fff;
            border-color: #333;
        }}
        .nav-spacer {{ flex: 1; min-width: 0; }}
        .nav-customize {{
            font-size: 0.85rem;
            color: #1a73e8;
            text-decoration: none;
            white-space: nowrap;
        }}
        .nav-customize:hover {{ text-decoration: underline; }}

        /* Main content */
        .page-content {{
            max-width: 750px;
            margin: 2rem auto;
            padding: 2rem;
            background: #fff;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            border-radius: 4px;
        }}

        /* Generated policy styles */
        .generated-policy h1 {{ font-size: 1.8rem; margin-bottom: 0.6rem; }}
        .generated-policy h2 {{ font-size: 1.4rem; margin-top: 1rem; margin-bottom: 0.4rem; }}
        .policy-date {{ color: #666; margin-bottom: 1rem; font-style: italic; }}
        .policy-intro {{ margin-bottom: 1rem; }}
        .policy-category {{ margin-bottom: 1.5rem; }}
        .policy-category h2 {{ font-size: 1.4rem; border-bottom: 1px solid #ddd; padding-bottom: 0.3rem; margin-bottom: 1rem; }}
        .policy-subcategory {{ margin-top: 1.5rem; margin-bottom: 1rem; }}
        .policy-subcategory:first-child {{ margin-top: 0.8rem; }}
        .policy-distinguishing-section {{
            border-top: 3px solid #666;
            border-radius: 6px;
            padding: 1rem 1.2rem;
            margin: 1rem 0;
        }}
        .subcategory-title {{ font-size: 1rem; font-weight: 600; color: #555; margin-bottom: 0.8rem; }}
        .policy-item-result {{ margin-bottom: 1.2rem; }}
        .policy-item-text p {{ margin-bottom: 0.3rem; }}
        .policy-item-text ul, .policy-item-text ol {{ margin-top: 0.2rem; margin-bottom: 0.3rem; padding-left: 1.5rem; }}
        .policy-item-text li {{ margin-bottom: 0.2rem; }}

        /* TL;DR section */
        .policy-tldr-section {{ background: #f9f9f9; border: 1px solid #e0e0e0; border-radius: 6px; padding: 1rem 1.2rem; margin-bottom: 1.5rem; }}
        .policy-tldr-section h2 {{ font-size: 1.1rem; margin-bottom: 0.5rem; border: none; padding: 0; }}
        .policy-tldr-section ul {{ list-style: disc; padding-left: 1.5rem; margin: 0; }}
        .policy-tldr-section li {{ margin-bottom: 0.3rem; font-size: 0.95rem; }}

        /* Policy card */
        .policy-card {{ border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; margin-top: 1.5rem; margin-bottom: 1.5rem; }}
        .policy-card-header {{ display: flex; align-items: center; gap: 0.7rem; padding: 1rem 1.2rem; border-bottom: 1px solid #e0e0e0; }}
        .policy-card-dot {{ width: 14px; height: 14px; border-radius: 50%; display: inline-block; flex-shrink: 0; }}
        .policy-card-title {{ font-size: 1.1rem; font-weight: 700; }}
        .policy-card-upload-badge {{ font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 3px; background: #f9f9f9; border: 1px solid #e0e0e0; color: #666; margin-left: auto; white-space: nowrap; }}
        .policy-card-tldr {{ list-style: none; padding: 1rem 1.2rem; margin: 0; }}
        .policy-card-tldr li {{ padding: 0.3rem 0 0.3rem 1.3em; position: relative; font-size: 0.9rem; }}
        .policy-card-tldr li::before {{ content: "\\2022"; position: absolute; left: 0; font-weight: bold; }}
        .policy-card-footer {{ padding: 0.6rem 1.2rem; border-top: 1px solid #e0e0e0; background: #f9f9f9; font-size: 0.75rem; color: #999; text-align: center; }}

        /* Footer */
        .page-footer {{
            max-width: 750px;
            margin: 2rem auto 0;
            padding: 2rem 1rem;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            font-size: 0.85rem;
            color: #666;
        }}
        .page-footer h3 {{
            font-size: 0.95rem;
            margin-bottom: 8px;
            color: #333;
        }}
        .page-footer p {{
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        .page-footer a {{
            color: #555;
            text-decoration-color: rgba(85, 85, 85, 0.3);
        }}
        .page-footer a:hover {{
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

        /* Print styles */
        @media print {{
            body {{ background: #fff; }}
            .uni-branding-bar {{ display: none; }}
            .page-nav {{ display: none; }}
            .page-content {{
                box-shadow: none;
                margin: 0;
                padding: 1rem;
                max-width: 100%;
            }}
            .page-footer {{ display: none; }}
            .policy-card {{ box-shadow: none; }}
        }}

        /* Mobile */
        @media (max-width: 768px) {{
            .uni-branding-bar {{ padding: 0.5rem 1rem; }}
            .uni-branding-bar a span {{ display: none; }}
            .uni-branding-logo {{ height: 20px; }}
            .page-content {{ margin: 1rem; padding: 1.2rem; }}
            .page-nav {{
                padding: 0.5rem 1rem;
                gap: 0.5rem;
                justify-content: center;
            }}
            .nav-spacer {{ display: none; }}
            .nav-customize {{ font-size: 0.8rem; width: 100%; text-align: center; }}
        }}
    </style>
</head>
<body>
    <nav class="uni-branding-bar" aria-label="{'Preset-Übersicht' if lang == 'de' else 'Preset overview'}">
        <a href="{presets_index_url}" class="branding-back">&larr; {'Alle Presets' if lang == 'de' else 'All Presets'}</a>
        <a href="https://www.uni-bamberg.de/" target="_blank" rel="noopener">
            <span>Universität Bamberg</span>
            <svg class="uni-branding-logo" viewBox="0 0 183 183" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><circle cx="76.6" cy="106" r="36" style="fill:none;stroke:white;stroke-width:19.84px"/><path d="M26.7,25.2C65.4,1.3 115.6,8.2 146.4,41.6C177.2,75 180.1,125.6 153.1,162.2" style="fill:none;stroke:white;stroke-width:19.84px"/><path d="M11.2,109.2C9.8,82.5 25,57.6 49.4,46.5C73.8,35.4 102.5,40.2 121.8,58.7C141.2,77.2 147.3,105.7 137.3,130.5C127.3,155.4 103.1,171.6 76.3,171.5" style="fill:none;stroke:white;stroke-width:19.84px"/></svg>
        </a>
    </nav>

    <nav class="page-nav">
        <div class="nav-group">
            <a href="{de_url}" class="nav-btn {'active' if lang == 'de' else ''}">DE</a>
            <a href="{en_url}" class="nav-btn {'active' if lang == 'en' else ''}">EN</a>
        </div>
        <div class="nav-group">
            <a href="{no_upload_url}" class="nav-btn {'active' if not upload else ''}">{escape_html('Kein Upload' if lang == 'de' else 'No upload')}</a>
            <a href="{upload_url}" class="nav-btn {'active' if upload else ''}">{escape_html('Upload erlaubt' if lang == 'de' else 'Upload allowed')}</a>
        </div>
        <div class="nav-spacer"></div>
        <a href="{escape_html(generator_url)}" class="nav-customize">{escape_html(customize_label)} &rarr;</a>
    </nav>

    <main class="page-content">
        <div class="generated-policy">
            {policy_content}
        </div>
    </main>

    <footer class="page-footer">
        {'<div class="footer-section"><h3>&Uuml;ber diesen Generator</h3><p>Dieser KI-Policy-Generator wird vom <a href="https://www.uni-bamberg.de/cio/" target="_blank">Chief Information Office der Universit&auml;t Bamberg</a> betrieben und im Rahmen des Projekts <a href="https://projekt-bakule.de/" target="_blank">BaKuLe</a> entwickelt. BaKuLe ist ein Hochschulentwicklungsprojekt der Universit&auml;t Bamberg, gef&ouml;rdert durch die <a href="https://stiftung-hochschullehre.de/" target="_blank">Stiftung Innovation in der Hochschullehre</a>.</p><p>Bei der Entwicklung der Texte und des Generators kam Generative KI zum Einsatz.</p><p class="footer-logo"><a href="https://stiftung-hochschullehre.de/" target="_blank"><img src="/v3/images/logo-stil.svg" alt="Stiftung Innovation in der Hochschullehre" height="40"></a></p></div><div class="footer-links"><a href="https://www.uni-bamberg.de/cio/ki/" target="_blank">Weiterf&uuml;hrende Informationen</a><a href="https://github.com/UBA-PSI/ki-policy-generator" target="_blank">GitHub</a><a href="https://www.uni-bamberg.de/cio/kontaktnavigation/impressum/" target="_blank">Impressum</a><a href="https://www.uni-bamberg.de/its/verfahrensweisen/datenschutz/datenschutzerklaerungen/webauftritt/" target="_blank">Datenschutz</a></div><div class="footer-license"><p>Inhalte lizenziert unter <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.de" target="_blank">CC BY-SA 4.0</a>, Code unter <a href="https://opensource.org/licenses/MIT" target="_blank">MIT-Lizenz</a></p></div><div class="footer-bottom"><p>Der KI-Policy-Generator l&auml;uft vollst&auml;ndig clientseitig. Die Inhalte, die Sie eingeben, werden nicht an den Server gesendet.</p></div>' if lang == 'de' else '<div class="footer-section"><h3>About this Generator</h3><p>This AI Policy Generator is operated by the <a href="https://www.uni-bamberg.de/cio/" target="_blank">Chief Information Office of the University of Bamberg</a> and developed as part of the <a href="https://projekt-bakule.de/" target="_blank">BaKuLe</a> project. BaKuLe is a higher education development project at the University of Bamberg, funded by the <a href="https://stiftung-hochschullehre.de/" target="_blank">Foundation for Innovation in Higher Education Teaching</a>.</p><p>Generative AI was used in the development of the texts and the generator.</p><p class="footer-logo"><a href="https://stiftung-hochschullehre.de/" target="_blank"><img src="/v3/images/logo-stil.svg" alt="Foundation for Innovation in Higher Education Teaching" height="40"></a></p></div><div class="footer-links"><a href="https://www.uni-bamberg.de/cio/ki/" target="_blank">More Information</a><a href="https://github.com/UBA-PSI/ki-policy-generator" target="_blank">GitHub</a><a href="https://www.uni-bamberg.de/cio/kontaktnavigation/impressum/" target="_blank">Legal Notice</a><a href="https://www.uni-bamberg.de/its/verfahrensweisen/datenschutz/datenschutzerklaerungen/webauftritt/" target="_blank">Privacy Policy</a></div><div class="footer-license"><p>Content licensed under <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.en" target="_blank">CC BY-SA 4.0</a>, code under <a href="https://opensource.org/licenses/MIT" target="_blank">MIT License</a></p></div><div class="footer-bottom"><p>The AI Policy Generator runs entirely client-side. The content you enter is not sent to the server.</p></div>'}
    </footer>

    <script>
        // Set current date
        document.getElementById('policy-date').textContent =
            new Date().toLocaleDateString('{date_locale}');
    </script>
</body>
</html>'''


# ---------------------------------------------------------------------------
# Redirect page
# ---------------------------------------------------------------------------

def generate_redirect_page(preset_id):
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0;url=de/">
    <title>Redirecting…</title>
</head>
<body>
    <p>Redirecting to <a href="de/">de/</a>…</p>
    <script>window.location.replace('de/');</script>
</body>
</html>'''


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Generate static preset pages')
    parser.add_argument(
        '--output', '-o',
        default=None,
        help='Output directory (default: p/ in project root)',
    )
    parser.add_argument(
        '--generator-url',
        default='/v3/',
        help='Base URL of the generator (default: /v3/)',
    )
    args = parser.parse_args()

    # Find project root (where data/ directory is)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_dir = os.path.join(project_root, 'data')

    if not os.path.isdir(data_dir):
        print(f'Error: data/ directory not found at {data_dir}', file=sys.stderr)
        sys.exit(1)

    output_dir = args.output or os.path.join(project_root, 'p')

    # Load all YAML files
    print('Loading YAML data…')
    policy_de = load_yaml(os.path.join(data_dir, 'policy-data.yaml'))
    policy_en = load_yaml(os.path.join(data_dir, 'policy-data-en.yaml'))
    presets_de = load_yaml(os.path.join(data_dir, 'presets.yaml'))
    presets_en = load_yaml(os.path.join(data_dir, 'presets-en.yaml'))

    # Build item maps
    item_map_de = build_item_map(policy_de)
    item_map_en = build_item_map(policy_en)

    # Extract UI strings
    ui_strings_de = policy_de.get('ui_strings', {})
    ui_strings_en = policy_en.get('ui_strings', {})

    # Build preset lookup by id
    presets_by_id_de = {p['id']: p for p in presets_de.get('presets', [])}
    presets_by_id_en = {p['id']: p for p in presets_en.get('presets', [])}

    preset_ids = [p['id'] for p in presets_de.get('presets', [])]

    file_count = 0

    for preset_id in preset_ids:
        print(f'  Generating {preset_id}…')

        # Create redirect page: /p/{id}/index.html
        redirect_dir = os.path.join(output_dir, preset_id)
        os.makedirs(redirect_dir, exist_ok=True)
        redirect_path = os.path.join(redirect_dir, 'index.html')
        with open(redirect_path, 'w', encoding='utf-8') as f:
            f.write(generate_redirect_page(preset_id))
        file_count += 1

        for lang in ('de', 'en'):
            preset = presets_by_id_de[preset_id] if lang == 'de' else presets_by_id_en[preset_id]
            item_map = item_map_de if lang == 'de' else item_map_en
            ui_strings = ui_strings_de if lang == 'de' else ui_strings_en
            other_lang = 'en' if lang == 'de' else 'de'

            for upload in (False, True):
                # Resolve items
                items = resolve_preset_items(preset, item_map, upload)
                items_grouped = group_items_by_category(items)

                # Generate content
                policy_html = generate_policy_content(
                    preset, items_grouped, upload, lang, ui_strings,
                )

                # Generate full page
                page_html = generate_full_page(
                    preset, policy_html, upload, lang, other_lang,
                    ui_strings, preset_id, args.generator_url,
                )

                # Write file
                if upload:
                    page_dir = os.path.join(output_dir, preset_id, lang, 'upload')
                else:
                    page_dir = os.path.join(output_dir, preset_id, lang)

                os.makedirs(page_dir, exist_ok=True)
                page_path = os.path.join(page_dir, 'index.html')
                with open(page_path, 'w', encoding='utf-8') as f:
                    f.write(page_html)
                file_count += 1

    print(f'\nDone! Generated {file_count} files in {output_dir}')


if __name__ == '__main__':
    main()
