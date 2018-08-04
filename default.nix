with import <nixpkgs> {};
stdenv.mkDerivation rec {
  name = "env";
  env = buildEnv { name = name; paths = buildInputs; };
  buildInputs = [
    python3
    pipenv
    python3Packages.pillow
    python3Packages.reportlab
  ];
  shellHook = ''
  pipenv sync --dev
  '';
}
