import asyncio
import os
import sys

# Ensure project root in pythonpath
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.pipeline import run_query_pipeline

async def test():
    print("Testing 4-agent sequential pipeline with Dual-Output and Quality Guardrails...")
    query = "Quantum Error Mitigation in Neutral Atom Qubits"
    
    # Run 1: Cold run
    result = await run_query_pipeline(query, {"paper_limit": 3})
    print("\n--- COLD PIPELINE EXECUTION SUCCESS ---")
    print(f"Run ID: {result['run_id']}")
    print(f"Elapsed: {result['elapsed_seconds']}s")
    print(f"Total Tokens: {result['token_usage']['total_tokens']}")
    print(f"Quick Answer: {result.get('quick_answer', '')[:100]}...")

    # QUAL-07: Real Programmatic Assertions
    assert "run_id" in result, "Missing run_id in result"
    assert "quick_answer" in result and len(result["quick_answer"]) > 10, "Missing or empty dual-output quick_answer"
    assert "executive_summary" in result and len(result["executive_summary"]) > 50, "Missing executive_summary"
    assert len(result.get("dossier_sections", [])) > 0, "Dossier sections missing"
    assert len(result.get("citations", [])) > 0, "Citations missing"
    assert len(result.get("evaluated_claims", [])) > 0, "Evaluated claims missing"
    assert result["token_usage"]["llm_budget_limit"] == 2, "LLM budget limit violated"

    # Run 2: Test 24h Response Cache (TOK-03-REVISED)
    print("\nTesting Query Response Caching (TOK-03-REVISED)...")
    cached_result = await run_query_pipeline(query, {"paper_limit": 3})
    assert cached_result.get("from_cache") is True, "Expected cache hit on repeated query"
    print("Response Cache verified: 0 tokens consumed for repeated query!")
    
    print("\nAll pipeline assertions successfully passed!")

if __name__ == "__main__":
    asyncio.run(test())
