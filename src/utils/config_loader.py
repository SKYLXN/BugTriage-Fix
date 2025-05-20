import os
import yaml
import re

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    def env_replace(match):
        var = match.group(1)
        return os.environ.get(var, "")

    text = re.sub(r"\$\{(\w+)\}", env_replace, text)
    return yaml.safe_load(text)
