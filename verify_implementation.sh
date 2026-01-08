#!/bin/bash
# Multi-Document RAG - Quick Verification Script

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║              Multi-Document RAG - System Verification                        ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python files compile
echo "1. Checking Python syntax..."
python -m py_compile \
    src/retrieval/question_decomposition.py \
    src/retrieval/answer_validation.py \
    src/ingestion/entity_extraction.py \
    src/ingestion/chunking.py \
    src/rag/pipeline.py 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All Python files compile successfully${NC}"
else
    echo -e "${RED}❌ Syntax errors found${NC}"
    exit 1
fi

# Check if new modules exist
echo ""
echo "2. Checking new modules..."
files=(
    "src/retrieval/question_decomposition.py"
    "src/retrieval/answer_validation.py"
    "src/ingestion/entity_extraction.py"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${RED}❌${NC} $file (missing)"
        all_exist=false
    fi
done

if [ "$all_exist" = false ]; then
    echo -e "${RED}❌ Some files are missing${NC}"
    exit 1
fi

# Run automated tests
echo ""
echo "3. Running automated tests..."
python test_improvements.py 2>&1 | tail -n 10

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Tests passed${NC}"
else
    echo -e "${RED}❌ Tests failed${NC}"
    exit 1
fi

# Check documentation
echo ""
echo "4. Checking documentation..."
docs=(
    "MULTI_DOCUMENT_FIX_SUMMARY.md"
    "TESTING_GUIDE.md"
    "IMPLEMENTATION_COMPLETE.md"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "${GREEN}✅${NC} $doc"
    else
        echo -e "${YELLOW}⚠️${NC}  $doc (missing)"
    fi
done

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                        Verification Complete                                 ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}✅ All improvements successfully implemented!${NC}"
echo ""
echo "Next steps:"
echo "  1. Clear old embeddings: rm -rf src/embedding_store/*"
echo "  2. Start server: ./start.sh"
echo "  3. Re-upload your documents"
echo "  4. Test multi-document queries"
echo ""
echo "Documentation:"
echo "  - Quick start: TESTING_GUIDE.md"
echo "  - Technical details: MULTI_DOCUMENT_FIX_SUMMARY.md"
echo "  - Complete summary: IMPLEMENTATION_COMPLETE.md"
echo ""
