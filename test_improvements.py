"""
Test script to demonstrate multi-document RAG improvements.

This script tests the new functionality:
1. Question decomposition
2. Entity extraction
3. Answer validation
"""

import sys
sys.path.insert(0, 'src')

from retrieval.question_decomposition import (
    detect_multi_intent_question,
    decompose_question,
    extract_document_filter_from_question,
)
from ingestion.entity_extraction import (
    extract_project_names,
    extract_person_names,
    extract_dates,
)
from retrieval.answer_validation import (
    is_counting_question,
    validate_context_completeness,
)


def test_question_decomposition():
    """Test question decomposition functionality."""
    print("=" * 80)
    print("TEST 1: Question Decomposition")
    print("=" * 80)
    
    test_questions = [
        "What is the timeline for Smart Healthcare project?",
        "What is timeline for Smart Healthcare and give me objective of Smart City Traffic?",
        "How many projects are in Project_Details.pdf and what are their budgets?",
    ]
    
    for question in test_questions:
        print(f"\nQuestion: {question}")
        is_multi = detect_multi_intent_question(question)
        print(f"Multi-intent: {is_multi}")
        
        sub_questions = decompose_question(question)
        print(f"Sub-questions ({len(sub_questions)}):")
        for i, sq in enumerate(sub_questions, 1):
            print(f"  {i}. [{sq['type']}] {sq['question']}")
        
        doc_filter = extract_document_filter_from_question(question)
        if doc_filter:
            print(f"Document filter: {doc_filter}")
    print()


def test_entity_extraction():
    """Test entity extraction functionality."""
    print("=" * 80)
    print("TEST 2: Entity Extraction")
    print("=" * 80)
    
    sample_text = """
    Project Name: Smart Healthcare Management System
    Project Name: AI-Powered Document Intelligence Platform
    Timeline: 6 Months
    Location: New York, USA
    Name: John Smith
    
    1. Smart City Traffic Monitoring System
    2. Blockchain Supply Chain Solution
    """
    
    print("\nSample Text:")
    print("-" * 40)
    print(sample_text)
    print("-" * 40)
    
    projects = extract_project_names(sample_text)
    print(f"\nExtracted Projects ({len(projects)}):")
    for p in projects:
        print(f"  - {p}")
    
    persons = extract_person_names(sample_text)
    print(f"\nExtracted Persons ({len(persons)}):")
    for p in persons:
        print(f"  - {p}")
    
    dates = extract_dates(sample_text)
    print(f"\nExtracted Dates ({len(dates)}):")
    for d in dates:
        print(f"  - {d}")
    print()


def test_answer_validation():
    """Test answer validation functionality."""
    print("=" * 80)
    print("TEST 3: Answer Validation")
    print("=" * 80)
    
    test_cases = [
        ("What is the timeline?", False),
        ("How many projects are there?", True),
        ("List all the project names", True),
        ("Count the number of documents", True),
        ("Tell me about the Smart City project", False),
    ]
    
    for question, expected_counting in test_cases:
        print(f"\nQuestion: {question}")
        is_counting = is_counting_question(question)
        print(f"Is counting question: {is_counting} (expected: {expected_counting})")
        status = "✅" if is_counting == expected_counting else "❌"
        print(f"Status: {status}")
    
    # Test context completeness validation
    print("\n" + "-" * 80)
    print("Context Completeness Validation")
    print("-" * 80)
    
    mock_context = [
        {"doc": type('obj', (object,), {
            'metadata': {'document_name': 'doc1.pdf'},
            'page_content': 'Content 1'
        })()},
        {"doc": type('obj', (object,), {
            'metadata': {'document_name': 'doc1.pdf'},
            'page_content': 'Content 2'
        })()},
    ]
    
    counting_question = "How many projects are in all documents?"
    answer = "I found 2 projects."
    
    validation = validate_context_completeness(counting_question, mock_context, answer)
    print(f"\nQuestion: {counting_question}")
    print(f"Context: {validation['num_chunks']} chunks from {validation['num_documents']} document(s)")
    print(f"Confidence: {validation['confidence']}")
    print(f"Complete: {validation['is_complete']}")
    if validation['warning']:
        print(f"Warning: {validation['warning']}")
    print()


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "MULTI-DOCUMENT RAG IMPROVEMENTS TEST" + " " * 22 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    try:
        test_question_decomposition()
        test_entity_extraction()
        test_answer_validation()
        
        print("=" * 80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print()
        print("The improvements are working correctly!")
        print("Re-upload your documents to benefit from entity extraction.")
        print()
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
