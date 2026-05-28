#!/bin/bash
# GeoRisk Oracle — Pre-commit security hook
# Blocks commits containing sensitive data patterns
# Install: bash scripts/install-hooks.sh

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "🔍 Scanning for sensitive data..."

FAILED=0

# Get list of staged files (not deleted)
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    echo -e "${GREEN}✅ No staged files to scan.${NC}"
    exit 0
fi

# Scan each file for sensitive patterns
for FILE in $STAGED_FILES; do
    # Skip binary files
    if file "$FILE" 2>/dev/null | grep -q "binary"; then
        continue
    fi

    CONTENT=$(git show ":$FILE" 2>/dev/null)

    # NVIDIA NIM API key
    if echo "$CONTENT" | grep -qE "nvapi-[A-Za-z0-9_-]{20,}"; then
        echo -e "${RED}❌ BLOCKED: NVIDIA NIM API key found in $FILE${NC}"
        FAILED=1
    fi

    # Anthropic API key
    if echo "$CONTENT" | grep -qE "sk-ant-api[0-9A-Za-z-]{20,}"; then
        echo -e "${RED}❌ BLOCKED: Anthropic API key found in $FILE${NC}"
        FAILED=1
    fi

    # Private key block (SSH, RSA, EC)
    if echo "$CONTENT" | grep -qE "\-\-\-\-\-BEGIN .* PRIVATE KEY\-\-\-\-\-"; then
        echo -e "${RED}❌ BLOCKED: Private key found in $FILE${NC}"
        FAILED=1
    fi

    # Firebase service account (split pattern to avoid self-detection)
    FIREBASE_PAT='"private_key'"_id"'"'
    if echo "$CONTENT" | grep -q "$FIREBASE_PAT"; then
        echo -e "${RED}❌ BLOCKED: Firebase service account credentials found in $FILE${NC}"
        FAILED=1
    fi

    # Telegram bot token pattern (digits:AA...)
    if echo "$CONTENT" | grep -qE "[0-9]{8,10}:AA[A-Za-z0-9_-]{33}"; then
        echo -e "${RED}❌ BLOCKED: Telegram bot token found in $FILE${NC}"
        FAILED=1
    fi

    # Generic high-entropy API key patterns
    if echo "$CONTENT" | grep -qiE "api_key\s*=\s*['\"][A-Za-z0-9_-]{32,}"; then
        echo -e "${RED}❌ BLOCKED: Hardcoded API key found in $FILE${NC}"
        FAILED=1
    fi
done

# Block sensitive filenames from being staged
for FILE in $STAGED_FILES; do
    case "$FILE" in
        .env|*.key|*.pem|*.p12|*.pfx)
            echo -e "${RED}❌ BLOCKED: Sensitive file: $FILE${NC}"
            FAILED=1
            ;;
        *firebase-adminsdk*.json|*service-account*.json|*credentials*.json)
            echo -e "${RED}❌ BLOCKED: Sensitive credentials file: $FILE${NC}"
            FAILED=1
            ;;
    esac
done

if [ $FAILED -eq 1 ]; then
    echo ""
    echo -e "${RED}🚨 Commit blocked — sensitive data detected.${NC}"
    echo -e "${YELLOW}   Remove the sensitive data and try again.${NC}"
    echo -e "${YELLOW}   To bypass (NOT recommended): git commit --no-verify${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Clean — no sensitive data detected.${NC}"
exit 0
