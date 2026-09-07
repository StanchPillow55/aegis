#!/usr/bin/env python3
import os
import re
import sys
import json
import urllib.request
import urllib.error

def parse_tasks(filepath: str):
    """Parse the markdown file and extract tasks and their descriptions."""
    tasks = []
    current_task = None

    if not os.path.exists(filepath):
        print(f"Error: File not found - {filepath}")
        return tasks

    task_pattern = re.compile(r'^-\s+\[( |x|/)\]\s+(.*)')

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            match = task_pattern.match(line)
            if match:
                if current_task:
                    tasks.append(current_task)
                title = match.group(2).strip()
                current_task = {
                    "id": "temp",
                    "title": title,
                    "description": "",
                    "goal_type": "activity",
                    "created_at": "2024-01-01T00:00:00Z"
                }
            elif current_task and line.strip():
                # Append subsequent lines as description
                current_task["description"] += line

    if current_task:
        tasks.append(current_task)

    # Clean up descriptions
    for task in tasks:
        task["description"] = task["description"].strip()

    return tasks

def send_to_api(tasks, base_url="http://localhost:8000"):
    """Send tasks to the Goals API."""
    url = f"{base_url}/api/goals"
    headers = {
        'Content-Type': 'application/json'
    }

    success_count = 0
    for task in tasks:
        data = json.dumps(task).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req) as response:
                if response.status in (200, 201):
                    print(f"Successfully added goal: {task['title']}")
                    success_count += 1
                else:
                    print(f"Failed to add goal '{task['title']}'. Status: {response.status}")
        except urllib.error.URLError as e:
            print(f"Error connecting to Aegis API: {e.reason}")
            print(f"Please ensure the server is running on {base_url}")
            sys.exit(1)

    print(f"\nImported {success_count}/{len(tasks)} tasks successfully.")

if __name__ == "__main__":
    target_file = ".kiro/specs/aegis-functional-baseline/tasks.md"
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    filepath = os.path.join(workspace_root, target_file)
    
    print(f"Parsing tasks from {filepath}...")
    tasks = parse_tasks(filepath)
    
    if not tasks:
        print("No tasks found to import.")
        sys.exit(0)
        
    print(f"Found {len(tasks)} top-level tasks.")
    
    # Just to confirm parsing logic, print first task title:
    print(f"First task: {tasks[0]['title']}")
    
    # Send them
    send_to_api(tasks)
