import io
from typing import List, Tuple
import streamlit as st
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
from PyPDF2 import PdfReader
from .config import RAG_EMBED_MODEL, EMBED_DIM


@st.cache_resource
def load_embedder():
    """Load sentence-transformer model once per session."""
    return SentenceTransformer(RAG_EMBED_MODEL)


def extract_text_from_pdf(file) -> str:
    """Extract plain text from a PDF file-like object."""
    reader = PdfReader(io.BytesIO(file.read()))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text += page_text + "\n"
    return text


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split long text into overlapping word chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += max(chunk_size - overlap, 1)
    return chunks


class SimpleVectorStore:
    """Lightweight in-memory vector store using FAISS."""

    def __init__(self):
        self.index = None
        self.embeddings = None
        self.chunks: List[str] = []

    def build_index(self, chunks: List[str]):
        if not chunks:
            return
        model = load_embedder()
        self.chunks = chunks
        embeddings = model.encode(chunks, show_progress_bar=False)
        self.embeddings = embeddings.astype("float32")
        dim = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(self.embeddings)

    def similarity_search(self, query: str, k: int = 4) -> List[Tuple[str, float]]:
        """Return top-k (chunk, distance) pairs."""
        if self.index is None:
            return []
        model = load_embedder()
        q_emb = model.encode([query]).astype("float32")
        distances, indices = self.index.search(q_emb, k)
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if 0 <= idx < len(self.chunks):
                results.append((self.chunks[idx], float(dist)))
        return results


def build_vectorstore_from_uploads(uploaded_files):
    """Extract, chunk, embed uploaded PDFs and return a vector store."""
    text = ""
    for f in uploaded_files:
        try:
            text += extract_text_from_pdf(f)
        except Exception:
            st.error(f"Could not read PDF: {getattr(f, 'name', 'unnamed file')}")

    if not text.strip():
        return None

    chunks = chunk_text(text)
    store = SimpleVectorStore()
    store.build_index(chunks)
    return store
