#!/bin/bash

echo "==================================="
echo "Meteo Score - Structure Verification"
echo "==================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (missing)"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/ (missing)"
        return 1
    fi
}

echo "Root Files:"
check_file ".env"
check_file ".env.example"
check_file ".gitignore"
check_file "README.md"
check_file "docker-compose.yml"

echo ""
echo "Backend Structure:"
check_dir "backend/api"
check_dir "backend/api/routes"
check_dir "backend/collectors"
check_dir "backend/core"
check_dir "backend/db"
check_dir "backend/db/migrations"
check_dir "backend/scheduler"
check_dir "backend/tests"

echo ""
echo "Backend Files:"
check_file "backend/.python-version"
check_file "backend/requirements.txt"
check_file "backend/pyproject.toml"
check_file "backend/pytest.ini"
check_file "backend/api/__init__.py"
check_file "backend/collectors/__init__.py"
check_file "backend/core/__init__.py"
check_file "backend/db/__init__.py"
check_file "backend/scheduler/__init__.py"
check_file "backend/tests/__init__.py"

echo ""
echo "Frontend Structure:"
check_dir "frontend/src"
check_dir "frontend/src/components"
check_dir "frontend/src/pages"
check_dir "frontend/src/lib"
check_dir "frontend/src/styles"
check_dir "frontend/public"

echo ""
echo "Frontend Files:"
check_file "frontend/package.json"
check_file "frontend/vite.config.ts"
check_file "frontend/tsconfig.json"
check_file "frontend/tsconfig.node.json"
check_file "frontend/tailwind.config.js"
check_file "frontend/postcss.config.js"
check_file "frontend/.eslintrc.json"
check_file "frontend/.prettierrc"
check_file "frontend/index.html"
check_file "frontend/src/index.tsx"
check_file "frontend/src/App.tsx"
check_file "frontend/src/styles/index.css"

echo ""
echo "==================================="
echo "Verification Complete!"
echo "==================================="
