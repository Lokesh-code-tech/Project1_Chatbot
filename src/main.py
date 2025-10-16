from fastapi import FastAPI, Request, BackgroundTasks
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from src.chatbot import chatbot, created_files
import os
from fastapi.responses import JSONResponse
import asyncio
import json
import requests
import base64
import time

from collections import defaultdict

# Global task histories - initialized ONCE when module loads
if 'task_histories' not in globals():
    task_histories = {}

print(f"🔧 Initialized task_histories: {id(task_histories)}")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
app = FastAPI(title="CORS Enabled FastAPI App")

# Enable CORS for all domains, methods, and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],          # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],          # Allow all headers
)


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <form action="/ask" method="POST">
        Prompt: <input type="text" name="prompt">
        
        <button type="submit"> Ask </button>
    </form>
    """

@app.post("/ask")
async def ask(request: Request):

    form_data = await request.form()
    prompt = form_data.get('prompt')
    result = await chatbot.run(prompt)

    return {"form_data": form_data, "prompt": prompt, "ai": result.output}


# Store message histories per task (global or class-level)
async def write_code_with_llm(
    task_brief: str, 
    task_id: str,  # NEW: Unique identifier for the task
    round: int = 1,  # NEW: Round number (1 or 2)
    checks: list = None, 
    attachments: list = None
):

    global task_histories
    
    # Clear the shared created_files dictionary
    created_files.clear()

    print(f"🔍 Current task_histories keys: {list(task_histories.keys())}")
    print(f"🔍 Memory address: {id(task_histories)}")
    
    # Get or create message history for this specific task
    if round == 1:
        # Round 1: Start fresh history for new task
        task_histories[task_id] = []
        print(f"🆕 Starting new task: {task_id}")
    elif round == 2:
        # Round 2: Continue with existing history from Round 1
        if task_id not in task_histories:
            raise ValueError(f"No Round 1 history found for task: {task_id}")
        print(f"🔄 Continuing task: {task_id} (Round {round})")
    
    # Get the message history for this task
    message_history = task_histories[task_id]
    
    # Build enhanced prompt
    enhanced_prompt = f"{task_brief}\n\n"
    
    # Add round information
    if round == 2:
        enhanced_prompt = f"[ROUND 2 - UPDATE REQUEST]\n{enhanced_prompt}"
        enhanced_prompt += "Build upon the previous implementation and make the requested changes.\n\n"
    
    # Add checks to the prompt
    if checks and len(checks) > 0:
        enhanced_prompt += "IMPORTANT REQUIREMENTS (All must be satisfied):\n"
        for i, check in enumerate(checks, 1):
            enhanced_prompt += f"{i}. {check}\n"
        enhanced_prompt += "\n"
    
    # Add attachment information
    if attachments and len(attachments) > 0:
        enhanced_prompt += "ATTACHMENTS PROVIDED:\n"
        for attachment in attachments:
            att_name = attachment.get("name", "unknown")
            att_url = attachment.get("url", "")
            
            if att_url.startswith("data:"):
                mime_type = att_url.split(";")[0].replace("data:", "")
                enhanced_prompt += f"- {att_name} ({mime_type}) - Use this in your application\n"
            else:
                enhanced_prompt += f"- {att_name} (URL: {att_url})\n"
        enhanced_prompt += "\nIncorporate these attachments appropriately in your application.\n\n"
    
    print(f"📝 Enhanced Prompt (Round {round}):\n{enhanced_prompt}")
    print(f"📊 Current history length: {len(message_history)} messages")
    
    # Run chatbot with task-specific history
    result = await chatbot.run(
        enhanced_prompt,
        message_history=message_history
    )
    
    # Update the task-specific history
    message_history.extend(result.new_messages())
    task_histories[task_id] = message_history
    
    print(f"✅ Updated history length: {len(message_history)} messages")
    
    return {
        "result": result.output,
        "files": created_files,
        "task_id": task_id,
        "round": round
    }



def create_github_repo(repo_name: str):
    payload = {"name": repo_name, "private": False, "auto_init": False, "license_template": "mit"}
    
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}",
               "Accept": "application/vnd.github+json"}
    
    response = requests.post("https://api.github.com/user/repos",
                  headers=headers,
                  json=payload)
    
    if response.status_code != 201:
        raise Exception(f"Failed to create repo: {response.status_code} {response.text}")
    else:
        return response.json()
    
def get_sha_of_latest_commit(repo: str, branch: str="main") -> str:
    response = requests.get(f"https://api.github.com/repos/Lokesh-code-tech/{repo}/commits/{branch}")
    if response.status_code != 200:
        raise Exception(f"Failed to get latest commit: {response.status_code} {response.text}")
    return response.json().get("sha")        
    

def push_files_to_repo(repo_name: str, files: dict[str, dict], round: int = 1) -> bool:
    """
    Push multiple files to GitHub repository
    
    Args:
        repo_name: Name of the GitHub repository
        files: Dictionary from created_files {filename: {path, content, directory}}
        round: Round number (1 for initial commit, 2+ for updates/changes)
    
    Returns:
        bool: True if all files pushed successfully, False otherwise
    """
    success = True
    
    
    for filename, file_data in files.items():
        content = file_data.get("content", "")
        
        # Encode content to base64
        if isinstance(content, bytes):
            content_encoded = base64.b64encode(content).decode('utf-8')
        else:
            content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        # Check if file already exists (to get SHA for updates)
        get_url = f"https://api.github.com/repos/Lokesh-code-tech/{repo_name}/contents/{filename}"
        get_response = requests.get(
            get_url,
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json"
            }
        )
        
        # Prepare payload
        commit_message = f"Update {filename}" if round == 2 else f"Add {filename}"
        payload = {
            "message": commit_message,
            "content": content_encoded,
            "branch": "main"
        }
        
        # If file exists, include SHA for update
        if get_response.status_code == 200:
            payload["sha"] = get_response.json()["sha"]
        
        # Push file
        response = requests.put(
            get_url,
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json"
            },
            json=payload
        )
        
        if response.status_code in [200, 201]:
            action = "Updated" if round == 2 else "Pushed"
            print(f"✓ {action} {filename}")
        else:
            print(f"✗ Failed to push {filename}: {response.status_code} {response.text}")
            success = False
    
    return success


def enable_github_pages(repo: str):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}",
               "Accept": "application/vnd.github+json"}   

    payload = {"build_type": "legacy", "source": {"branch": "main", "path": "/"}}

    response = requests.post(f"https://api.github.com/repos/Lokesh-code-tech/{repo}/pages",
                             headers=headers,
                             json=payload)

    if response.status_code != 201:
        raise Exception(f"Failed to enable GitHub Pages: {response.status_code} {response.text}")
    
def verify_repo_exists(repo_name: str) -> bool:
    """Check if repository was created successfully"""
    url = f"https://api.github.com/repos/Lokesh-code-tech/{repo_name}"
    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }
    )
    
    if response.status_code == 200:
        print(f"✓ Repository {repo_name} exists")
        return True
    else:
        print(f"✗ Repository {repo_name} not found: {response.status_code}")
        print(f"Response: {response.text}")
        return False

  


async def process_task(task_data: dict):
    round_num = task_data.get("round", 1)
    task_id = task_data['task'].strip().replace(" ", "_")
    repo_name = f"TDS_Project1_{task_id}"
    repo_name = repo_name.lower().strip()

    
    
    print(f"🔄 Processing Round {round_num}")
    
    # Extract checks and attachments
    checks = task_data.get("checks", [])
    attachments = task_data.get("attachments", [])
    
    print(f"📋 Checks: {len(checks)} requirements")
    print(f"📎 Attachments: {len(attachments)} files")
    
    # Step 1: Generate code with LLM (pass checks and attachments)
    output = await write_code_with_llm(
        task_brief=task_data.get("brief", "No brief provided"),
        task_id=task_id,  # Pass the task identifier
        round=round_num,  # Pass the round number
        checks=checks,
        attachments=attachments
    )
    print("✓ LLM Output is done")
    
    # Rest of your code remains the same...
    # Step 2: Create repository (Round 1 only)
    if round_num == 1:
        create_github_repo(repo_name)
        print("✓ Repo Created")
        time.sleep(15)
    else:
        print("ℹ️  Skipping repo creation (Round 2)")



    if not verify_repo_exists(repo_name):
        raise Exception(f"Repository {repo_name} must be created first")    
    
    # Step 3: Push files
    files = output.get("files", {})
    if not files:
        print("⚠️  No files to push!")
        return {"error": "No files generated"}
    
    push_files_to_repo(repo_name, files, round=round_num)
    print(f"✓ Files {'Pushed' if round_num == 1 else 'Updated'}")
    
    # Step 4: Enable Pages (Round 1 only)
    if round_num == 1:
        time.sleep(3)
        enable_github_pages(repo_name)
        print("✓ GitHub Pages Enabled")
    
    # Step 5: Get commit SHA
    time.sleep(150)
    commit_sha = get_sha_of_latest_commit(repo_name, branch="main")
    print(f"✓ Latest Commit SHA: {commit_sha}")
    
    # Step 6: Send evaluation
    evaluation_payload = {
        "email": task_data.get("email"),
        "task": task_data.get("task"),
        "round": round_num,
        "nonce": task_data.get("nonce"),
        "repo_url": f"https://github.com/Lokesh-code-tech/{repo_name}",
        "commit_sha": commit_sha,
        "pages_url": f"https://Lokesh-code-tech.github.io/{repo_name}/"
    }
    
    print(f"📤 Sending Round {round_num} evaluation")
    
    try:
        evaluation_response = requests.post(
            task_data.get("evaluation_url"),
            json=evaluation_payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=10
        )
        
        print(f"✓ Evaluation response: {evaluation_response.status_code}")
        
        try:
            eval_response_data = evaluation_response.json()
        except:
            eval_response_data = evaluation_response.text or "Success"
        
        return {
            "status": "success",
            "round": round_num,
            "repo_name": repo_name,
            "pages_url": f"https://Lokesh-code-tech.github.io/{repo_name}/",
            "commit_sha": commit_sha,
            "files_created": list(files.keys()),
            "checks_provided": len(checks),
            "attachments_provided": len(attachments),
            "evaluation_response": eval_response_data
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }



@app.post("/handle_task")
async def handle_task(data: dict, background_tasks: BackgroundTasks):
    if data.get("secret") == os.getenv("secret"):
        background_tasks.add_task(process_task, task_data=data)
        return {"status_code": 200, "status": "Task received"}
    else:
        return JSONResponse(status_code=403, content={"message": "Incorrect secret"})
 



if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=True)
