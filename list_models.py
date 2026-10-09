import requests
import os

API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
response = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}")

if response.status_code == 200:
    data = response.json()
    print("Available models:")
    for model in data.get('models', []):
        print(f"- {model['name']}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
