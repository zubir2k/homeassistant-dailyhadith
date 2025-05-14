import requests
import os
import hashlib
import json

API_ENDPOINT = os.getenv("API_ENDPOINT")
API_KEY = os.getenv("API_KEY")

if not API_ENDPOINT or not API_KEY:
    print("❌ Missing API_ENDPOINT or API_KEY in environment.")
    exit(1)

headers = {
    "x-api-key": API_KEY
}

response = requests.get(API_ENDPOINT, headers=headers)
if response.status_code != 200:
    print(f"❌ Failed to fetch API: {response.status_code} - {response.text}")
    exit(1)

# Validate structure first
try:
    data = response.json()
    if "hadith" not in data or not data["hadith"]:
        print("❌ Invalid response: missing 'hadith' key.")
        exit(1)
except Exception as e:
    print(f"❌ Failed to parse JSON: {e}")
    exit(1)

# Compare hashes
json_string = response.text
file_path = "dailyhadith.json"

if os.path.exists(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        current = f.read()
        if hashlib.md5(current.encode()).hexdigest() == hashlib.md5(json_string.encode()).hexdigest():
            print("✅ Hadith content unchanged. No update needed.")
            exit(0)

# Save raw response text
with open(file_path, "w", encoding="utf-8") as f:
    f.write(json_string)
    print("✅ New hadith written to dailyhadith.json")
