from fastapi import FastAPI, Request
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from src.chatbot import chatbot


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

    # form_data, json_data = (None, None)
    # try:
    #     json_data = await request.json()
    # except:
    #     form_data = await request.form()
    
    # agent = create_chatbot_agent()
    # result = await agent.run(form_data.get('prompt'))
    
    # return {"received form data": form_data, "received json data": json_data, "ai": result.output}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=True)
