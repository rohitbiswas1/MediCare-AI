"""Build through the existing cloud proxy and CA, without printing or persisting credentials.
Optional helper for Docker bridges that lack the host's proxy DNS. Standard docker build also works
on ordinary development machines. Only predefined Docker proxy args and a temporary CA secret are used.
"""

import os
import argparse
import socket
import subprocess
from pathlib import Path
from urllib.parse import urlparse

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dockerfile", default="infrastructure/docker/api.Dockerfile")
parser.add_argument("--tag", default="medicare-ai-api:local")
args = parser.parse_args()
environment = os.environ.copy()
environment.setdefault("DOCKER_CONFIG", str(root / ".local" / "docker"))
command = ["docker", "build", "--network", "host"]
seen = set()
for variable in ["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"]:
    if environment.get(variable):
        command += ["--build-arg", variable]
        if variable != "NO_PROXY":
            hostname = urlparse(environment[variable]).hostname
            if hostname and hostname not in seen:
                command += ["--add-host", f"{hostname}:{socket.gethostbyname(hostname)}"]
                seen.add(hostname)
ca_path = environment.get("SSL_CERT_FILE")
if ca_path and Path(ca_path).is_file():
    command += ["--secret", f"id=build_ca,src={ca_path}"]
command += ["-f", args.dockerfile, "-t", args.tag, "."]
raise SystemExit(subprocess.call(command, cwd=root, env=environment))
