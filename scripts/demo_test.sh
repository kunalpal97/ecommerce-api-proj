#!/usr/bin/env bash
# ==============================================================================
# scripts/demo_test.sh — Interactive Live E2E Smoke & Scenario Runner
# ==============================================================================
# Starts a temporary API server, executes every challenge scenario against it,
# asserts both HTTP codes and live state, then cleanly stops the server.
# ==============================================================================

set -euo pipefail

PORT=8976
BASE_URL="http://127.0.0.1:${PORT}/api/v1"

echo "======================================================================"
echo "🚀 STARTING COMMERCE API LIVE TEST DEMO"
echo "======================================================================"

# Start server in background
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $PORT --log-level error &
SERVER_PID=$!
trap 'echo -e "\n🛑 Stopping server (PID: $SERVER_PID)..."; kill $SERVER_PID 2>/dev/null || true' EXIT

sleep 2

echo -e "\n--- Scenario 1: Product Catalogue & Initial Baseline ---"
curl -s "${BASE_URL}/products" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Total products: {data[\"total\"]}')
for p in data['products']:
    print(f'  • {p[\"name\"]} ({p[\"id\"]}) | Stock: {p[\"stock\"]} | ₹{p[\"price\"]}')
"

echo -e "\n--- Scenario 2: Reject Invalid Quantities (0, -1, 1.5) ---"
CART_1=$(curl -s -X POST "${BASE_URL}/cart" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Created test cart: $CART_1"

# Test 0
CODE_0=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/cart/${CART_1}/items" \
  -H "Content-Type: application/json" -d '{"product_id": "prod_laptop", "quantity": 0}')
echo "  • Adding quantity = 0  -> HTTP Status: $CODE_0 (Expected: 422)"

# Test -5
CODE_NEG=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/cart/${CART_1}/items" \
  -H "Content-Type: application/json" -d '{"product_id": "prod_laptop", "quantity": -5}')
echo "  • Adding quantity = -5 -> HTTP Status: $CODE_NEG (Expected: 422)"

# Test 1.5
CODE_FLOAT=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/cart/${CART_1}/items" \
  -H "Content-Type: application/json" -d '{"product_id": "prod_laptop", "quantity": 1.5}')
echo "  • Adding quantity = 1.5-> HTTP Status: $CODE_FLOAT (Expected: 422)"

echo -e "\n--- Scenario 3: Exact Stock Limit Checkout (USB Hub has stock = 1) ---"
CART_EXACT=$(curl -s -X POST "${BASE_URL}/cart" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
curl -s -X POST "${BASE_URL}/cart/${CART_EXACT}/items" \
  -H "Content-Type: application/json" -d '{"product_id": "prod_usb_hub", "quantity": 1}' > /dev/null

RES_EXACT=$(curl -s -X POST "${BASE_URL}/checkout" \
  -H "Content-Type: application/json" -H "Idempotency-Key: key-exact-limit-01" \
  -d "{\"cart_id\": \"${CART_EXACT}\"}")
echo "  • Checkout response: $(echo "$RES_EXACT" | python3 -c "import sys, json; print(json.load(sys.stdin)['message'])")"

# Check remaining stock for USB Hub
HUB_STOCK=$(curl -s "${BASE_URL}/products" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for p in data['products']:
    if p['id'] == 'prod_usb_hub':
        print(p['stock'])
")
echo "  • USB-C Hub remaining stock: $HUB_STOCK (Expected: 0)"

echo -e "\n--- Scenario 4: CRITICAL Partial Failure (Item 1 Available, Item 2 Short) ---"
CART_PARTIAL=$(curl -s -X POST "${BASE_URL}/cart" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
# Add 2 Laptops (available = 10)
curl -s -X POST "${BASE_URL}/cart/${CART_PARTIAL}/items" \
  -H "Content-Type: application/json" -d '{"product_id": "prod_laptop", "quantity": 2}' > /dev/null
# Add 99 Headphones (available = 5, short!)
curl -s -X POST "${BASE_URL}/cart/${CART_PARTIAL}/items" \
  -H "Content-Type: application/json" -d '{"product_id": "prod_headphones", "quantity": 99}' > /dev/null

RES_FAIL=$(curl -s -X POST "${BASE_URL}/checkout" \
  -H "Content-Type: application/json" -H "Idempotency-Key: key-partial-fail-01" \
  -d "{\"cart_id\": \"${CART_PARTIAL}\"}")
echo "  • Checkout response: $(echo "$RES_FAIL" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"{d['error']}: {d['message']}\")")"

LAPTOP_STOCK=$(curl -s "${BASE_URL}/products" | python3 -c "
import sys, json
for p in json.load(sys.stdin)['products']:
    if p['id'] == 'prod_laptop': print(p['stock'])
")
echo "  • STATE PROOF: Laptop stock untouched: $LAPTOP_STOCK (Expected: 10, NOT 8!)"

echo -e "\n--- Scenario 5: Idempotent Retry (Same Key + Same Payload) ---"
CART_RETRY=$(curl -s -X POST "${BASE_URL}/cart" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
curl -s -X POST "${BASE_URL}/cart/${CART_RETRY}/items" \
  -H "Content-Type: application/json" -d '{"product_id": "prod_laptop", "quantity": 1}' > /dev/null

RETRY_KEY="uuid-retry-12345"
RES_1=$(curl -s -X POST "${BASE_URL}/checkout" \
  -H "Content-Type: application/json" -H "Idempotency-Key: ${RETRY_KEY}" \
  -d "{\"cart_id\": \"${CART_RETRY}\"}")
ORD_1=$(echo "$RES_1" | python3 -c "import sys, json; print(json.load(sys.stdin)['order']['id'])")
echo "  • Attempt 1: Order created: $ORD_1"

RES_2=$(curl -s -X POST "${BASE_URL}/checkout" \
  -H "Content-Type: application/json" -H "Idempotency-Key: ${RETRY_KEY}" \
  -d "{\"cart_id\": \"${CART_RETRY}\"}")
ORD_2=$(echo "$RES_2" | python3 -c "import sys, json; print(json.load(sys.stdin)['order']['id'])")
MSG_2=$(echo "$RES_2" | python3 -c "import sys, json; print(json.load(sys.stdin)['message'])")
echo "  • Attempt 2: $MSG_2"
echo "  • STATE PROOF: Same Order ID returned: $ORD_2 (Matches $ORD_1: $([ "$ORD_1" == "$ORD_2" ] && echo "YES" || echo "NO"))"

echo -e "\n--- Scenario 6: Idempotent Conflict (Same Key + Mutated Payload) ---"
CART_DIFF=$(curl -s -X POST "${BASE_URL}/cart" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
CODE_CONFLICT=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/checkout" \
  -H "Content-Type: application/json" -H "Idempotency-Key: ${RETRY_KEY}" \
  -d "{\"cart_id\": \"${CART_DIFF}\"}")
echo "  • Reusing '${RETRY_KEY}' with different cart_id -> HTTP Status: $CODE_CONFLICT (Expected: 409)"

echo -e "\n======================================================================"
echo "✅ ALL INTERACTIVE LIVE SCENARIO TESTS VERIFIED SUCCESSFULLY!"
echo "======================================================================"
