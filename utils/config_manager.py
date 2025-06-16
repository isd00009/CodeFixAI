import json
import os

class ConfigManager:
    def __init__(self):
        home = os.path.expanduser("~")
        cfg_dir = os.path.join(home, ".codefixai")
        os.makedirs(cfg_dir, exist_ok=True)
        self.path = os.path.join(cfg_dir, "config.json")

    def load_api_key(self) -> str | None:
        if not os.path.isfile(self.path):
            return None
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("api_key")

    def save_api_key(self, key: str):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"api_key": key}, f, indent=2)
