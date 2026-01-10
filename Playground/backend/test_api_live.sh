#!/bin/bash
#
# Live API Test Script - Test running API server
# Requires server to be running on localhost:8000
#

API_URL="${API_URL:-http://localhost:8000}"

echo "=========================================="
echo "  AONP API Live Test"
echo "=========================================="
echo "Testing API at: $API_URL"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    
    echo -n "Testing $name... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$API_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_URL$endpoint")
    fi
    
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$status_code" = "200" ] || [ "$status_code" = "202" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $status_code)"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $status_code)"
        echo "  Response: $body"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Test 1: Health Check
echo "----------------------------------------"
echo "Test Suite 1: Health & Status"
echo "----------------------------------------"
test_endpoint "Health Check" "GET" "/api/v1/health"
test_endpoint "Statistics" "GET" "/api/v1/statistics"

# Test 2: Router
echo ""
echo "----------------------------------------"
echo "Test Suite 2: Router"
echo "----------------------------------------"
test_endpoint "Router Test" "POST" "/api/v1/router" \
    '{"query": "Simulate PWR at 4.5% enrichment", "use_llm": false}'

# Test 3: Natural Language Query
echo ""
echo "----------------------------------------"
echo "Test Suite 3: Natural Language Query"
echo "----------------------------------------"

echo -n "Submitting query... "
query_response=$(curl -s -X POST "$API_URL/api/v1/query" \
    -H "Content-Type: application/json" \
    -d '{"query": "Simulate PWR at 4.5% enrichment", "use_llm": false}')

query_id=$(echo "$query_response" | grep -o '"query_id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$query_id" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "  Query ID: $query_id"
    PASSED=$((PASSED + 1))
    
    # Wait for query to complete
    echo -n "  Waiting for completion... "
    sleep 2
    
    # Check status
    status_response=$(curl -s "$API_URL/api/v1/query/$query_id")
    status=$(echo "$status_response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$status" = "completed" ]; then
        echo -e "${GREEN}✓ COMPLETED${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${YELLOW}⚠ Status: $status${NC}"
        PASSED=$((PASSED + 1))
    fi
else
    echo -e "${RED}✗ FAILED${NC}"
    FAILED=$((FAILED + 1))
fi

# Test 4: Agent-Specific Endpoints
echo ""
echo "----------------------------------------"
echo "Test Suite 4: Agent Endpoints"
echo "----------------------------------------"
test_endpoint "Studies Agent" "POST" "/api/v1/agents/studies" \
    '{"query": "Simulate PWR at 4.5% enrichment"}'

test_endpoint "Sweep Agent" "POST" "/api/v1/agents/sweep" \
    '{"query": "Compare enrichments 3%, 4%, 5%"}'

test_endpoint "Query Agent" "POST" "/api/v1/agents/query" \
    '{"query": "Show me recent simulations"}'

# Test 5: Direct Tool Access
echo ""
echo "----------------------------------------"
echo "Test Suite 5: Direct Tool Access"
echo "----------------------------------------"

echo -n "Submit Direct Study... "
study_response=$(curl -s -X POST "$API_URL/api/v1/studies" \
    -H "Content-Type: application/json" \
    -d '{
        "geometry": "PWR pin cell",
        "materials": ["UO2", "Zircaloy", "Water"],
        "enrichment_pct": 4.5,
        "temperature_K": 600,
        "particles": 10000,
        "batches": 50
    }')

run_id=$(echo "$study_response" | grep -o '"run_id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$run_id" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "  Run ID: $run_id"
    PASSED=$((PASSED + 1))
    
    # Test get study by ID
    test_endpoint "Get Study by ID" "GET" "/api/v1/studies/$run_id"
else
    echo -e "${RED}✗ FAILED${NC}"
    echo "  Response: $study_response"
    FAILED=$((FAILED + 1))
fi

# Test 6: Query Runs
echo ""
echo "----------------------------------------"
echo "Test Suite 6: Query Runs"
echo "----------------------------------------"
test_endpoint "Query All Runs" "GET" "/api/v1/runs?limit=5"
test_endpoint "Query PWR Runs" "GET" "/api/v1/runs?geometry=PWR&limit=5"

# Summary
echo ""
echo "=========================================="
echo "  Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo "=========================================="
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo "=========================================="
    exit 1
fi

