import os, tempfile, shutil
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.responses import JSONResponse
from docling_haystack.converter import DoclingConverter, ExportType
from docling.chunking import HybridChunker

API_KEY = os.getenv("PARSER_API_KEY", "")
DEFAULT_EMBED_MODEL = os.getenv("EMBED_MODEL_ID", "sentence-transformers/all-MiniLM-L6-v2")

def make_converter(export_type: ExportType):
    return DoclingConverter(
        export_type=export_type,                 # DOC_CHUNKS or MARKDOWN
        chunker=HybridChunker(tokenizer=DEFAULT_EMBED_MODEL),
    )

converter = make_converter(ExportType.DOC_CHUNKS)
app = FastAPI(title="Docling ↔ Haystack Parser")

def auth_guard(x_api_key: Optional[str]):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "Unauthorized")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/convert")
async def convert(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    export_type: Optional[str] = Form("DOC_CHUNKS"),
    x_api_key: Optional[str] = Header(None, convert_underscores=False)
):
    auth_guard(x_api_key)

    if not file and not url:
        raise HTTPException(400, "Provide either 'file' or 'url'.")

    et = ExportType.DOC_CHUNKS if export_type.upper() == "DOC_CHUNKS" else ExportType.MARKDOWN
    global converter
    if converter.export_type != et:
        converter = make_converter(et)

    paths: List[str] = []
    tmpdir = None
    try:
        if file:
            tmpdir = tempfile.mkdtemp(prefix="docling_")
            fpath = os.path.join(tmpdir, file.filename)
            with open(fpath, "wb") as out:
                out.write(await file.read())
            paths = [fpath]
        else:
            paths = [url]

        result = converter.run(paths=paths)   # {"documents": [Haystack Document, ...]}
        docs = result.get("documents", [])
        out = [{"id": getattr(d, "id", None), "content": d.content, "meta": getattr(d, "meta", {}) or {}} for d in docs]
        return JSONResponse({"count": len(out), "documents": out})
    finally:
        if tmpdir and os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)
