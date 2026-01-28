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

// Aktuelle Sprache
let currentLanguage = 'de';

/**
 * Lädt die Policy-Daten aus der YAML-Datei
 * @param {string} language - Sprachcode (default: 'de')
 * @returns {Promise<object>} Die geparsten Policy-Daten
 */
async function loadPolicyData(language = 'de') {
    const filename = language === 'de' ? 'policy-data.yaml' : `policy-data-${language}.yaml`;

    try {
        const response = await fetch(`data/${filename}`);
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
    // parseMarkdown ist die bestehende Funktion aus v3.html die escapeHTML intern aufruft
    const renderedHtml = parseMarkdown(item.text.trim());
    textDiv.innerHTML = renderedHtml;
    itemDiv.appendChild(textDiv);

    // Action Buttons
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'item-actions';

    const editBtn = document.createElement('button');
    editBtn.className = 'edit-item-btn';
    editBtn.textContent = 'Bearbeiten';
    actionsDiv.appendChild(editBtn);

    const addBtn = document.createElement('button');
    addBtn.className = 'add-item-btn';
    addBtn.textContent = 'Hinzufügen';
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
 * Hauptfunktion: Lädt Daten und rendert die UI
 * @param {string} language - Sprachcode (default: 'de')
 */
async function initializePolicyLoader(language = 'de') {
    try {
        // Lade YAML-Daten
        const data = await loadPolicyData(language);

        // Finde den Container
        const container = document.querySelector('.left-panel');
        if (!container) {
            throw new Error('Container .left-panel not found');
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
            }
            if (data.metadata.default_document_intro) {
                window.documentIntro = data.metadata.default_document_intro;
                if (typeof updateIntroDisplay === 'function') {
                    updateIntroDisplay();
                }
            }
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
            h3.textContent = 'Fehler beim Laden der Policy-Daten';
            errorDiv.appendChild(h3);

            const p1 = document.createElement('p');
            p1.textContent = error.message;
            errorDiv.appendChild(p1);

            const p2 = document.createElement('p');
            p2.textContent = 'Stellen Sie sicher, dass die Datei über einen Webserver geladen wird (nicht file://).';
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
        const confirmSwitch = confirm(
            language === 'en'
                ? 'Switching the language will reload all text modules. Unsaved changes will be lost. Continue?'
                : 'Beim Sprachwechsel werden alle Textbausteine neu geladen. Nicht gespeicherte Änderungen gehen verloren. Fortfahren?'
        );
        if (!confirmSwitch) return;
    }

    try {
        await initializePolicyLoader(language);
        console.log(`Language switched to ${language}`);
    } catch (error) {
        console.error('Failed to switch language:', error);
        alert(
            language === 'en'
                ? 'Failed to load English text modules.'
                : 'Fehler beim Laden der Textbausteine.'
        );
    }
}

/**
 * Prüft ob es ungespeicherte Änderungen gibt
 * @returns {boolean} true wenn Änderungen vorhanden
 */
function checkForUnsavedChanges() {
    const addedItems = document.querySelectorAll('.policy-item.added');
    const editedItems = document.querySelectorAll('.policy-item[data-edited="true"]');
    return addedItems.length > 0 || editedItems.length > 0;
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
