# Herkunft

Philharmonie entsteht in `muhackel/claude-code-plugins` aus dem lokalen ask-Plugin und dem hier dokumentierten eigenen Design.

Die Konzepte für getrennte Planungs-, Generator- und Evaluator-Rollen, eine ergebnisorientierte Spec und das Review Briefing sind durch die TandemKit-Evaluierung angeregt. Quelle: [FlineDev/TandemKit](https://github.com/FlineDev/TandemKit), in der Evaluierung genannter Stand `72c4709`, Version 1.4.0.

Die mitgelieferten Rollen, Templates und Laufzeitmodule wurden für Philharmonie neu formuliert beziehungsweise implementiert. Es sind keine TandemKit-Skripte oder wörtlich kopierten Template-Dateien enthalten. Bei einer späteren direkten Übernahme müssen deren vollständige Lizenz- und Copyright-Hinweise zusätzlich ins Paket aufgenommen werden.

Nix, Python, jsonschema, PyYAML und Bubblewrap werden über nixpkgs als Abhängigkeiten bereitgestellt. Ihre Lizenzangaben gehören zu den jeweiligen Nix-Paketen.
