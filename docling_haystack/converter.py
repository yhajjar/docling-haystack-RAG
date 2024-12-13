#
# Copyright IBM Corp. 2024 - 2024
# SPDX-License-Identifier: MIT
#

"""Docling Haystack converter module."""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from docling.chunking import BaseChunk, BaseChunker, HybridChunker
from docling.datamodel.document import DoclingDocument
from docling.document_converter import DocumentConverter
from haystack import Document, component


class ExportType(str, Enum):
    """Enumeration of available export types."""

    MARKDOWN = "markdown"
    DOC_CHUNKS = "doc_chunks"


class BaseMetaExtractor(ABC):
    """BaseMetaExtractor."""

    @abstractmethod
    def extract_chunk_meta(self, chunk: BaseChunk) -> dict[str, Any]:
        """Extract chunk meta."""
        raise NotImplementedError()

    @abstractmethod
    def extract_dl_doc_meta(self, dl_doc: DoclingDocument) -> dict[str, Any]:
        """Extract Docling document meta."""
        raise NotImplementedError()


class MetaExtractor(BaseMetaExtractor):
    """MetaExtractor."""

    def extract_chunk_meta(self, chunk: BaseChunk) -> dict[str, Any]:
        """Extract chunk meta."""
        return {"chunk_json": chunk.model_dump_json()}

    def extract_dl_doc_meta(self, dl_doc: DoclingDocument) -> dict[str, Any]:
        """Extract Docling document meta."""
        return {"origin_json": dl_doc.origin.model_dump_json()} if dl_doc.origin else {}


@component
class DoclingConverter:
    """Docling Haystack converter."""

    def __init__(
        self,
        converter: Optional[DocumentConverter] = None,
        convert_kwargs: Optional[dict[str, Any]] = None,
        export_type: ExportType = ExportType.DOC_CHUNKS,
        md_export_kwargs: Optional[dict[str, Any]] = None,
        chunker: Optional[BaseChunker] = None,
        meta_extractor: Optional[BaseMetaExtractor] = None,
    ):
        """Create a Docling Haystack converter."""
        self._converter = converter or DocumentConverter()
        self._convert_kwargs = convert_kwargs if convert_kwargs is not None else {}
        self._export_type = export_type
        self._md_export_kwargs = (
            md_export_kwargs
            if md_export_kwargs is not None
            else {"image_placeholder": ""}
        )
        if self._export_type == ExportType.DOC_CHUNKS:
            # TODO remove tokenizer once docling-core ^2.10.0 guaranteed via docling:
            self._chunker = chunker or HybridChunker(
                tokenizer="sentence-transformers/all-MiniLM-L6-v2"
            )
        self._meta_extractor = meta_extractor or MetaExtractor()

    @component.output_types(documents=list[Document])
    def run(
        self,
        paths: Iterable[Union[Path, str]],
    ):
        """Run the component.

        Args:
            paths (Iterable[Union[Path, str]]): _description_

        Raises:
            RuntimeError: _description_

        Returns:
            _type_: _description_
        """
        documents: list[Document] = []
        for filepath in paths:
            dl_doc = self._converter.convert(
                source=filepath,
                **self._convert_kwargs,
            ).document

            if self._export_type == ExportType.DOC_CHUNKS:
                chunk_iter = self._chunker.chunk(dl_doc=dl_doc)
                hs_docs = [
                    Document(
                        content=self._chunker.serialize(chunk=chunk),
                        meta=self._meta_extractor.extract_chunk_meta(chunk=chunk),
                    )
                    for chunk in chunk_iter
                ]
                documents.extend(hs_docs)
            elif self._export_type == ExportType.MARKDOWN:
                hs_doc = Document(
                    content=dl_doc.export_to_markdown(**self._md_export_kwargs),
                    meta=self._meta_extractor.extract_dl_doc_meta(dl_doc=dl_doc),
                )
                documents.append(hs_doc)
            else:
                raise RuntimeError(f"Unexpected export type: {self._export_type}")
        return {"documents": documents}
