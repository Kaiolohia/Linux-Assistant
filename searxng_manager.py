import subprocess
import sys
import time
import urllib
from pathlib import Path

config_path = Path(__file__).parent / "searxng" / "settings.yml"

def ensure_searxng_running():
    """Check whether the SearXNG container is running and start it if needed."""
    try:
        result = subprocess.run(
            ["podman", "ps"],
            capture_output=True,
            text=True,
        )

        # If the running-container list already contains SearXNG,
        # no additional setup is needed.
        if "searxng" in result.stdout.lower():
            print("✅ SearXNG container is already running")
            return

        print("🔄 Starting SearXNG container...")

        subprocess.run(
    [
        "podman",
        "run",
        "-d",
        "--name",
        "searxng",
        "-p",
        "127.0.0.1:8080:8080",
        "-v",
        f"{config_path}:/etc/searxng/settings.yml:ro,Z",
        "docker.io/searxng/searxng:latest",
    ],
        capture_output=True,
        text=True,
        )

        # Check if container started normally
        if result.returncode != 0:
            print(f"❌ Failed to start SearXNG: {result.stderr.strip()}")
            sys.exit(1)

        # Attempt HTTP requests to searxng to ensure container is sear is running fully.
        for attempt in range(20):
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:8080/",
                    timeout=1,
                ):
                    print("✅ SearXNG is ready")
                    break

            except (urllib.error.URLError, TimeoutError, ConnectionResetError):
                time.sleep(0.25)

        else:
            print("❌ SearXNG container started, but the web service never became ready.")
            sys.exit(1)

    except FileNotFoundError:
        print("❌ Podman not found. Please install Podman first.")
        sys.exit(1)


def stop_searxng():
    """Remove the SearXNG container when Bob exits."""
    try:
        subprocess.run(
            ["podman", "rm", "searxng", "-f"],
            capture_output=True,
            text=True,
        )

        print("🛑 Stopped SearXNG container")

    except Exception as error:
        print(f"⚠️ Could not stop container: {error}")