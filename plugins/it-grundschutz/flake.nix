{
  description = "it-grundschutz — Build-/Laufumgebung für Korpus-Ingest und OSCAL-Lookup (Grundschutz++)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f system (import nixpkgs { inherit system; }));
    in
    {
      devShells = forAll (system: pkgs: {
        default = pkgs.mkShell {
          packages = [ pkgs.python3 pkgs.curl pkgs.jq pkgs.coreutils ];
          shellHook = ''
            echo "it-grundschutz devShell — scripts/ingest.sh, scripts/gs.py"
            echo "Korpus-Verzeichnis via GS_CORPUS_DIR (default ~/.local/share/it-grundschutz/corpus)"
          '';
        };
      });

      apps = forAll (system: pkgs:
        let
          runtime = [ pkgs.python3 pkgs.curl pkgs.jq pkgs.coreutils ];
          mkApp = name: desc: cmd: {
            type = "app";
            meta.description = desc;
            program = toString (pkgs.writeShellScript name ''
              export PATH=${pkgs.lib.makeBinPath runtime}:$PATH
              exec ${cmd} "$@"
            '');
          };
          ingest = mkApp "gs-ingest" "Grundschutz++-OSCAL-Korpus von der BSI-Quelle laden/aktualisieren"
            "${pkgs.bash}/bin/bash ${./scripts/ingest.sh}";
          ingest-2023 = mkApp "gs-ingest-2023" "Edition 2023 (DocBook-XML) von der BSI-Quelle nach OSCAL normalisieren"
            "${pkgs.python3}/bin/python3 ${./scripts/adapter-2023.py}";
          gs = mkApp "gs" "OSCAL-Lookup im lokalen Grundschutz-Korpus (status/groups/targets/list/get/search/prozess/checklist/coverage/crosswalk/json; --edition, --target)"
            "${pkgs.coreutils}/bin/env GS_HINTS_FILE=${./data/edition-2023-baustein-komponenten.csv} ${pkgs.python3}/bin/python3 ${./scripts/gs.py}";
        in
        {
          inherit ingest ingest-2023 gs;
          default = gs;
        });
    };
}
