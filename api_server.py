"""FastAPI backend with Google Gemini for legal case chat"""
import json
import asyncio
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path
import tempfile
from google import genai
from google.genai import types
import config
from search import Searcher

from aws_db import AWSStorage as StorageClient

app = FastAPI(title="Legal Case Search API")

# CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients (lazy loaded)
_searcher = None
_mongo = None
_client = None


def get_searcher():
    global _searcher
    if _searcher is None:
        _searcher = Searcher()
    return _searcher


def get_mongo():
    global _mongo
    if _mongo is None:
        _mongo = StorageClient()
    return _mongo


def get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GOOGLE_API_KEY)
    return _client


# Tool definitions
TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="search_legal_cases",
                description="Search for similar Indian legal judgments based on a query. Returns a list of relevant cases with similarity scores and snippets.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(
                            type=types.Type.STRING,
                            description="The search query describing the legal topic, case facts, or legal question"
                        ),
                        "top_k": types.Schema(
                            type=types.Type.INTEGER,
                            description="Number of results to return (default: 5)"
                        ),
                    },
                    required=["query"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_legal_case",
                description="Get the full text content of a specific legal case by its case ID",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "case_id": types.Schema(
                            type=types.Type.STRING,
                            description="The unique identifier of the legal case"
                        ),
                    },
                    required=["case_id"],
                ),
            ),
        ]
    )
]

SYSTEM_PROMPT = """You are a helpful legal research assistant specializing in Indian law. You help users find relevant legal cases and understand legal concepts.

When a user asks about legal topics or wants to find cases:
1. Use the search_legal_cases tool to find relevant cases
2. Summarize the key findings for the user
3. If the user wants more details about a specific case, use get_legal_case to retrieve the full text

Be informative but concise. When presenting search results:
- List the cases with their relevance scores
- Provide a brief description of what each case is about based on the snippet
- Offer to show the full text of any case the user is interested in

Remember: You are a research assistant, not a lawyer. Always recommend consulting a legal professional for actual legal advice."""


class ChatRequest(BaseModel):
    message: str
    conversation_history: list = []


class ChatResponse(BaseModel):
    response: str
    tool_calls: list = []


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool and return the result"""
    if tool_name == "search_legal_cases":
        query = tool_input["query"]
        top_k = tool_input.get("top_k", 5)
        searcher = get_searcher()
        results = searcher.search(query=query, top_k=top_k)
        return {"results": results}

    elif tool_name == "get_legal_case":
        case_id = tool_input["case_id"]
        mongo = get_mongo()
        case_doc = mongo.get_case(case_id)
        if case_doc:
            return {
                "case_id": case_doc["case_id"],
                "filename": case_doc.get("filename", ""),
                "page_count": case_doc.get("page_count", 0),
                "full_text": case_doc.get("full_text", "")[:10000]
            }
        else:
            return {"error": f"Case '{case_id}' not found"}

    return {"error": f"Unknown tool: {tool_name}"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint with Gemini and tool use"""
    client = get_client()

    # Build conversation history
    contents = []
    for msg in request.conversation_history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

    # Add current user message
    contents.append(types.Content(role="user", parts=[types.Part(text=request.message)]))

    tool_calls = []

    # Generate config
    generate_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=TOOLS,
    )

    # Agentic loop
    while True:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=generate_config,
        )

        # Check for function calls
        candidate = response.candidates[0]
        has_function_call = False

        for part in candidate.content.parts:
            if part.function_call:
                has_function_call = True
                fc = part.function_call
                tool_name = fc.name
                tool_input = dict(fc.args) if fc.args else {}

                # Execute the tool
                result = execute_tool(tool_name, tool_input)
                tool_calls.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "result": json.dumps(result)[:500] + "..." if len(json.dumps(result)) > 500 else json.dumps(result)
                })

                # Add model's function call to contents
                contents.append(candidate.content)

                # Add function response
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(
                        function_response=types.FunctionResponse(
                            name=tool_name,
                            response={"result": result}
                        )
                    )]
                ))
                break  # Process one function call at a time

        if not has_function_call:
            # Extract final text response
            final_text = ""
            for part in candidate.content.parts:
                if part.text:
                    final_text += part.text
            break

    return ChatResponse(
        response=final_text,
        tool_calls=tool_calls
    )


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint using SSE"""
    client = get_client()

    # Build conversation history
    contents = []
    for msg in request.conversation_history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

    # Add current user message
    contents.append(types.Content(role="user", parts=[types.Part(text=request.message)]))

    # Generate config
    generate_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=TOOLS,
    )

    async def event_generator():
        nonlocal contents
        tool_calls = []

        while True:
            # Use streaming for text generation
            accumulated_text = ""
            has_function_call = False
            function_call_data = None

            try:
                stream = client.models.generate_content_stream(
                    model="gemini-2.0-flash",
                    contents=contents,
                    config=generate_config,
                )

                for chunk in stream:
                    if chunk.candidates and chunk.candidates[0].content.parts:
                        for part in chunk.candidates[0].content.parts:
                            if part.text:
                                accumulated_text += part.text
                                yield f"data: {json.dumps({'type': 'text', 'content': part.text})}\n\n"
                                await asyncio.sleep(0)  # Allow other tasks to run
                            elif part.function_call:
                                has_function_call = True
                                function_call_data = part.function_call
                                break
                    if has_function_call:
                        break

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            if has_function_call and function_call_data:
                # Execute the tool
                fc = function_call_data
                tool_name = fc.name
                tool_input = dict(fc.args) if fc.args else {}

                # Send tool call notification
                yield f"data: {json.dumps({'type': 'tool_call', 'tool': tool_name, 'input': tool_input})}\n\n"

                # Execute tool
                result = execute_tool(tool_name, tool_input)
                tool_calls.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "result": json.dumps(result)[:500] + "..." if len(json.dumps(result)) > 500 else json.dumps(result)
                })

                # Send tool result notification
                yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'result': tool_calls[-1]['result']})}\n\n"

                # Add model's function call to contents
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part(function_call=fc)]
                ))

                # Add function response
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(
                        function_response=types.FunctionResponse(
                            name=tool_name,
                            response={"result": result}
                        )
                    )]
                ))
                # Continue the loop to get the next response
            else:
                # No function call, we're done
                break

        yield f"data: {json.dumps({'type': 'done', 'tool_calls': tool_calls})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/search")
async def search(q: str, top_k: int = 5):
    """Direct search endpoint for testing"""
    searcher = get_searcher()
    results = searcher.search(query=q, top_k=top_k)
    return {"query": q, "results": results}


@app.post("/api/search/pdf")
async def search_pdf(file: UploadFile = File(...), top_k: int = Form(5)):
    """Search using uploaded PDF"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        searcher = get_searcher()
        results = searcher.search(pdf_path=tmp_path, top_k=top_k)
        return {"filename": file.filename, "results": results}
    finally:
        tmp_path.unlink()  # Clean up temp file


@app.get("/api/case/{case_id}")
async def get_case(case_id: str):
    """Get full case text"""
    mongo = get_mongo()
    case_doc = mongo.get_case(case_id)
    if not case_doc:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    return {
        "case_id": case_doc["case_id"],
        "filename": case_doc.get("filename", ""),
        "page_count": case_doc.get("page_count", 0),
        "full_text": case_doc.get("full_text", "")
    }


@app.get("/api/download/{case_id}")
async def download_pdf(case_id: str):
    """Download PDF from GridFS"""
    mongo = get_mongo()
    result = mongo.get_pdf(case_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"PDF for case '{case_id}' not found")

    pdf_bytes, filename = result
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/cases")
async def list_cases():
    """List all available cases"""
    mongo = get_mongo()
    cases = mongo.list_cases()
    return {"cases": cases, "total": len(cases)}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    print(f"Starting API server on port {config.API_PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=config.API_PORT)
