import os
import requests
from datetime import datetime, timezone

WRIKE_TOKEN = os.environ["WRIKE_TOKEN"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DB_ID = os.environ["NOTION_DATABASE_ID"]

today = datetime.now(timezone.utc).date()

# Get Wrike tasks with due dates
wrike_headers = {"Authorization": f"bearer {WRIKE_TOKEN}"}
response = requests.get(
    "https://www.wrike.com/api/v4/tasks?status=Active&fields=[dueDate]",
    headers=wrike_headers
)
tasks = response.json()

# Filter to only future due dates
task_list = []
for task in tasks.get("data", []):
    due = task.get("dates", {}).get("due")
    if not due:
        continue
    due_date = datetime.fromisoformat(due.replace("Z", "+00:00")).date()
    if due_date >= today:
        task["_due_date"] = due_date
        task_list.append(task)

# Sort soonest first
task_list.sort(key=lambda t: t["_due_date"])
print(f"Found {len(task_list)} upcoming tasks with due dates")

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

# Build lookup by Wrike ID and by name
existing_by_wrike_id = {}
existing_by_name = {}
for p in existing.get("results", []):
    try:
        page_id = p["id"]
        rich_text = p["properties"].get("Wrike ID", {}).get("rich_text", [])
        name = p["properties"].get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "")
        if rich_text:
            existing_by_wrike_id[rich_text[0]["text"]["content"]] = page_id
        if name:
            existing_by_name[name] = page_id
    except (IndexError, KeyError):
        continue

# Sync to Notion
for task in task_list:
    due_str = task["_due_date"].isoformat()
    properties = {
        "Name": {"title": [{"text": {"content": task["title"]}}]},
        "Wrike ID": {"rich_text": [{"text": {"content": task["id"]}}]},
        "Status": {"select": {"name": task.get("status", "Active")}},
        "Due Date": {"date": {"start": due_str}}
    }

    # If already exists by Wrike ID or name, update it
    page_id = existing_by_wrike_id.get(task["id"]) or existing_by_name.get(task["title"])
    if page_id:
        r = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=notion_headers,
            json={"properties": properties}
        )
        print(f"Updated: {task['title']} | Due: {due_str} → {r.status_code}")
    else:
        r = requests.post(
            "https://api.notion.com/v1/pages",
            headers=notion_headers,
            json={"parent": {"database_id": NOTION_DB_ID}, "properties": properties}
        )
        print(f"Added: {task['title']} | Due: {due_str} → {r.status_code}")

print("Sync complete")
