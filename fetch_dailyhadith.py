import requests
import json
import os
import hashlib
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

data = response.json()
if "hadith" not in data or not data["hadith"]:
    print("❌ Invalid response: missing 'hadith' key.")
    exit(1)

# Dump the formatted JSON string
json_string = json.dumps(data, indent=4, ensure_ascii=False)

# Check if the file already exists and has the same content
file_path = "dailyhadith.json"
if os.path.exists(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        current = f.read()
        if hashlib.md5(current.encode()).hexdigest() == hashlib.md5(json_string.encode()).hexdigest():
            print("✅ Hadith content unchanged. No update needed.")
            exit(0)

# Write new content
with open(file_path, "w", encoding="utf-8") as f:
    f.write(json_string)
    print("✅ New hadith written to dailyhadith.json")
