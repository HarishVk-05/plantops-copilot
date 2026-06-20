import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.rag.document_classifier import get_document_category

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"
MANUALS_DIR = RAW_DIR / "manuals"
TICKETS_DIR = RAW_DIR / "tickets"

VECTOR_DIR = BASE_DIR / "data" / "processed" / "chroma_db"

DEFAULT_COLLECTION_NAME = "plantops_documents"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    metadata: Dict[str, str]

def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def detect_source_type(path: Path) -> str:
    parts = {p.lower() for p in path.parts}

    if "manuals" in parts:
        return "manual"
    if "tickets" in parts:
        return "maintenance_ticket"
    
    return "unknown"

def extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.replace("#", "").strip()
    return fallback

def split_markdown_sections(text: str) -> List[Dict[str, str]]:
    """
    Splits markdown-like documents into heading-aware sections.
    
    Returns:
        [
            {
                "heading": "Section heading",
                "content": "section text"
            }
        ]
    """
    lines = text.splitlines()

    sections = []
    current_heading = "Document"
    current_lines = []

    heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$")

    for line in lines:
        match = heading_pattern.match(line.strip())

        if match:
            if current_lines:
                sections.append(
                    {
                        "heading": current_heading,
                        "content": "\n".join(current_lines).strip()
                    }
                )
            current_heading = match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    
    if current_lines:
        sections.append(
            {
                "heading": current_heading,
                "content": "\n".join(current_lines).strip()
            }
        )
    return [section for section in sections if section["content"]]

def chunk_text_by_words(
        text: str,
        max_words: int = 200,
        overlap_words: int = 50
    ) -> List[str]:
    """
    Word based chunking with overlap.
    
    Might change it later with better chunking mechanism.
    """
    words = text.split()

    if len(words) <= max_words:
        return[text.strip()]
    
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + max_words, len(words))
        chunk = " ".join(words[start:end]).strip()

        if chunk:
            chunks.append(chunk)
        
        if end == len(words):
            break

        start = end - overlap_words
        start = max(start, 0)
    
    return chunks

def extract_machine_id(text: str) -> str:
    machine_ids = list(
        dict.fromkeys(
            re.findall(
                r"\b[A-Z]{3}-[A-Z0-9]+\b",
                text
            )
        )
    )
    if len(machine_ids) == 1:
        return machine_ids[0]
    
    if not machine_ids:
        return "GLOBAL"
    
    return "MULTI"

def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def load_documents() -> List[Path]:
    supported_extensions = {".md", ".txt"}

    paths = []

    for folder in [MANUALS_DIR, TICKETS_DIR]:
        if not folder.exists():
            continue

        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in supported_extensions:
                paths.append(path)
    
    return sorted(paths)

def build_chunks(
        max_words: int = 200,
        overlap_words: int = 50
    ) -> List[DocumentChunk]:
    chunks: List[DocumentChunk] = []

    document_paths = load_documents()

    for path in document_paths:
        raw_text = read_text_file(path)
        text = clean_text(raw_text)

        if not text:
            continue

        source_type = detect_source_type(path)
        title = extract_title(text, fallback=path.stem)
        document_category = get_document_category(path.name)
        machine_id = extract_machine_id(text)
        sections = split_markdown_sections(text)

        for section_index, section in enumerate(sections):
            section_heading = section["heading"]
            section_content = clean_text(section["content"])

            section_chunks = chunk_text_by_words(
                section_content,
                max_words=max_words,
                overlap_words=overlap_words
            )

            for chunk_index, chunk_text in enumerate(section_chunks):
                chunk_fingerprint = stable_hash(
                    f"{path.name}|{section_heading}|{chunk_index}|{chunk_text}"
                )

                chunk_id = f"{path.stem}_{section_index}_{chunk_index}_{chunk_fingerprint}"

                metadata = {
                    "source_file": path.name,
                    "source_path": str(path.relative_to(BASE_DIR)),
                    "source_type": source_type,
                    "document_category": document_category,
                    "machine_id": machine_id,
                    "document_title": title,
                    "heading": section_heading,
                    "section_index": str(section_index),
                    "chunk_index": str(chunk_index)
                }

                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        text=chunk_text,
                        metadata=metadata
                    )
                )
    return chunks

def get_chroma_collection(
        collection_name: str,
        embedding_model: str,
        reset: bool = False
    ):
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    embedding_function = SentenceTransformerEmbeddingFunction(
        model_name=embedding_model
    )

    client = chromadb.PersistentClient(path=str(VECTOR_DIR))

    if reset:
        try:
            client.delete_collection(collection_name)
            print(f"Deleted existing collection: {collection_name}")
        except Exception:
            pass
    
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )

    return collection

def index_chunks(
        chunks: List[DocumentChunk],
        collection_name: str,
        embedding_model: str,
        reset: bool = False
    ):
    collection = get_chroma_collection(
        collection_name=collection_name,
        embedding_model=embedding_model,
        reset=reset
    )

    if not chunks:
        print("No chunks found. Make sure data/raw/manuals and data/raw/tickets exist.")
        return
    
    ids = [chunk.chunk_id for chunk in chunks]
    documents = [chunk.text for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    print(f"indexed {len(chunks)} chunks into ChromaDB.")
    print(f"Vector DB path: {VECTOR_DIR}")
    print(f"Collection name: {collection_name}")
    print(f"Embedding model: {embedding_model}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build ChromaDB vector index for PlantOps Copilot documents."
    )

    parser.add_argument(
        "--collection-name",
        default = DEFAULT_COLLECTION_NAME,
        help = "ChromaDB collection name."
    )

    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBEDDING_MODEL,
        help="SentenceTransformer embedding model name,"
    )

    parser.add_argument(
        "--max-words",
        type=int,
        default=200,
        help="Maximum words per chunk."
    )

    parser.add_argument(
        "--overlap-words",
        type=int,
        default=50,
        help="Word Overlap between chunks."
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing collection before indexing."
    )

    args = parser.parse_args()

    print("Building document chunks...")

    chunks = build_chunks(
        max_words=args.max_words,
        overlap_words=args.overlap_words
    )

    print(f"Found {len(chunks)} chunks.")

    index_chunks(
        chunks=chunks,
        collection_name=args.collection_name,
        embedding_model=args.embedding_model,
        reset=args.reset
    )

if __name__ == "__main__":
    main()