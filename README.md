# KI-Policy-Generator

Ein interaktives Werkzeug zur Erstellung von KI-Richtlinien für Lehrveranstaltungen an Hochschulen.

**Live-Version:** https://web.psi.uni-bamberg.de/ki-policy-generator/v3/

## Funktionen

- Erstellung individueller KI-Richtlinien für Lehrveranstaltungen
- Unterstützung für Deutsch und Englisch
- Export/Import von Konfigurationen
- Vollständig clientseitig – keine Daten werden an den Server gesendet

## Nutzung

Die Anwendung läuft vollständig im Browser. Einfach `index.html` öffnen oder auf einem Webserver bereitstellen.

### Lokale Nutzung

```bash
# Repository klonen
git clone https://github.com/UBA-PSI/ki-policy-generator.git
cd ki-policy-generator

# Mit beliebigem Webserver starten, z.B.:
python3 -m http.server 8000
# Dann http://localhost:8000 im Browser öffnen
```

## Projektstruktur

```
├── index.html          # Hauptanwendung
├── policy-loader.js    # Logik zum Laden der Policy-Daten
├── data/
│   ├── policy-data.yaml      # Policy-Inhalte (Deutsch)
│   └── policy-data-en.yaml   # Policy-Inhalte (Englisch)
├── lib/
│   └── js-yaml.min.js  # YAML-Parser
├── fonts/              # Roboto-Schriftarten (Apache 2.0)
└── pako.min.js         # Komprimierungsbibliothek
```

## Lizenz

Dieses Projekt verwendet eine duale Lizenzierung:

- **Code** (HTML, JavaScript): [MIT License](LICENSE)
- **Inhalte** (Policy-Texte in `data/*.yaml`): [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.de)
- **Schriftarten** (`fonts/`): [Apache License 2.0](fonts/LICENSE)

## Autor

**Dominik Herrmann**
Otto-Friedrich-Universität Bamberg
https://www.uni-bamberg.de/psi/

## Kontakt

Chief Information Office der Universität Bamberg
https://www.uni-bamberg.de/cio/
