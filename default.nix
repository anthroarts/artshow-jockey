with import <nixpkgs> {};
stdenv.mkDerivation rec {
  name = "env";
  env = buildEnv { name = name; paths = buildInputs; };
  buildInputs = [
    mysql.connector-c
    openssl
    pipenv
    python3
    python3Packages.pillow
    python3Packages.reportlab
  ];
  shellHook = ''
  pipenv sync --dev
  '';
}
