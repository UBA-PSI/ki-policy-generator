/**
 * Policy Data Loader
 * Lädt Textbausteine aus YAML und generiert das HTML dynamisch
 *
 * Vorbereitet für Mehrsprachigkeit: loadPolicyData('de') oder loadPolicyData('en')
 *
 * Sicherheitshinweis: Die YAML-Daten werden als vertrauenswürdig behandelt,
 * da sie aus lokalen Dateien stammen. Der parseMarkdown-Parser escaped
 * HTML-Sonderzeichen bevor Markdown verarbeitet wird.
 */

// Globale Variable für die geladenen Policy-Daten
let policyData = null;

// UI-Übersetzungen
let uiStrings = {};

// Aktuelle Sprache
let currentLanguage = 'de';

// Preset-Daten
let presetsData = null;

// Map: YAML-Item-ID → Runtime-ID (z.B. "grundsatz-erlaubt" → "item-1")
let yamlIdToRuntimeId = {};

// Map: YAML-Item-ID → Array von Preset-Textvarianten
// z.B. { "pruefung-massnahmen": [{presetId, presetName, text}, ...] }
let presetVariantsByItemId = {};

/**
 * Gibt den übersetzten UI-String für den gegebenen Key zurück
 * @param {string} key - Der Übersetzungsschlüssel
 * @param {string} fallback - Fallback-Text wenn Key nicht gefunden
 * @returns {string} Der übersetzte Text
 */
function t(key, fallback) {
    return uiStrings[key] || fallback || key;
}

/**
 * Lädt die Policy-Daten aus der YAML-Datei
 * @param {string} language - Sprachcode (default: 'de')
 * @returns {Promise<object>} Die geparsten Policy-Daten
 */
async function loadPolicyData(language = 'de') {
    const filename = language === 'de' ? 'policy-data.yaml' : `policy-data-${language}.yaml`;

    try {
        const cacheBust = window.APP_VERSION || '3.4.9';
        const response = await fetch(`data/${filename}?v=${cacheBust}`);
        if (!response.ok) {
            throw new Error(`Failed to load ${filename}: ${response.status}`);
        }
        const yamlText = await response.text();
        // Security: Use safe schema to prevent code execution via YAML
        policyData = jsyaml.load(yamlText, { schema: jsyaml.SAFE_SCHEMA });
        console.log(`Policy data loaded successfully (${language}):`, policyData.categories.length, 'categories');
        return policyData;
    } catch (error) {
        console.error('Error loading policy data:', error);
        throw error;
    }
}

/**
 * Rendert alle Kategorien und Policy-Items in den Container
 * @param {HTMLElement} container - Das DOM-Element für die Policy-Items
 * @param {object} data - Die Policy-Daten
 */
function renderPolicyItems(container, data) {
    // Container leeren
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }

    data.categories.forEach(category => {
        const categoryEl = renderCategory(category);
        container.appendChild(categoryEl);
    });
}

/**
 * Rendert eine einzelne Kategorie
 * @param {object} category - Die Kategorie-Daten
 * @returns {HTMLElement} Das Kategorie-Element
 */
function renderCategory(category) {
    const categoryDiv = document.createElement('div');
    categoryDiv.className = 'category';
    categoryDiv.dataset.categoryId = category.id;

    // Category Header
    const header = document.createElement('div');
    header.className = 'category-header';
    const h2 = document.createElement('h2');
    h2.textContent = category.title;
    header.appendChild(h2);
    categoryDiv.appendChild(header);

    // Category Content
    const content = document.createElement('div');
    content.className = 'category-content';

    category.subcategories.forEach(subcategory => {
        const subDiv = renderSubcategory(subcategory);
        content.appendChild(subDiv);
    });

    categoryDiv.appendChild(content);
    return categoryDiv;
}

/**
 * Rendert eine Subkategorie
 * @param {object} subcategory - Die Subkategorie-Daten
 * @returns {HTMLElement} Das Subkategorie-Element
 */
function renderSubcategory(subcategory) {
    const subDiv = document.createElement('div');
    subDiv.className = 'subcategory';

    // Title
    const title = document.createElement('div');
    title.className = 'subcategory-title';
    title.textContent = subcategory.title;
    subDiv.appendChild(title);

    // Instructor Guidance (Hinweise für Lehrende)
    if (subcategory.guidance) {
        const guidance = document.createElement('div');
        guidance.className = 'instructor-guidance';
        const p = document.createElement('p');
        p.textContent = subcategory.guidance.trim();
        guidance.appendChild(p);
        subDiv.appendChild(guidance);
    }

    // Policy Items
    subcategory.items.forEach(item => {
        const itemEl = renderPolicyItem(item);
        subDiv.appendChild(itemEl);
    });

    return subDiv;
}

/**
 * Rendert ein einzelnes Policy-Item
 * @param {object} item - Die Item-Daten
 * @returns {HTMLElement} Das Policy-Item-Element
 */
function renderPolicyItem(item) {
    const itemDiv = document.createElement('div');
    itemDiv.className = 'policy-item';
    itemDiv.dataset.itemId = item.id;

    // Tags
    const tagsDiv = document.createElement('div');
    tagsDiv.className = 'policy-tags';
    item.tags.forEach(tag => {
        const span = document.createElement('span');
        span.className = `tag tag-${tag.type}`;
        span.textContent = tag.label;
        tagsDiv.appendChild(span);
    });
    itemDiv.appendChild(tagsDiv);

    // Text (Markdown wird zu HTML konvertiert)
    // parseMarkdown escaped HTML-Sonderzeichen bevor Markdown verarbeitet wird
    const textDiv = document.createElement('div');
    textDiv.className = 'policy-text';
    // Store raw Markdown source for correct revert in inline editor
    textDiv.dataset.originalMarkdown = item.text.trim();
    // Security: parseMarkdown escapes HTML via escapeHTML() before processing Markdown
    const renderedHtml = parseMarkdown(item.text.trim());
    textDiv.innerHTML = renderedHtml;
    itemDiv.appendChild(textDiv);

    // Action Buttons
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'item-actions';

    const editBtn = document.createElement('button');
    editBtn.className = 'edit-item-btn';
    editBtn.textContent = t('btn_edit', 'Bearbeiten');
    actionsDiv.appendChild(editBtn);

    const addBtn = document.createElement('button');
    addBtn.className = 'add-item-btn';
    addBtn.textContent = t('btn_add', 'Hinzufügen');
    actionsDiv.appendChild(addBtn);

    itemDiv.appendChild(actionsDiv);

    return itemDiv;
}

/**
 * Initialisiert die Policy-Daten nach dem Laden
 * Ruft die bestehenden Initialisierungsfunktionen auf
 */
function initializeAfterLoad() {
    // IDs zuweisen und Original-Texte speichern
    if (typeof initializeAllPolicyItems === 'function') {
        initializeAllPolicyItems();
    }

    // SVG-Icons hinzufügen
    if (typeof addSvgIcons === 'function') {
        addSvgIcons();
    }

    // Accordion-Funktionalität
    if (typeof initializeAccordions === 'function') {
        initializeAccordions();
    }

    // Editor-Interaktionen
    if (typeof setupEditorInteractions === 'function') {
        setupEditorInteractions();
    }

    console.log('Policy items initialized');
}

/**
 * Baut eine Map von YAML-Item-IDs zu Runtime-IDs
 * Muss nach initializeAllPolicyItems() aufgerufen werden
 */
function buildIdMap() {
    yamlIdToRuntimeId = {};
    document.querySelectorAll('.policy-item').forEach(item => {
        const yamlId = item.dataset.itemId;
        const runtimeId = item.dataset.id;
        if (yamlId && runtimeId) {
            yamlIdToRuntimeId[yamlId] = runtimeId;
        }
    });
    console.log('ID map built:', Object.keys(yamlIdToRuntimeId).length, 'entries');
}

/**
 * Normalisiert einen Preset-Item-Eintrag (String oder Objekt) zu einheitlichem Format
 * @param {string|object} entry - "yaml-id" oder { id: "yaml-id", text: "..." }
 * @returns {{ yamlId: string, text: string|null }|null}
 */
function normalizePresetItem(entry) {
    if (typeof entry === 'string') {
        return { yamlId: entry, text: null };
    }
    if (entry && typeof entry === 'object' && entry.id) {
        return { yamlId: entry.id, text: entry.text || null };
    }
    console.warn('Unrecognized preset item entry:', entry);
    return null;
}

/**
 * Baut eine Map von YAML-Item-IDs zu ihren Preset-spezifischen Textvarianten.
 * Wird nach dem Laden der Presets aufgerufen.
 * @param {object} data - Die geladenen Preset-Daten
 */
function buildPresetVariantMap(data) {
    presetVariantsByItemId = {};
    if (!data || !data.presets) return;

    data.presets.forEach(preset => {
        // Alle Item-Einträge sammeln (reguläre + upload + no_upload)
        const allEntries = [
            ...(preset.items || []),
            preset.upload_item,
            preset.no_upload_item
        ].filter(Boolean);

        allEntries.forEach(entry => {
            const normalized = normalizePresetItem(entry);
            if (!normalized || !normalized.text) return;

            const { yamlId, text } = normalized;
            const textTrimmed = text.trim();

            if (!presetVariantsByItemId[yamlId]) {
                presetVariantsByItemId[yamlId] = [];
            }

            // Duplikate vermeiden (gleicher Text)
            const exists = presetVariantsByItemId[yamlId].some(
                v => v.text === textTrimmed
            );
            if (!exists) {
                presetVariantsByItemId[yamlId].push({
                    presetId: preset.id,
                    presetName: preset.name,
                    text: textTrimmed
                });
            }
        });
    });

    console.log('Preset variant map built:', Object.keys(presetVariantsByItemId).length, 'items with variants');
}

/**
 * Fügt Variant-Badges an Items an, die Preset-Textvarianten haben.
 * Wird nach buildPresetVariantMap() aufgerufen.
 */
function addVariantBadges() {
    // Remove existing badges first (for language switch)
    document.querySelectorAll('.variant-badge').forEach(b => b.remove());

    Object.keys(presetVariantsByItemId).forEach(yamlId => {
        const variants = presetVariantsByItemId[yamlId];
        if (!variants || variants.length === 0) return;

        const item = document.querySelector(`.policy-item[data-item-id="${yamlId}"]`);
        if (!item) return;

        const actions = item.querySelector('.item-actions');
        if (!actions) return;

        const badge = document.createElement('button');
        badge.className = 'variant-badge';
        badge.title = t('variant_badge_tooltip', 'Textvarianten aus Vorlagen verfügbar');
        badge.type = 'button';
        badge.textContent = '\u27D0 ' + t('variant_badge_label', 'Vorlagen');
        badge.addEventListener('click', () => {
            const itemId = item.dataset.id;
            const policyTextEl = item.querySelector('.policy-text');
            if (itemId && policyTextEl && typeof enableInlineEditing === 'function') {
                enableInlineEditing(item, itemId, policyTextEl.innerHTML);
            } else if (!itemId) {
                console.warn('Variant badge clicked but item has no runtime ID:', item.dataset.itemId);
            }
        });

        actions.insertBefore(badge, actions.firstChild);
    });

    console.log('Variant badges added');
}

/**
 * Lädt die Preset-Daten aus der YAML-Datei
 * @param {string} language - Sprachcode (default: 'de')
 * @returns {Promise<object>} Die geparsten Preset-Daten
 */
async function loadPresets(language = 'de') {
    const filename = language === 'de' ? 'presets.yaml' : `presets-${language}.yaml`;

    try {
        const cacheBust = window.APP_VERSION || '3.4.9';
        const response = await fetch(`data/${filename}?v=${cacheBust}`);
        if (!response.ok) {
            throw new Error(`Failed to load ${filename}: ${response.status}`);
        }
        const yamlText = await response.text();
        presetsData = jsyaml.load(yamlText, { schema: jsyaml.SAFE_SCHEMA });
        console.log(`Presets loaded successfully (${language}):`, presetsData.presets.length, 'presets');
        return presetsData;
    } catch (error) {
        console.error('Error loading presets:', error);
        presetsData = null;
        return null;
    }
}

/**
 * Hauptfunktion: Lädt Daten und rendert die UI
 * @param {string} language - Sprachcode (default: 'de')
 */
async function initializePolicyLoader(language = 'de') {
    try {
        // Lade YAML-Daten
        const data = await loadPolicyData(language);

        // Store UI strings globally (must happen before rendering so t() works)
        if (data.ui_strings) {
            uiStrings = data.ui_strings;
        }

        // Finde den Container
        const container = document.querySelector('.left-panel');
        if (!container) {
            throw new Error('Container .left-panel not found');
        }

        // Reset preset state (e.g. on language switch)
        if (typeof resetPresetState === 'function') {
            resetPresetState();
        }

        // Rendere Policy-Items
        renderPolicyItems(container, data);

        // Initialisiere bestehende Funktionen
        initializeAfterLoad();

        // Setze Dokument-Titel und Intro aus Metadata
        if (data.metadata) {
            const docTitle = document.getElementById('document-title');
            if (data.metadata.default_document_title && docTitle) {
                docTitle.textContent = data.metadata.default_document_title;
                window.defaultDocumentTitle = data.metadata.default_document_title;
            }
            if (data.metadata.default_document_intro) {
                window.documentIntro = data.metadata.default_document_intro;
                window.defaultDocumentIntro = data.metadata.default_document_intro;
                if (typeof updateIntroDisplay === 'function') {
                    updateIntroDisplay();
                }
            }
        }

        // Apply UI translations
        applyUITranslations(language);

        // Build ID map (YAML-ID → Runtime-ID) after items are initialized
        buildIdMap();

        // Load presets, build variant map, and render cards
        await loadPresets(language);
        if (presetsData) {
            buildPresetVariantMap(presetsData);
            if (typeof renderPresetCards === 'function') {
                renderPresetCards(presetsData.presets);
            }
            addVariantBadges();
        }

        console.log('Policy loader initialization complete');

        // Aktualisiere Sprachwahl-UI
        currentLanguage = language;
        updateLanguageSwitcher();

    } catch (error) {
        console.error('Failed to initialize policy loader:', error);

        // Zeige Fehlermeldung
        const container = document.querySelector('.left-panel');
        if (container) {
            // Container leeren
            while (container.firstChild) {
                container.removeChild(container.firstChild);
            }

            // Fehlermeldung erstellen
            const errorDiv = document.createElement('div');
            errorDiv.style.cssText = 'padding: 20px; color: #c00; background: #fee; border: 1px solid #c00; border-radius: 4px; margin: 20px;';

            const h3 = document.createElement('h3');
            h3.textContent = t('error_loading_title', 'Fehler beim Laden der Policy-Daten');
            errorDiv.appendChild(h3);

            const p1 = document.createElement('p');
            p1.textContent = error.message;
            errorDiv.appendChild(p1);

            const p2 = document.createElement('p');
            p2.textContent = t('error_loading_hint', 'Stellen Sie sicher, dass die Datei über einen Webserver geladen wird (nicht file://)');
            errorDiv.appendChild(p2);

            container.appendChild(errorDiv);
        }
    }
}

/**
 * Wechselt die Sprache der Textbausteine
 * @param {string} language - Zielsprache ('de' oder 'en')
 */
async function switchLanguage(language) {
    if (language === currentLanguage) return;

    // Warnung anzeigen, dass Änderungen verloren gehen könnten
    const hasChanges = checkForUnsavedChanges();
    if (hasChanges) {
        const confirmSwitch = confirm(t('confirm_language_switch'));
        if (!confirmSwitch) return;
    }

    try {
        await initializePolicyLoader(language);
        console.log(`Language switched to ${language}`);
    } catch (error) {
        console.error('Failed to switch language:', error);
        alert(t('alert_language_error'));
    }
}

/**
 * Prüft ob es ungespeicherte Änderungen gibt
 * @returns {boolean} true wenn Änderungen vorhanden
 */
function checkForUnsavedChanges() {
    const selectedItems = document.querySelectorAll('.policy-item.selected');
    return selectedItems.length > 0;
}

/**
 * Aktualisiert den Zustand der Sprachwechsel-Buttons
 */
function updateLanguageSwitcher() {
    const switchers = document.querySelectorAll('.language-switcher');
    switchers.forEach(switcher => {
        const deBtn = switcher.querySelector('[data-lang="de"]');
        const enBtn = switcher.querySelector('[data-lang="en"]');
        if (deBtn) {
            deBtn.classList.toggle('active', currentLanguage === 'de');
        }
        if (enBtn) {
            enBtn.classList.toggle('active', currentLanguage === 'en');
        }
    });
}

/**
 * Initialisiert die Sprachwechsel-Event-Handler
 */
function initLanguageSwitcher() {
    document.querySelectorAll('.language-switcher button').forEach(btn => {
        btn.addEventListener('click', () => {
            const lang = btn.dataset.lang;
            if (lang) {
                switchLanguage(lang);
            }
        });
    });
}

/**
 * Wendet UI-Übersetzungen auf alle markierten Elemente an
 * Hinweis: data-i18n-html Werte stammen aus lokalen, vertrauenswürdigen YAML-Dateien
 * (gleiche Vertrauensstufe wie die Policy-Texte, die ebenfalls via innerHTML gesetzt werden)
 * @param {string} language - Aktuelle Sprache ('de' oder 'en')
 */
function applyUITranslations(language) {
    // Update html lang attribute
    document.documentElement.lang = language;

    // Update page title
    document.title = t('page_title', document.title);

    // Apply text translations via data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        const translated = uiStrings[key];
        if (translated) {
            // Preserve SVG icons in buttons
            const svg = el.querySelector('svg');
            if (svg) {
                el.textContent = '';
                el.appendChild(svg);
                el.appendChild(document.createTextNode(' ' + translated));
            } else {
                el.textContent = translated;
            }
        }
    });

    // Apply HTML translations via data-i18n-html attribute
    // Security: These values come from trusted local YAML files (same trust level as policy content)
    document.querySelectorAll('[data-i18n-html]').forEach(el => {
        const key = el.dataset.i18nHtml;
        const translated = uiStrings[key];
        if (translated) {
            el.innerHTML = translated;
        }
    });

    // Apply attribute translations via data-i18n-attr (format: "attr:key")
    document.querySelectorAll('[data-i18n-attr]').forEach(el => {
        const spec = el.dataset.i18nAttr;
        if (!spec) return;
        const [attr, key] = spec.split(':');
        const translated = uiStrings[key];
        if (translated && attr) {
            el.setAttribute(attr, translated);
        }
    });

    // Toggle language-specific content blocks
    document.querySelectorAll('[data-ui-lang]').forEach(el => {
        el.style.display = el.dataset.uiLang === language ? '' : 'none';
    });
}
