"""
Project-scoped RAG (MVP on SQLite FTS over chunks).

Future: plug ChromaDB or another vector store behind :mod:`app.rag.retriever`
without changing Telegram handlers — only retriever implementation.

Voice/STT: transcribe to text, then reuse :func:`app.rag.chunking.chunk_text` and the same indexer.
"""
