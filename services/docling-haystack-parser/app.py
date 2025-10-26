import os, tempfile, shutil
from functools import lru_cache
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.responses import JSONResponse

from docling_haystack.converter import DoclingConverter, ExportType
from docling.chunking import HybridChunker

API_KEY = os.getenv("PARSER_API_KEY", "")
DEFAULT_EMBED_MODEL = os.getenv("EMBED_MODEL_ID", "sentence-transformers/all-MiniLM-L6-v2")

app = FastAPI(title="Docling ↔ Haystack Parser")


def auth_guard(x_api_key: Optional[str]):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "Unauthorized")


def parse_export_type(value: Optional[str]) -> ExportType:
    v = (value or "").strip().upper()
    return ExportType.DOC_CHUNKS if v in {"DOC_CHUNKS", "DOCCHUNKS", "CHUNKS", "DOCS"} else ExportType.MARKDOWN


@lru_cache(maxsize=4)
def get_converter(et: ExportType, model: str = DEFAULT_EMBED_MODEL) -> DoclingConverter:
    # Build (and cache) a converter per export type / model
    return DoclingConverter(
        export_type=et,                  # DOC_CHUNKS or MARKDOWN
        chunker=HybridChunker(tokenizer=model),
    )


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/convert")
async def convert(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    export_type: Optional[str] = Form("DOC_CHUNKS"),
    x_api_key: Optional[str] = Header(None, alias="X-Api-Key"),
):
    auth_guard(x_api_key)

    if not file and not url:
        raise HTTPException(400, "Provide either 'file' or 'url'.")

    et = parse_export_type(export_type)
    converter = get_converter(et)

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

        try:
            result = converter.run(paths=paths)  # {"documents": [Haystack Document, ...]}
        except Exception as e:
            # Helpful fallback: if user uploaded HTML and asked for DOC_CHUNKS, retry as MARKDOWN
            if file and file.filename.lower().endswith((".html", ".htm")) and et != ExportType.MARKDOWN:
                result = get_converter(ExportType.MARKDOWN).run(paths=paths)
            else:
                raise HTTPException(500, f"Docling conversion failed: {e}")

        docs = result.get("documents", [])
        out = [
            {
                "id": getattr(d, "id", None),
                "content": d.content,
                "meta": (getattr(d, "meta", {}) or {}),
            }
            for d in docs
        ]
        return JSONResponse({"count": len(out), "documents": out})

    finally:
        if tmpdir and os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)
