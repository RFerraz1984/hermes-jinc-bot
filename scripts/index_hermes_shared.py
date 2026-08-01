#!/usr/bin/env python3
"""
Mini-RAG local para /opt/data/hermes-shared
Indexa todos os arquivos de texto/markdown/PDF na pasta e subpastas.
Gera embeddings locais (sentence-transformers) + busca semântica simples.
Salva índice em /opt/data/hermes-shared/.rag-index/

Uso:
    python3 index_hermes_shared.py          # indexa tudo (incremental)
    python3 index_hermes_shared.py --query "capacitismo algorítmico"  # busca
    python3 index_hermes_shared.py --reindex  # força reindexação total
"""

import os
import json
import hashlib
import pickle
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
except ImportError:
    SentenceTransformer = None
    np = None

# Config
SHARED_ROOT = Path("/opt/data/hermes-shared")
INDEX_DIR = SHARED_ROOT / ".rag-index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDINGS_FILE = INDEX_DIR / "embeddings.pkl"
METADATA_FILE = INDEX_DIR / "metadata.json"
HASHES_FILE = INDEX_DIR / "file_hashes.json"

# Modelo de embeddings (leve, multilingue, bom para PT)
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 500  # tokens aproximados
CHUNK_OVERLAP = 50

# Extensões suportadas
SUPPORTED_EXTS = {".txt", ".md", ".markdown", ".pdf", ".json", ".csv"}


def get_file_hash(path: Path) -> str:
    """SHA256 do conteúdo do arquivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_text_from_pdf(path: Path) -> str:
    """Extrai texto de PDF via PyMuPDF."""
    if not fitz:
        return ""
    text_parts = []
    try:
        doc = fitz.open(str(path))
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
    except Exception as e:
        print(f"[WARN] Falha ao extrair {path}: {e}")
    return "\n".join(text_parts)


def extract_text_from_file(path: Path) -> str:
    """Extrai texto conforme extensão."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext in {".txt", ".md", ".markdown", ".json", ".csv"}:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="latin-1")
            except Exception as e:
                print(f"[WARN] Falha ao ler {path}: {e}")
                return ""
    return ""


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Divide texto em chunks com overlap (aprox. por palavras)."""
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def load_hashes() -> Dict[str, str]:
    if HASHES_FILE.exists():
        try:
            return json.loads(HASHES_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_hashes(hashes: Dict[str, str]):
    HASHES_FILE.write_text(json.dumps(hashes, indent=2))


def load_index() -> tuple:
    """Carrega embeddings e metadados existentes."""
    if EMBEDDINGS_FILE.exists() and METADATA_FILE.exists():
        try:
            with open(EMBEDDINGS_FILE, "rb") as f:
                embeddings = pickle.load(f)
            metadata = json.loads(METADATA_FILE.read_text())
            return embeddings, metadata
        except Exception as e:
            print(f"[WARN] Falha ao carregar índice existente: {e}")
    return None, []


def save_index(embeddings, metadata: List[Dict]):
    with open(EMBEDDINGS_FILE, "wb") as f:
        pickle.dump(embeddings, f)
    METADATA_FILE.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))


def get_model():
    """Carrega modelo de embeddings (lazy)."""
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers não instalado. Rode: uv pip install sentence-transformers")
    return SentenceTransformer(MODEL_NAME)


def index_files(force_reindex: bool = False) -> Dict[str, int]:
    """Indexa todos os arquivos suportados em SHARED_ROOT."""
    print(f"[INDEX] Iniciando indexação em {SHARED_ROOT}")
    print(f"[INDEX] Diretório do índice: {INDEX_DIR}")

    # Carrega estado anterior
    old_hashes = {} if force_reindex else load_hashes()
    embeddings, metadata = (None, []) if force_reindex else load_index()

    model = get_model()
    new_hashes = {}
    new_chunks = []
    new_metadata = []
    stats = {"files_scanned": 0, "files_indexed": 0, "chunks_created": 0, "files_skipped": 0, "errors": 0}

    for file_path in SHARED_ROOT.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTS:
            continue
        if ".rag-index" in file_path.parts:
            continue

        stats["files_scanned"] += 1
        rel_path = file_path.relative_to(SHARED_ROOT)
        file_hash = get_file_hash(file_path)
        new_hashes[str(rel_path)] = file_hash

        # Pula se não mudou
        if not force_reindex and old_hashes.get(str(rel_path)) == file_hash:
            stats["files_skipped"] += 1
            continue

        # Extrai texto
        text = extract_text_from_file(file_path)
        if not text or not text.strip():
            print(f"[INFO] Sem texto extraível: {rel_path}")
            stats["errors"] += 1
            continue

        # Chunking
        chunks = chunk_text(text)
        if not chunks:
            stats["errors"] += 1
            continue

        # Embeddings
        try:
            chunk_embeddings = model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)
        except Exception as e:
            print(f"[ERROR] Falha ao gerar embeddings para {rel_path}: {e}")
            stats["errors"] += 1
            continue

        # Adiciona ao índice
        for i, (chunk, emb) in enumerate(zip(chunks, chunk_embeddings)):
            new_chunks.append(emb)
            new_metadata.append({
                "file": str(rel_path),
                "chunk_id": i,
                "text": chunk[:1000],  # guarda preview
                "indexed_at": datetime.utcnow().isoformat() + "Z"
            })

        stats["files_indexed"] += 1
        stats["chunks_created"] += len(chunks)
        print(f"[OK] Indexado: {rel_path} ({len(chunks)} chunks)")

    # Merge com índice existente (se não force_reindex)
    if embeddings is not None and metadata and not force_reindex:
        # Filtra metadata para remover chunks de arquivos reindexados
        reindexed_files = {str(p.relative_to(SHARED_ROOT)) for p in SHARED_ROOT.rglob("*")
                          if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
                          and get_file_hash(p) != old_hashes.get(str(p.relative_to(SHARED_ROOT)), "")}
        # Mantém apenas chunks de arquivos NÃO reindexados
        filtered_meta = [m for m in metadata if m["file"] not in reindexed_files]
        filtered_embs = []
        # Reconstroi embeddings filtrados (simplificado: re-encode tudo se houver mudanças)
        # Para simplicidade, se houve qualquer mudança, reindexa tudo
        if reindexed_files:
            print(f"[INFO] Arquivos alterados detectados ({len(reindexed_files)}), reindexando tudo...")
            return index_files(force_reindex=True)

        # Se chegou aqui, nenhum arquivo mudou
        print("[INFO] Nenhum arquivo alterado desde última indexação.")
        return stats

    # Salva novo índice
    if new_chunks:
        import numpy as np
        all_embeddings = np.vstack(new_chunks) if new_chunks else None
        save_index(all_embeddings, new_metadata)
    save_hashes(new_hashes)

    print(f"[INDEX] Concluído: {stats}")
    return stats


def search(query: str, top_k: int = 5) -> List[Dict]:
    """Busca semântica no índice."""
    if not EMBEDDINGS_FILE.exists() or not METADATA_FILE.exists():
        print("[ERROR] Índice não encontrado. Rode indexação primeiro.")
        return []

    with open(EMBEDDINGS_FILE, "rb") as f:
        embeddings = pickle.load(f)
    metadata = json.loads(METADATA_FILE.read_text())

    model = get_model()
    query_emb = model.encode([query], convert_to_numpy=True)[0]

    # Similaridade coseno
    import numpy as np
    sims = np.dot(embeddings, query_emb) / (np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_emb) + 1e-8)
    top_indices = np.argsort(sims)[::-1][:top_k]

    results = []
    for idx in top_indices:
        m = metadata[idx].copy()
        m["score"] = float(sims[idx])
        results.append(m)
    return results


def main():
    parser = argparse.ArgumentParser(description="Mini-RAG local para /opt/data/hermes-shared")
    parser.add_argument("--reindex", action="store_true", help="Força reindexação total")
    parser.add_argument("--query", type=str, help="Busca semântica")
    parser.add_argument("--top-k", type=int, default=5, help="Número de resultados na busca")
    parser.add_argument("--stats", action="store_true", help="Mostra estatísticas do índice")
    args = parser.parse_args()

    if args.query:
        results = search(args.query, args.top_k)
        print(f"\n🔍 Resultados para: '{args.query}' (top {args.top_k})")
        for i, r in enumerate(results, 1):
            print(f"\n{i}. [{r['score']:.3f}] {r['file']} (chunk {r['chunk_id']})")
            print(f"   {r['text'][:200]}...")
        return

    if args.stats:
        if METADATA_FILE.exists():
            meta = json.loads(METADATA_FILE.read_text())
            files = set(m["file"] for m in meta)
            print(f"📊 Índice: {len(meta)} chunks | {len(files)} arquivos")
            for f in sorted(files):
                count = sum(1 for m in meta if m["file"] == f)
                print(f"  - {f}: {count} chunks")
        else:
            print("📊 Índice vazio.")
        return

    # Indexação padrão
    stats = index_files(force_reindex=args.reindex)
    print(f"\n✅ Indexação finalizada: {stats}")


if __name__ == "__main__":
    main()