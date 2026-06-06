{
  description = "it-grundschutz — Build-/Laufumgebung fuer Korpus-Ingest und OSCAL-Lookup (Grundschutz++)";

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
          gs = mkApp "gs" "OSCAL-Lookup im lokalen Grundschutz-Korpus (status/groups/list/get/search/json)"
            "${pkgs.python3}/bin/python3 ${./scripts/gs.py}";
        in
        {
          inherit ingest gs;
          default = gs;
        });
    };
}
