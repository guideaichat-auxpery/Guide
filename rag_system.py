"""
RAG (Retrieval Augmented Generation) System for Guide
Handles document ingestion, embedding generation, and semantic retrieval
"""

import os
import re
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
import psycopg2
from psycopg2.extras import Json
import numpy as np

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


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for text using OpenAI text-embedding-3-small
    
    Args:
        text: Text to embed
    
    Returns:
        1536-dimensional embedding vector
    """
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


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
            print(f"Warning: {filepath} not found, skipping...")
            results[filename] = 0
            continue
        
        print(f"Processing {filename}...")
        
        # Read file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            results[filename] = 0
            continue
        
        # Chunk the content
        chunks = chunk_text(content, chunk_size=1000, overlap=200)
        print(f"  Created {len(chunks)} chunks")
        
        # Process each chunk
        chunk_count = 0
        for idx, chunk in enumerate(chunks):
            # Generate embedding
            embedding = generate_embedding(chunk)
            
            if embedding is None:
                print(f"  Skipping chunk {idx} due to embedding error")
                continue
            
            # Store in database
            try:
                import json
                # Convert embedding list to PostgreSQL array format
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
                print(f"  Error storing chunk {idx}: {e}")
                continue
        
        db_session.commit()
        results[filename] = chunk_count
        print(f"  ✓ Stored {chunk_count} chunks from {filename}")
    
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
        print(f"Error retrieving chunks: {e}")
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
    print("✓ Cleared all document chunks")


if __name__ == "__main__":
    # For testing/manual ingestion
    import os
    from database import get_db
    
    print("=== Guide RAG System - Document Ingestion ===\n")
    
    db = get_db()
    if not db:
        print("❌ Could not connect to database")
        exit(1)
    
    # Clear existing chunks (optional - comment out to keep existing)
    # clear_document_chunks(db)
    
    # Ingest documents
    results = ingest_documents(db)
    
    print("\n=== Ingestion Summary ===")
    total_chunks = sum(results.values())
    print(f"Total chunks created: {total_chunks}")
    for file, count in results.items():
        print(f"  {file}: {count} chunks")
    
    # Test retrieval
    print("\n=== Testing Retrieval ===")
    test_query = "What is the Absorbent Mind in Montessori education?"
    chunks = retrieve_relevant_chunks(db, test_query, top_k=2)
    
    print(f"Query: {test_query}")
    print(f"Retrieved {len(chunks)} chunks:\n")
    print(format_retrieved_context(chunks))
    
    db.close()
