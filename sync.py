import os
import requests

WRIKE_TOKEN = os.environ["WRIKE_TOKEN"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DB_ID = os.environ["NOTION_DATABASE_ID"]

# Get Wrike tasks
wrike_headers = {"Authorization": f"bearer {WRIKE_TOKEN}"}
tasks = requests.get("https://www.wrike.com/api/v4/tasks?status=Active", headers=wrike_headers).json()

# Get existing Notion tasks to avoid duplicates
notion_headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}
existing = requests.post(
    f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
    headers=notion_headers
).json()

existing_ids = [
    p["properties"].get("Wrike ID", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
    for p in existing.get("results", [])
]

# Sync to Notion
for task in tasks.get("data", []):
    if task["id"] in existing_ids:
        continue
    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": task["title"]}}]},
            "Wrike ID": {"rich_text": [{"text": {"content": task["id"]}}]},
            "Status": {"select": {"name": task.get("status", "Active")}}
        }
    }
    requests.post("https://api.notion.com/v1/pages", headers=notion_headers, json=payload)

print("Sync complete")
