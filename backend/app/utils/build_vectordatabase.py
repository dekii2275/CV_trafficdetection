"""
Script để build vector database từ các file luật giao thông
Chạy script này mỗi khi có văn bản luật mới

Usage:
    python -m app.utils.build_vector_db
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.services.rag_services.vector_store import VectorStoreService
from app.services.rag_services.document_process import DocumentProcessor


def build_vector_database(
    documents_dir: str = "./data/law_documents",
    reset: bool = False
):
    """
    Build vector database từ các file luật
    
    Args:
        documents_dir: Thư mục chứa file .doc/.docx
        reset: True để xóa và rebuild từ đầu
    """
    print("="*60)
    print("🚀 RAG VECTOR DATABASE BUILDER")
    print("="*60)
    
    # Khởi tạo services
    print("\n📦 Initializing services...")
    vector_store = VectorStoreService(
        collection_name="traffic_laws",
        persist_directory="./data/chroma_db"
    )
    
    processor = DocumentProcessor(
        chunk_size=500,
        chunk_overlap=100
    )
    
    # Reset nếu cần
    if reset:
        print("\n🗑️ Resetting vector database...")
        vector_store.reset_and_rebuild()
    
    # Kiểm tra số documents hiện có
    info = vector_store.get_collection_info()
    print(f"\n📊 Current database status:")
    print(f"   - Collection: {info['name']}")
    print(f"   - Documents: {info['total_documents']}")
    print(f"   - Location: {info['persist_directory']}")
    
    # Process documents
    print(f"\n📄 Processing law documents from: {documents_dir}")
    documents, metadatas = processor.process_law_documents(documents_dir)
    
    if not documents:
        print("⚠️ No documents found to process!")
        return
    
    # Add to vector store
    print(f"\n💾 Adding {len(documents)} chunks to vector database...")
    vector_store.add_documents(
        documents=documents,
        metadatas=metadatas
    )
    
    # Final stats
    final_info = vector_store.get_collection_info()
    print("\n" + "="*60)
    print("✅ BUILD COMPLETED")
    print("="*60)
    print(f"📊 Final Statistics:")
    print(f"   - Total documents in DB: {final_info['total_documents']}")
    print(f"   - New documents added: {len(documents)}")
    print(f"   - Location: {final_info['persist_directory']}")
    print("\n💡 Your RAG chatbot is ready to use!")
    print("="*60)


def test_search(query: str = "Phạt bao nhiêu khi không đội mũ bảo hiểm?"):
    """
    Test search functionality
    """
    print("\n" + "="*60)
    print("🧪 TESTING SEARCH FUNCTIONALITY")
    print("="*60)
    
    vector_store = VectorStoreService()
    
    print(f"\n🔍 Query: {query}")
    results = vector_store.search(query, top_k=3)
    
    print(f"\n📋 Top {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} (Score: {result['similarity_score']:.2%}) ---")
        print(f"Law: {result['metadata'].get('law_name')}")
        print(f"Article: {result['metadata'].get('article_number')} - {result['metadata'].get('article_title')}")
        print(f"Content preview: {result['document'][:200]}...")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build RAG Vector Database")
    parser.add_argument(
        "--documents-dir",
        type=str,
        default="./data/law_documents",
        help="Directory containing law documents"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset and rebuild database from scratch"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run search test after building"
    )
    parser.add_argument(
        "--test-query",
        type=str,
        default="Phạt bao nhiêu khi không đội mũ bảo hiểm?",
        help="Query for testing"
    )
    
    args = parser.parse_args()
    
    # Build database
    build_vector_database(
        documents_dir=args.documents_dir,
        reset=args.reset
    )
    
    # Test nếu cần
    if args.test:
        test_search(args.test_query)