import json
import urllib.request


OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "bob:latest"


def ask_ollama(messages, tools):
    """Send the current conversation to Ollama and return its decoded response."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": tools,
        "think": False,
        "stream": False,
        "options": {
            "num_ctx": 16384,
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(request) as response:
        return json.load(response)


def unload_model():
    """Unload Bob from Ollama so its VRAM is released when the wrapper exits."""
    try:
        # keep_alive=0 tells Ollama to unload the model immediately.
        unload_payload = {
            "model": MODEL,
            "messages": [],
            "keep_alive": 0,
            "stream": False,
        }

        unload_request = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(unload_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(unload_request):
            pass

        print("🧠 Bob unloaded from VRAM")

    except Exception as error:
        print(f"⚠️ Could not unload Bob from VRAM: {error}")