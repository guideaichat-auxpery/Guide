"""
Test script to verify RAG integration is working correctly
"""
import os
from database import get_db
from rag_system import retrieve_relevant_chunks, format_retrieved_context

def test_rag_retrieval():
    """Test RAG retrieval with different queries"""
    print("=" * 70)
    print("RAG SYSTEM INTEGRATION TEST")
    print("=" * 70)
    
    # Get database connection
    db = get_db()
    if not db:
        print("❌ Failed to connect to database")
        return
    
    try:
        # Test 1: Montessori query
        print("\n📚 TEST 1: Montessori Query (Absorbent Mind)")
        print("-" * 70)
        query1 = "What is the Absorbent Mind in Montessori education?"
        chunks1 = retrieve_relevant_chunks(
            db_session=db,
            query=query1,
            top_k=2,
            framework_filter="Montessori"
        )
        
        if chunks1:
            print(f"✅ Retrieved {len(chunks1)} chunks")
            for i, chunk in enumerate(chunks1, 1):
                print(f"\nChunk {i}:")
                print(f"  Source: {chunk['source']}")
                print(f"  Similarity: {chunk['similarity']:.2%}")
                print(f"  Preview: {chunk['text'][:100]}...")
        else:
            print("❌ No chunks retrieved")
        
        # Test 2: Australian Curriculum query
        print("\n\n📚 TEST 2: Australian Curriculum Query (Systems Thinking)")
        print("-" * 70)
        query2 = "What is systems thinking in the Australian Curriculum?"
        chunks2 = retrieve_relevant_chunks(
            db_session=db,
            query=query2,
            top_k=2,
            framework_filter="AC_V9"
        )
        
        if chunks2:
            print(f"✅ Retrieved {len(chunks2)} chunks")
            for i, chunk in enumerate(chunks2, 1):
                print(f"\nChunk {i}:")
                print(f"  Source: {chunk['source']}")
                print(f"  Similarity: {chunk['similarity']:.2%}")
                print(f"  Preview: {chunk['text'][:100]}...")
        else:
            print("❌ No chunks retrieved")
        
        # Test 3: Blended query (no filter)
        print("\n\n📚 TEST 3: Blended Query (No Framework Filter)")
        print("-" * 70)
        query3 = "How can I teach sustainability using cosmic education principles?"
        chunks3 = retrieve_relevant_chunks(
            db_session=db,
            query=query3,
            top_k=3,
            framework_filter=None  # Blended - retrieves from both
        )
        
        if chunks3:
            print(f"✅ Retrieved {len(chunks3)} chunks")
            for i, chunk in enumerate(chunks3, 1):
                print(f"\nChunk {i}:")
                print(f"  Source: {chunk['source']}")
                print(f"  Framework: {chunk['metadata'].get('framework', 'Unknown')}")
                print(f"  Similarity: {chunk['similarity']:.2%}")
                print(f"  Preview: {chunk['text'][:100]}...")
        else:
            print("❌ No chunks retrieved")
        
        # Test 4: Format context for API
        print("\n\n📚 TEST 4: Formatted Context for API")
        print("-" * 70)
        if chunks1:
            formatted = format_retrieved_context(chunks1)
            print(formatted[:500] + "...")
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
        print("\n🔒 Database connection closed")

if __name__ == "__main__":
    test_rag_retrieval()
