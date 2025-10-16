
# from pydantic_ai import Agent

# chatbot = Agent('openai:gpt-5-nano',system_prompt="You answer concise.")


# result1 = chatbot_agent.run_sync("My name is Lokesh")
# result2 = chatbot_agent.run_sync("What is my name?",message_history=result1.all_messages())

# print(result1.output)
# print("--------------------------------")
# print(result2.output)


# print(result2.all_messages_json())





from pydantic_ai import Agent
from pathlib import Path
from pydantic import BaseModel
import asyncio


class FileCreationOutput(BaseModel):
    files_created: list[str]
    status: str
    next_steps: str


# Create agent first
# chatbot = Agent(
#     'openai:gpt-5-nano',
#     system_prompt="""
#     You are a development assistant that creates COMPLETE, CLIENT-SIDE web applications for GitHub Pages deployment
    
#     MUST create:
#     - index.html (HTML5 structure)
#     - styles.css (responsive design)
#     - script.js (client-side functionality)
#     - README.md (summary, setup, usage, code explanation, license)
    
#     Requirements:
#     - Only HTML, CSS, JavaScript (no backend, no .py, no Node.js)
#     - Use localStorage for data persistence
#     - Mobile-responsive and production-ready
#     - Works by opening index.html in browser
    
#     Do NOT create: requirements.txt, package.json, server files, databases
#     """,
#     output_type=FileCreationOutput
# )


chatbot = Agent(
    'openai:gpt-5-nano',  # Better model than gpt-5-nano
    system_prompt="""You are an expert web developer creating complete, production-ready static websites for GitHub Pages.

MANDATORY OUTPUT - Generate exactly 4 files:
1. index.html - Complete HTML5 with semantic structure
2. styles.css - Modern, mobile-first responsive CSS
3. script.js - Vanilla JavaScript with all required functionality
4. README.md - Provide summary, setup, usage, code explanation, license

TECHNICAL REQUIREMENTS:
- Pure HTML/CSS/JavaScript only (no frameworks, no backend)
- Use localStorage for data persistence
- Include error handling and input validation
- Mobile-responsive (works on phone, tablet, desktop)
- All functionality must work by opening index.html directly in browser

CODE QUALITY STANDARDS:
- Write clean, commented code with clear variable names
- Follow best practices (DRY, separation of concerns)
- Handle edge cases (empty data, invalid input, missing files)
- Add loading states and user feedback for all interactions

FILE PROCESSING:
- When CSV attachments provided: parse and display data properly
- When images provided: embed using data URLs or external links
- Read files using Fetch API or FileReader for client-side processing

ABSOLUTELY FORBIDDEN:
- No server-side code (Python, Node.js, PHP)
- No package.json, requirements.txt, or dependency files
- No databases or external APIs requiring keys
- No build tools or compilation steps

Make every application fully functional, visually appealing, and ready to deploy to GitHub Pages immediately.""",
    output_type=FileCreationOutput
)



created_files = {}

@chatbot.tool_plain
async def create_file(filename: str, content: str, directory: str = ".") -> str:
    """Create a file with specified content"""
    global created_files
    
    file_path = Path(directory) / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Store the file content for later retrieval
    created_files[filename] = {
        "path": str(file_path),
        "content": content,
        "directory": directory
    }
    
    return f"File {filename} created successfully at {file_path}"


@chatbot.tool_plain
async def create_file_from_data_url(filename: str, data_url: str) -> str:
    """
    Create a file from a data URL (base64 encoded)
    Used for processing attachments like images
    """
    global created_files
    
    import base64
    import re
    
    # Parse data URL: data:image/png;base64,iVBORw...
    match = re.match(r'data:([^;]+);base64,(.+)', data_url)
    
    if not match:
        return f"Invalid data URL format for {filename}"
    
    mime_type = match.group(1)
    base64_data = match.group(2)
    
    # Decode base64
    file_content = base64.b64decode(base64_data)
    
    # Save file
    file_path = Path(filename)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'wb') as f:  # Binary mode for images
        f.write(file_content)
    
    # Store in created_files
    created_files[filename] = {
        "path": str(file_path),
        "content": file_content,  # Store as bytes
        "directory": ".",
        "mime_type": mime_type
    }
    
    return f"File {filename} created from data URL ({mime_type})"



@chatbot.tool_plain
async def execute_python_code(code: str) -> str:
    """Execute Python code safely"""
    try:
        exec(code)
        return "Code executed successfully"
    except Exception as e:
        return f"Error executing code: {str(e)}"




