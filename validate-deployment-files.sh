#!/bin/bash
# Deployment File Validation Script
# Purpose: Verify all required files exist before Docker build
# Usage: chmod +x validate-deployment-files.sh && ./validate-deployment-files.sh

set -e

echo "🔍 Validating deployment files for Cloud Run migration..."
echo ""

REQUIRED_FILES=(
    "mcp-claude-connector-memory-server.py"
    "property_names.py"
    "v6_mcp_bridge.py"
    "jina_v3_optimized_embedder.py"
    "semantic_classifier.py"
    "schema_enforcement.py"
    "global_search.py"
    "local_search.py"
    "mcp_integration.py"
    "requirements.txt"
    "Dockerfile"
    ".dockerignore"
)

REQUIRED_DIRS=(
    "tools"
)

MISSING_FILES=0
MISSING_DIRS=0

# Check files
echo "📄 Checking required files..."
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ MISSING: $file"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

echo ""
echo "📁 Checking required directories..."
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir/"
        # Count Python files in directory
        py_count=$(find "$dir" -maxdepth 1 -name "*.py" | wc -l | tr -d ' ')
        echo "      └─ Contains $py_count Python files"
    else
        echo "  ❌ MISSING: $dir/"
        MISSING_DIRS=$((MISSING_DIRS + 1))
    fi
done

echo ""
echo "🔧 Checking environment template..."
if [ -f ".env.template" ]; then
    echo "  ✅ .env.template exists (reference for required variables)"
else
    echo "  ⚠️  WARNING: .env.template not found (non-critical)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $MISSING_FILES -eq 0 ] && [ $MISSING_DIRS -eq 0 ]; then
    echo "✅ VALIDATION PASSED"
    echo ""
    echo "All required files present. Ready for Docker build."
    echo ""
    echo "Next steps:"
    echo "  1. Complete /plans/task3-pre-deployment-checklist.md"
    echo "  2. Follow /plans/cloudrun-deployment-guide.md Task 2"
    echo "  3. Run: docker build -t daydreamer-mcp-connector:test ."
    echo ""
    exit 0
else
    echo "❌ VALIDATION FAILED"
    echo ""
    echo "Missing files: $MISSING_FILES"
    echo "Missing directories: $MISSING_DIRS"
    echo ""
    echo "⚠️  Cannot proceed with Docker build until all files are present."
    echo ""
    exit 1
fi
