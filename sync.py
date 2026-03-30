import os
import requests
from datetime import datetime

WRIKE_TOKEN = os.environ["WRIKE_TOKEN"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DB_ID = os.environ["NOTION_DATABASE_ID"]

# Get Wrike tasks with due dates
wrike_headers = {"Authorization": f"bearer {WRIKE_TOKEN}"}
response = requests.get(
    "https://www.wrike.com/api/v4/tasks?status=Active&fields=[dueDate,description]",
    headers=wrike_headers
)
tasks = response.json()
print("Wrike response:", tasks)

# Sort by due date soonest first (tasks with no due date go to the bottom)
def get_due_date(task):
    due = task.get("dates", {}).get("due")
    if due:
        return datetime.fromisoformat(due.replace("Z", "+00:00"))
    return datetime.max.replace(tzinfo=None)

task_list = tasks.get("data", [])
task_list.sort(key=lambda t: (t.get("dates", {}).get("due") is None, t.get("dates", {}).get("due", "")))

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
for task in task_list:
    if task["id"] in existing_ids:
        print(f"Skipping existing task: {task['title']}")
        continue

    # Build due date property if available
    due_date = task.get("dates", {}).get("due")
    properties = {
        "Name": {"title": [{"text": {"content": task["title"]}}]},
        "Wrike ID": {"rich_text": [{"text": {"content": task["id"]}}]},
        "Status": {"select": {"name": task.get("status", "Active")}}
    }
    if due_date:
        # Trim to date only (Notion expects YYYY-MM-DD)
        properties["Due Date"] = {"date": {"start": due_date[:10]}}

    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": properties
    }
    r = requests.post("https://api.notion.com/v1/pages", headers=notion_headers, json=payload)
    print(f"Added task: {task['title']} | Due: {due_date} → {r.status_code}")

print("Sync complete")
