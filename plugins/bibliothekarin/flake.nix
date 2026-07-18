{
  description = "bibliothekarin — Build-/Laufumgebung für Karins Offline-Diagramm-Doku (Mermaid + PlantUML) und lokales Rendering";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f system (import nixpkgs { inherit system; }));

      # Gemeinsame Runtime: Beschaffung (git/wget/poppler-utils/jq/coreutils)
      # + Rendering (mermaid-cli liefert mmdc, plantuml liefert plantuml, graphviz als Backend).
      runtimeFor = pkgs: [
        pkgs.mermaid-cli
        pkgs.plantuml
        pkgs.graphviz
        pkgs.git
        pkgs.wget
        pkgs.poppler-utils   # liefert pdftotext (Attribut heisst poppler-utils, NICHT poppler_utils)
        pkgs.jq
        pkgs.coreutils
      ];
    in
    {
      devShells = forAll (system: pkgs: {
        default = pkgs.mkShell {
          packages = runtimeFor pkgs;
          shellHook = ''
            echo "bibliothekarin devShell — scripts/fetch-diagram-docs.sh"
            echo "Rendering: mmdc (Mermaid), plantuml (PlantUML), pdftotext, git, wget, jq"
            echo "Offline-Doku via DIAGRAM_DOCS_DIR (default ~/.local/share/bibliothekarin/diagram-docs)"
          '';
        };
      });

      apps = forAll (system: pkgs:
        let
          runtime = runtimeFor pkgs;
          mkApp = name: desc: cmd: {
            type = "app";
            meta.description = desc;
            program = toString (pkgs.writeShellScript name ''
              export PATH=${pkgs.lib.makeBinPath runtime}:$PATH
              exec ${cmd} "$@"
            '');
          };
          fetch-docs = mkApp "fetch-docs"
            "Offizielle Diagramm-Doku (Mermaid + PlantUML) offline vorhalten — 14-Tage-Altersgate, --force, --status"
            "${pkgs.bash}/bin/bash ${./scripts/fetch-diagram-docs.sh}";
        in
        {
          inherit fetch-docs;
          default = fetch-docs;
        });
    };
}
