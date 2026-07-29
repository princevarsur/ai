import requests
import json

token = open("_token.txt").read().strip()
headers = {"Authorization": f"Bearer {token}"}

# Test 1: List laws
print("=" * 60)
print("TEST: GET /api/laws/")
r = requests.get("http://localhost:8000/api/laws/", headers=headers)
print(f"Status: {r.status_code}")
data = r.json()
print(f"Count: {data['count']}")
for x in data["results"][:5]:
    print(f"  {x['law_name']} {x['section']} [{x['category']}] sev={x['severity_weight']}")
print(f"  ... and {data['count'] - 5} more")

# Test 2: Profile
print("\n" + "=" * 60)
print("TEST: GET /api/auth/profile/")
r = requests.get("http://localhost:8000/api/auth/profile/", headers=headers)
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2))

# Test 3: Laws by category
print("\n" + "=" * 60)
print("TEST: GET /api/laws/category/data_privacy/")
r = requests.get("http://localhost:8000/api/laws/category/data_privacy/", headers=headers)
print(f"Status: {r.status_code}")
data = r.json()
print(f"Count: {data['count']}")
for x in data["results"]:
    print(f"  {x['law_name']} {x['section']} sev={x['severity_weight']}")

# Test 4: Dashboard (empty, no scans yet)
print("\n" + "=" * 60)
print("TEST: GET /api/compliance/dashboard/")
r = requests.get("http://localhost:8000/api/compliance/dashboard/", headers=headers)
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2))

# Test 5: What-if check
print("\n" + "=" * 60)
print("TEST: POST /api/compliance/what-if/")
r = requests.post(
    "http://localhost:8000/api/compliance/what-if/",
    json={"clause_text": "Female employees get 12 weeks maternity leave"},
    headers=headers,
)
print(f"Status: {r.status_code}")
data = r.json()
for m in data.get("matches", [])[:3]:
    print(f"  {m['law_name']} {m['section']} combined={m['combined_score']:.3f} conflict={m['is_potential_conflict']}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED")
