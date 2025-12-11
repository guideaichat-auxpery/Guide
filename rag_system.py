"""
RAG (Retrieval Augmented Generation) System for Guide
Handles document ingestion, embedding generation, and semantic retrieval
"""

import os
import re
import json
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

# Year level patterns for curriculum documents
YEAR_LEVEL_PATTERNS = {
    'Foundation': r'\b(Foundation|Kindergarten|F|Prep)\b',
    'Years 1-2': r'\b(Year [12]|Years 1-2|Grade [12])\b',
    'Years 3-4': r'\b(Year [34]|Years 3-4|Grade [34])\b',
    'Years 5-6': r'\b(Year [56]|Years 5-6|Grade [56])\b',
    'Years 7-8': r'\b(Year [78]|Years 7-8|Grade [78])\b',
    'Years 9-10': r'\b(Year [90]|Years 9-10|Grade [90])\b',
    'Years 11-12': r'\b(Year 1[12]|Years 11-12|Grade 1[12])\b',
}

# Subject patterns for curriculum documents
SUBJECT_PATTERNS = {
    'English': r'\b(English|Language Arts|Literacy|Writing|Reading|Literature)\b',
    'Mathematics': r'\b(Mathematics|Maths|Math|Numeracy|Arithmetic)\b',
    'Science': r'\b(Science|Physics|Chemistry|Biology|Earth Science)\b',
    'HASS': r'\b(HASS|Humanities|Social Studies|History|Geography|Civics)\b',
    'Arts': r'\b(Arts|Music|Visual Arts|Drama|Dance)\b',
    'Technology': r'\b(Technology|Computing|ICT|Digital|Design Technology)\b',
    'Physical Education': r'\b(Physical Education|PE|Sport|Health)\b',
}

def extract_year_levels(text: str) -> List[str]:
    """Extract year levels mentioned in text chunk"""
    found_levels = []
    for level, pattern in YEAR_LEVEL_PATTERNS.items():
        if re.search(pattern, text):
            found_levels.append(level)
    return found_levels

def extract_subjects(text: str) -> List[str]:
    """Extract subjects mentioned in text chunk"""
    found_subjects = []
    for subject, pattern in SUBJECT_PATTERNS.items():
        if re.search(pattern, text):
            found_subjects.append(subject)
    return found_subjects

def chunk_text_with_metadata(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict]:
    """
    Split text into overlapping chunks with extracted metadata (year levels, subjects)
    Enhanced for curriculum-aware chunking
    
    Args:
        text: Full text to chunk
        chunk_size: Target size of each chunk in characters
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of chunk dictionaries with metadata
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        
        if end < text_length:
            search_start = max(start, end - 100)
            search_text = text[search_start:end + 100]
            sentence_endings = [m.end() for m in re.finditer(r'[.!?]\s+', search_text)]
            if sentence_endings:
                last_ending = sentence_endings[-1]
                end = search_start + last_ending
        
        chunk_text = text[start:end].strip()
        if chunk_text:
            year_levels = extract_year_levels(chunk_text)
            subjects = extract_subjects(chunk_text)
            chunks.append({
                'text': chunk_text,
                'year_levels': year_levels,
                'subjects': subjects
            })
        
        start = end - overlap
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
        
        # Chunk the content with enhanced metadata
        chunks = chunk_text_with_metadata(content, chunk_size=1000, overlap=200)
        logger.info(f"Created {len(chunks)} chunks from {filename}")
        
        # Process each chunk
        chunk_count = 0
        for idx, chunk_data in enumerate(chunks):
            chunk_text = chunk_data['text']
            embedding = generate_embedding(chunk_text)
            
            if embedding is None:
                logger.warning(f"Skipping chunk {idx} from {filename} due to embedding error")
                continue
            
            # Store in database with enhanced metadata
            try:
                import json
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                enhanced_metadata = metadata.copy()
                enhanced_metadata['year_levels'] = chunk_data.get('year_levels', [])
                enhanced_metadata['subjects'] = chunk_data.get('subjects', [])
                metadata_str = json.dumps(enhanced_metadata)
                
                # Use raw connection to avoid SQLAlchemy parameter conversion issues
                connection = db_session.connection().connection
                cursor = connection.cursor()
                
                try:
                    cursor.execute(
                        """
                        INSERT INTO document_chunks (source_file, chunk_text, chunk_index, embedding, metadata)
                        VALUES (%s, %s, %s, %s::vector, %s::jsonb)
                        """,
                        (filename, chunk_text, idx, embedding_str, metadata_str)
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


def expand_query(query: str) -> List[str]:
    """
    Expand user queries with curriculum-specific variations
    Handles teacher language and maps to curriculum frameworks
    
    Args:
        query: User's original query
    
    Returns:
        List of expanded query variations for broader search
    """
    expanded_queries = [query]
    query_lower = query.lower()
    
    # Teacher language expansions
    expansions = {
        'fractions|dividing': ['number and algebra', 'proportional reasoning', 'rational numbers'],
        'cosmic education|big picture': ['interconnection', 'cultural knowledge', 'universe study'],
        'practical life': ['independence', 'motor skills', 'daily activities'],
        'sensorial materials|sensory': ['exploration', 'discrimination', 'perception'],
        'mixed age|loop groups': ['multiage learning', 'peer tutoring', 'vertical grouping'],
        'lesson cycle|three period lesson': ['introduction', 'practice', 'reinforcement'],
        'grace and courtesy': ['social skills', 'community responsibility', 'respectful interaction'],
        'montessori lesson|presentation': ['pedagogical technique', 'teacher guidance', 'child-centered'],
        'critical thinking|problem solving': ['higher order thinking', 'reasoning', 'analysis'],
        'indigenous knowledge|cultural': ['aboriginal perspectives', 'first nations', 'cultural awareness'],
    }
    
    for pattern, alternative_terms in expansions.items():
        if re.search(pattern, query_lower):
            expanded_queries.extend(alternative_terms)
    
    return list(set(expanded_queries))[:5]  # Return up to 5 unique queries


def extract_curriculum_codes(text: str) -> List[str]:
    """
    Extract Australian Curriculum and Montessori codes from text
    
    AC codes: ACELA1234, ACMNA456, etc.
    Montessori: PLN3, SEN4, etc.
    
    Args:
        text: Text to search for codes
    
    Returns:
        List of found curriculum codes
    """
    ac_codes = re.findall(r'\b[A-Z]{2}[A-Z]{3}\d{4}\b', text)
    montessori_codes = re.findall(r'\b[A-Z]{2,4}\d{1,2}\b', text)
    return ac_codes + montessori_codes


def retrieve_relevant_chunks(
    db_session, 
    query: str, 
    top_k: int = 6,
    framework_filter: Optional[str] = None,
    year_level: Optional[str] = None,
    subject: Optional[str] = None
) -> List[Dict]:
    """
    Retrieve most relevant document chunks using semantic + keyword hybrid search
    
    Args:
        db_session: SQLAlchemy database session
        query: User's query text
        top_k: Number of top chunks to retrieve (increased from 3 to 6)
        framework_filter: Optional filter for "AC_V9" or "Montessori"
        year_level: Optional filter by year level (e.g., "Years 3-4")
        subject: Optional filter by subject (e.g., "Mathematics")
    
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
    
    # Extract curriculum codes for hybrid search
    curriculum_codes = extract_curriculum_codes(query)
    
    try:
        # Use raw connection for vector operations
        connection = db_session.connection().connection
        cursor = connection.cursor()
        
        try:
            from psycopg2 import sql as psql
            
            code_patterns = [f'%{code}%' for code in curriculum_codes] if curriculum_codes else ['%___%']
            
            # Build WHERE clause with optional filters using psycopg2.sql for safe composition
            where_conditions = []
            params = [embedding_str, code_patterns]
            
            if framework_filter:
                where_conditions.append(psql.SQL("metadata->>'framework' = %s"))
                params.append(framework_filter)
            if year_level:
                where_conditions.append(psql.SQL("metadata->'year_levels' @> %s::jsonb"))
                params.append(json.dumps([year_level]))
            if subject:
                where_conditions.append(psql.SQL("metadata->'subjects' @> %s::jsonb"))
                params.append(json.dumps([subject]))
            
            base_query = psql.SQL("""
                SELECT 
                    chunk_text,
                    source_file,
                    metadata,
                    1 - (embedding <=> %s::vector) as similarity
                FROM document_chunks
            """)
            
            order_clause = psql.SQL("""
                ORDER BY (1 - (embedding <=> %s::vector)) * 
                         CASE 
                             WHEN chunk_text ILIKE ANY(%s) THEN 1.5
                             ELSE 1.0
                         END DESC,
                         embedding <=> %s::vector
                LIMIT %s
            """)
            
            if where_conditions:
                where_clause = psql.SQL(" WHERE ") + psql.SQL(" AND ").join(where_conditions)
                sql_query = base_query + where_clause + order_clause
            else:
                sql_query = base_query + order_clause
            
            params.extend([embedding_str, code_patterns, embedding_str, top_k])
            cursor.execute(sql_query, params)
            
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
        # Fallback to basic semantic search if keyword boost fails
        try:
            connection = db_session.connection().connection
            cursor = connection.cursor()
            
            try:
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
        except Exception as fallback_error:
            logger.error(f"Fallback search also failed: {type(fallback_error).__name__} - {str(fallback_error)}")
            return []


def format_retrieved_context(chunks: List[Dict]) -> str:
    """
    Format retrieved chunks into a context string for the AI with inline citation instructions
    Enhanced with source type indicators and improved organization
    
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
    
    # Group chunks by source type for better organization
    ac_chunks = []
    montessori_chunks = []
    other_chunks = []
    
    for idx, chunk in enumerate(chunks, 1):
        source = chunk['metadata'].get('source', chunk['source'])
        framework = chunk['metadata'].get('framework', 'Unknown')
        doc_type = chunk['metadata'].get('type', 'unknown')
        
        # Clean up source name for better readability
        source_display = source.replace('.txt', '').replace('_', ' ').title()
        
        chunk_entry = {
            'idx': idx,
            'source': source_display,
            'framework': framework,
            'type': doc_type,
            'text': chunk['text'],
            'similarity': chunk['similarity']
        }
        
        if framework == 'AC_V9':
            ac_chunks.append(chunk_entry)
        elif framework == 'Montessori':
            montessori_chunks.append(chunk_entry)
        else:
            other_chunks.append(chunk_entry)
        
        citation_list.append(f"[{idx}] {source_display}")
    
    # Format AC_V9 chunks first
    if ac_chunks:
        context += "**Australian Curriculum V9:**\n"
        for chunk in ac_chunks:
            context += f"[{chunk['idx']}] **{chunk['source']}** ({chunk['type']})\n"
            context += f"{chunk['text']}\n"
            context += f"(Relevance: {chunk['similarity']:.0%})\n\n"
    
    # Format Montessori chunks
    if montessori_chunks:
        context += "**Montessori Curriculum & Philosophy:**\n"
        for chunk in montessori_chunks:
            context += f"[{chunk['idx']}] **{chunk['source']}** ({chunk['type']})\n"
            context += f"{chunk['text']}\n"
            context += f"(Relevance: {chunk['similarity']:.0%})\n\n"
    
    # Format other chunks
    if other_chunks:
        context += "**Additional Resources:**\n"
        for chunk in other_chunks:
            context += f"[{chunk['idx']}] **{chunk['source']}** ({chunk['framework']})\n"
            context += f"{chunk['text']}\n"
            context += f"(Relevance: {chunk['similarity']:.0%})\n\n"
    
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

def reingest_documents_with_new_metadata(db_session) -> Dict[str, int]:
    """
    Re-ingest all documents with enhanced metadata (year_levels, subjects)
    Use this after adding new metadata extraction to chunk_text_with_metadata
    
    Args:
        db_session: SQLAlchemy database session
    
    Returns:
        Dictionary with file names and number of chunks processed
    """
    logger.info("=== Re-ingesting documents with enhanced metadata ===")
    clear_document_chunks(db_session)
    results = ingest_documents(db_session)
    logger.info("✓ Re-ingestion complete with enhanced metadata")
    return results


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
