import re
from utils.config_manager import ConfigManager
from logic.openai_client import OpenAIClient
from utils.diff_utils import generar_diff as _diff


class Controller:
    def __init__(self):
        self.config = ConfigManager()
        self.api_key = self.config.load_api_key()
        self.client = OpenAIClient(self.api_key) if self.api_key else None

    def validate_api_key(self, key: str) -> bool:
        return bool(key) and len(key) >= 20

    def save_api_key(self, key: str):
        self.config.save_api_key(key)
        self.api_key = key
        self.client = OpenAIClient(key)

    def load_api_key(self) -> str | None:
        return self.config.load_api_key()

    def detect_language(self, texto: str) -> str:
        t = texto.lower()
        if "def " in t or t.strip().startswith("import "):
            return "Python"
        if "#include" in t or "std::" in t:
            return "C++"
        if "public class" in t or "system.out.println" in t:
            return "Java"
        return ""

    def build_prompt(self, texto: str) -> str:
        """
        Construye un prompt que pida únicamente el código corregido,
        sin explicaciones, listo para copiar y pegar.
        """
        lang = self.detect_language(texto)
        base = (
            "Corrige los errores de sintaxis y estilo del siguiente "
            "fragmento de código"
        )
        if lang:
            base += f" en {lang}"
        base += ":\n"
        base += f"```{texto}```\n\n"
        base += (
            "Devuélveme únicamente el código corregido, listo para copiar "
            "y pegar en mi editor, sin explicaciones ni comentarios adicionales."
        )
        return base

    def send_to_openai(self, prompt: str) -> str:
        if not self.client:
            raise RuntimeError("No hay clave de API configurada.")
        return self.client.request_completion(prompt)

    def extract_code(self, ai_response: str) -> str:
        """
        Extrae el contenido dentro de un bloque ```...``` si existe,
        o devuelve todo el texto si no hay bloque.
        """
        m = re.search(r"```(?:\w*\n)?(.*?)```", ai_response, re.DOTALL)
        if m:
            return m.group(1).strip()
        return ai_response.strip()

    def generar_diff(self, original: str, corregido: str) -> list[str]:
        return _diff(original, corregido)
