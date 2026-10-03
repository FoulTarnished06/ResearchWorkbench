import time
import asyncio
import re
import sys

# 1. ReDoS test
from backend.agents.agent2_drafter import remove_consecutive_repeated_phrases
evil = ' '.join(['test word'] * 500)
t0 = time.time()
res = remove_consecutive_repeated_phrases(evil)
t_redos = time.time() - t0
assert t_redos < 0.1, f"ReDoS regression: {t_redos:.3f}s"
print(f"[PASS] ReDoS test: {t_redos*1000:.2f}ms")

# 2. Claim splitting test
from backend.agents.agent3_cacher import split_compound_claim
assert split_compound_claim("CRISPR and Cas9 are effective") == ["CRISPR and Cas9 are effective"]
s_split = split_compound_claim("Fidelity exceeds 99%, and coherence times surpass 40 seconds")
assert len(s_split) == 2, f"Expected 2 clauses, got: {s_split}"
print("[PASS] Claim splitting test")

# 3. Retry test
from backend.retry import retry_async
class BenignError(Exception): pass
async def f(): raise BenignError("Processed 400 chunks successfully")
try:
    asyncio.run(retry_async(f, max_retries=1, base_delay=0.01))
except BenignError:
    print("[PASS] Retry 400 false-positive guard test")

# 4. Post-processor nh3 test
from backend.post_processor import clean_monograph_text
cleaned = clean_monograph_text('<p>Test <span class="claim-wrapper" data-claim-id="c1">text</span><script>evil()</script></p>')
assert "<script>" not in cleaned
assert 'data-claim-id="c1"' in cleaned
print("[PASS] nh3 post-processor sanitization test")

# 5. Database init test
from backend.database import init_db
init_db()
print("[PASS] Database init and migration test")

print("\nALL BEHAVIORAL TESTS PASSED PERFECTLY!")
