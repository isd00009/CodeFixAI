import requests

class OpenAIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def request_completion(self, prompt: str) -> str:
        payload = {
            "model": "gpt-4.1",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2048,
            "temperature": 0.0
        }
        resp = requests.post(self.endpoint, json=payload, headers=self.headers, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Error {resp.status_code}: {resp.text}")
        data = resp.json()
        # Extraemos el contenido de la IA
        texto = data["choices"][0]["message"]["content"]
        return texto.strip()
