import requests

OLLAMA_URL = "http://ollama:11434/api/generate"

def ask_ollama(prompt: str, model: str = "mistral") -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"Erro ao consultar Ollama: {e}"
