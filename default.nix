with import <nixpkgs> {};
stdenv.mkDerivation rec {
  name = "env";
  env = buildEnv { name = name; paths = buildInputs; };
  buildInputs = [
    python3
    pipenv
    python3Packages.pillow
  ];
  shellHook = ''
  pipenv sync --dev
  '';
}
