import os
import requests

WRIKE_TOKEN = os.environ["WRIKE_TOKEN"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DB_ID = os.environ["NOTION_DATABASE_ID"]

# Get Wrike tasks
wrike_headers = {"Authorization": f"bearer {WRIKE_TOKEN}"}
response = requests.get("https://www.wrike.com/api/v4/tasks?status=Active", headers=wrike_headers)
tasks = response.json()
print("Wrike response:", tasks)

# Get existing Notion tasks
notion_headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}
existing_response = requests.post(
    f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
    headers=notion_headers
)
existing = existing_response.json()
print("Notion response:", existing)

# Safely build existing IDs list
existing_ids = []
for p in existing.get("results", []):
    try:
        rich_text = p["properties"].get("Wrike ID", {}).get("rich_text", [])
        if rich_text:
            existing_ids.append(rich_text[0]["text"]["content"])
    except (IndexError, KeyError):
        continue

print("Existing Wrike IDs in Notion:", existing_ids)

# Sync to Notion
for task in tasks.get("data", []):
    if task["id"] in existing_ids:
        print(f"Skipping existing task: {task['title']}")
        continue
    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": task["title"]}}]},
            "Wrike ID": {"rich_text": [{"text": {"content": task["id"]}}]},
            "Status": {"select": {"name": task.get("status", "Active")}}
        }
    }
    r = requests.post("https://api.notion.com/v1/pages", headers=notion_headers, json=payload)
    print(f"Added task: {task['title']} → {r.status_code}")

print("Sync complete")
