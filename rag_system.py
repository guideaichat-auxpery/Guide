"""
RAG (Retrieval Augmented Generation) System for Guide
Handles document ingestion, embedding generation, and semantic retrieval
"""

import os
import re
from typing import List, Dict, Optional, Tuple
from functools import lru_cache
from openai import OpenAI
import psycopg2
from psycopg2.extras import Json
import numpy as np
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Document sources with metadata
DOCUMENT_SOURCES = {
    "australian_curriculum_v9.txt": {
        "framework": "AC_V9",
        "type": "curriculum",
        "subject": "general"
    },
    "general_capabilities_v9.txt": {
        "framework": "AC_V9",
        "type": "capabilities",
        "subject": "general_capabilities"
    },
    "cross_curriculum_priorities_v9.txt": {
        "framework": "AC_V9",
        "type": "priorities",
        "subject": "cross_curriculum"
    },
    "montessori_national_curriculum.txt": {
        "framework": "Montessori",
        "type": "curriculum",
        "subject": "montessori"
    },
    "montessori_own_handbook.txt": {
        "framework": "Montessori",
        "type": "philosophy",
        "subject": "montessori",
        "source": "Dr. Montessori's Own Handbook"
    },
    "the_absorbent_mind_montessori.txt": {
        "framework": "Montessori",
        "type": "philosophy",
        "subject": "montessori",
        "source": "The Absorbent Mind"
    },
    "the_montessori_method.txt": {
        "framework": "Montessori",
        "type": "philosophy",
        "subject": "montessori",
        "source": "The Montessori Method"
    }
}


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for better context preservation
    
    Args:
        text: Full text to chunk
        chunk_size: Target size of each chunk in characters
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < text_length:
            # Look for sentence endings near the chunk boundary
            search_start = max(start, end - 100)
            search_text = text[search_start:end + 100]
            
            # Find last sentence ending
            sentence_endings = [m.end() for m in re.finditer(r'[.!?]\s+', search_text)]
            if sentence_endings:
                last_ending = sentence_endings[-1]
                end = search_start + last_ending
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        
        # Prevent infinite loop
        if start >= text_length:
            break
    
    return chunks


def generate_embedding_with_retry(text: str) -> Optional[List[float]]:
    """
    Generate embedding for text using OpenAI text-embedding-3-small with retry logic
    
    Handles rate limits, timeouts, and server errors with exponential backoff.
    
    Args:
        text: Text to embed
    
    Returns:
        1536-dimensional embedding vector or None on error
    """
    import time
    max_retries = 3
    initial_delay = 1.0
    
    for retry in range(max_retries + 1):
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            error_str = str(e).lower()
            is_retryable = (
                'rate_limit' in error_str or '429' in error_str or
                'timeout' in error_str or 'timed out' in error_str or
                any(code in error_str for code in ['500', '502', '503'])
            )
            
            if retry >= max_retries or not is_retryable:
                logger.error(f"Error generating embedding: {type(e).__name__} - {str(e)}")
                return None
            
            wait_time = initial_delay * (2 ** retry)
            logger.warning(f"Embedding API error (attempt {retry + 1}/{max_retries}): {type(e).__name__}")
            logger.info(f"Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
    
    return None

@lru_cache(maxsize=100)
def generate_embedding(text: str) -> Optional[tuple]:
    """
    Generate embedding for text with process-wide caching (100 entries)
    
    This is used for document ingestion where embeddings are shared across all users.
    For per-session query embeddings, use generate_embedding_with_session_cache().
    
    Args:
        text: Text to embed
    
    Returns:
        1536-dimensional embedding vector as tuple (for caching compatibility) or None
    """
    embedding = generate_embedding_with_retry(text)
    if embedding is None:
        return None
    # Return as tuple for lru_cache compatibility (lists aren't hashable)
    return tuple(embedding)


def ingest_documents(db_session) -> Dict[str, int]:
    """
    Ingest all curriculum and Montessori documents into the RAG system
    
    Args:
        db_session: SQLAlchemy database session
    
    Returns:
        Dictionary with file names and number of chunks processed
    """
    from sqlalchemy import text
    results = {}
    
    for filename, metadata in DOCUMENT_SOURCES.items():
        filepath = filename
        
        if not os.path.exists(filepath):
            logger.warning(f"File not found: {filepath}, skipping...")
            results[filename] = 0
            continue
        
        logger.info(f"Processing document: {filename}")
        
        # Read file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading {filename}: {type(e).__name__} - {str(e)}")
            results[filename] = 0
            continue
        
        # Chunk the content
        chunks = chunk_text(content, chunk_size=1000, overlap=200)
        logger.info(f"Created {len(chunks)} chunks from {filename}")
        
        # Process each chunk
        chunk_count = 0
        for idx, chunk in enumerate(chunks):
            # Generate embedding (returns tuple from cache)
            embedding = generate_embedding(chunk)
            
            if embedding is None:
                logger.warning(f"Skipping chunk {idx} from {filename} due to embedding error")
                continue
            
            # Store in database
            try:
                import json
                # Convert embedding tuple/list to PostgreSQL array format
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                metadata_str = json.dumps(metadata)
                
                # Use raw connection to avoid SQLAlchemy parameter conversion issues
                connection = db_session.connection().connection
                cursor = connection.cursor()
                
                try:
                    cursor.execute(
                        """
                        INSERT INTO document_chunks (source_file, chunk_text, chunk_index, embedding, metadata)
                        VALUES (%s, %s, %s, %s::vector, %s::jsonb)
                        """,
                        (filename, chunk, idx, embedding_str, metadata_str)
                    )
                    chunk_count += 1
                finally:
                    cursor.close()
            except Exception as e:
                logger.error(f"Error storing chunk {idx} from {filename}: {type(e).__name__} - {str(e)}")
                continue
        
        db_session.commit()
        results[filename] = chunk_count
        logger.info(f"✓ Stored {chunk_count} chunks from {filename}")
    
    return results


def retrieve_relevant_chunks(
    db_session, 
    query: str, 
    top_k: int = 3,
    framework_filter: Optional[str] = None
) -> List[Dict]:
    """
    Retrieve most relevant document chunks for a query using semantic search
    
    Args:
        db_session: SQLAlchemy database session
        query: User's query text
        top_k: Number of top chunks to retrieve
        framework_filter: Optional filter for "AC_V9" or "Montessori"
    
    Returns:
        List of dictionaries containing chunk text, source, and metadata
    """
    from sqlalchemy import text
    
    # Generate query embedding
    query_embedding = generate_embedding(query)
    
    if query_embedding is None:
        return []
    
    # Convert embedding to PostgreSQL array format
    embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
    
    try:
        # Use raw connection for vector operations
        connection = db_session.connection().connection
        cursor = connection.cursor()
        
        try:
            # Build SQL query with optional framework filter
            if framework_filter:
                sql_query = """
                    SELECT 
                        chunk_text,
                        source_file,
                        metadata,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM document_chunks
                    WHERE metadata->>'framework' = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                cursor.execute(sql_query, (embedding_str, framework_filter, embedding_str, top_k))
            else:
                sql_query = """
                    SELECT 
                        chunk_text,
                        source_file,
                        metadata,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM document_chunks
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                cursor.execute(sql_query, (embedding_str, embedding_str, top_k))
            
            rows = cursor.fetchall()
            
            chunks = []
            for row in rows:
                chunks.append({
                    "text": row[0],
                    "source": row[1],
                    "metadata": row[2],
                    "similarity": row[3]
                })
            
            return chunks
        finally:
            cursor.close()
    
    except Exception as e:
        logger.error(f"Error retrieving chunks: {type(e).__name__} - {str(e)}")
        return []


def format_retrieved_context(chunks: List[Dict]) -> str:
    """
    Format retrieved chunks into a context string for the AI with inline citation instructions
    
    Args:
        chunks: List of retrieved chunk dictionaries
    
    Returns:
        Formatted context string with citations
    """
    if not chunks:
        return ""
    
    context = "📚 RELEVANT CURRICULUM & MONTESSORI REFERENCES:\n\n"
    context += "**IMPORTANT: Use inline citations when referencing these sources.**\n"
    context += "Format: 'According to [Source Name]...' or 'As outlined in [1]...'\n\n"
    
    citation_list = []
    for idx, chunk in enumerate(chunks, 1):
        source = chunk['metadata'].get('source', chunk['source'])
        framework = chunk['metadata'].get('framework', 'Unknown')
        
        # Clean up source name for better readability
        source_display = source.replace('.txt', '').replace('_', ' ').title()
        
        context += f"[{idx}] **{source_display}** ({framework})\n"
        context += f"{chunk['text']}\n"
        context += f"(Similarity: {chunk['similarity']:.1%})\n\n"
        
        citation_list.append(f"[{idx}] {source_display}")
    
    context += "─" * 70 + "\n"
    context += "**CITATION REQUIREMENT**: When using information from these sources, cite them inline.\n"
    context += f"Available citations: {', '.join(citation_list)}\n"
    context += "Example: 'The Absorbent Mind [1] describes how children...'\n\n"
    
    return context


def clear_document_chunks(db_session):
    """Clear all document chunks from the database (for re-ingestion)"""
    from sqlalchemy import text
    db_session.execute(text("DELETE FROM document_chunks"))
    db_session.commit()
    logger.info("✓ Cleared all document chunks")


if __name__ == "__main__":
    # For testing/manual ingestion
    import os
    from database import get_db
    
    logger.info("=== Guide RAG System - Document Ingestion ===\n")
    
    db = get_db()
    if not db:
        logger.error("❌ Could not connect to database")
        exit(1)
    
    # Clear existing chunks (optional - comment out to keep existing)
    # clear_document_chunks(db)
    
    # Ingest documents
    results = ingest_documents(db)
    
    logger.info("\n=== Ingestion Summary ===")
    total_chunks = sum(results.values())
    logger.info(f"Total chunks created: {total_chunks}")
    for file, count in results.items():
        logger.info(f"  {file}: {count} chunks")
    
    # Test retrieval
    logger.info("\n=== Testing Retrieval ===")
    test_query = "What is the Absorbent Mind in Montessori education?"
    chunks = retrieve_relevant_chunks(db, test_query, top_k=2)
    
    logger.info(f"Query: {test_query}")
    logger.info(f"Retrieved {len(chunks)} chunks:\n")
    logger.info(format_retrieved_context(chunks))
    
    db.close()
