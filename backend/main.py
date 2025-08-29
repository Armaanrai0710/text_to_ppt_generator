from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import tempfile, os, uuid, io
from typing import Optional
from llm_router import structure_slides
from pptx_builder import build_presentation

app = FastAPI(title="Text → Styled PowerPoint", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/generate")
async def generate_pptx(
    template: UploadFile = File(...),
    text: str = Form(...),
    guidance: Optional[str] = Form(None),
    provider: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    speaker_notes: Optional[bool] = Form(False)
):
    # Security/safety: do not log any sensitive fields (especially api_key).
    if not template.filename.lower().endswith((".pptx", ".potx")):
        raise HTTPException(status_code=400, detail="Please upload a .pptx or .potx file")

    template_bytes = await template.read()
    if len(template_bytes) > 40 * 1024 * 1024:  # 40MB limit
        raise HTTPException(status_code=400, detail="Template too large (max 40MB)")

    deck = structure_slides(provider or "", api_key or None, text, guidance)
    if not speaker_notes:
        for s in deck.get("slides", []):
            s["notes"] = ""

    try:
        out_bytes = build_presentation(template_bytes, deck)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build presentation: {e}")

    # Persist to a temp file for download
    out_path = os.path.join(tempfile.gettempdir(), f"generated-{uuid.uuid4().hex}.pptx")
    with open(out_path, "wb") as f:
        f.write(out_bytes)
    return FileResponse(out_path, filename="generated.pptx", media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")

@app.get("/api/health")
async def health():
    return JSONResponse({"ok": True})

# Run: uvicorn main:app --reload --port 8000
