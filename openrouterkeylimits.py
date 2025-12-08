import requests
import json
from environment.config import OPENROUTER_API_KEY


response = requests.get(
  url="https://openrouter.ai/api/v1/key",
  headers={
    "Authorization": f"Bearer {OPENROUTER_API_KEY}"
  }
)

print(json.dumps(response.json(), indent=2))
