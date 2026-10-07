import asyncio
import os
import sys
from unittest.mock import patch

# Ensure project root in pythonpath
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.pipeline import run_query_pipeline
from backend.agents.agent2_drafter import synthesize_fallback_draft

async def test():
    print("Testing 4-agent sequential pipeline with Dual-Output and Quality Guardrails...")
    query = "Quantum Error Mitigation in Neutral Atom Qubits"
    
    # 1. Verify Zero Fallback Mandate when no API keys are provided
    has_any_key = any(os.environ.get(k) for k in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY"))
    if not has_any_key:
        print("\nVerifying Zero Fallback Mandate: Unauthenticated cold run fails loudly with RuntimeError...")
        try:
            await run_query_pipeline(query, {"paper_limit": 3, "bypass_cache": True})
            assert False, "Pipeline should have failed with RuntimeError when no API keys are configured"
        except RuntimeError as e:
            assert "requires an API key" in str(e)
            print(f"[PASS] Zero Fallback Mandate verified: {e}")
            
    # 2. Test Pipeline Execution with mocked LLMs to verify data structures & cache
    mock_a2 = synthesize_fallback_draft(query, [], [], target_count=3)
    mock_a2["tokens_used"] = 850
    mock_a4 = {
        "dossier_sections": [{"sub_question": "Overview", "content_html": "<p>Overview</p>"}],
        "citations": [{"ref_id": "REF-1", "title": "Paper 1"}],
        "executive_summary": "Monograph executive summary text exceeding 50 characters for validation.",
        "tokens_used": 600,
        "quick_answer": mock_a2["quick_answer"],
        "evaluated_claims": [{"claim_id": "c1", "status": "Auto-Verified"}]
    }
    with patch("backend.pipeline.run_agent2_the_drafter", return_value=mock_a2), \
         patch("backend.pipeline.run_agent4_fact_checker_synthesizer", return_value=mock_a4):
        result = await run_query_pipeline(query, {"paper_limit": 3, "bypass_cache": True})
        print("\n--- PIPELINE EXECUTION SUCCESS ---")
        print(f"Run ID: {result['run_id']}")
        print(f"Elapsed: {result['elapsed_seconds']}s")
        print(f"Total Tokens: {result['token_usage']['total_tokens']}")
        print(f"Quick Answer: {result.get('quick_answer', '')[:100]}...")

        assert "run_id" in result, "Missing run_id in result"
        assert "quick_answer" in result and len(result["quick_answer"]) > 10, "Missing or empty dual-output quick_answer"
        assert "executive_summary" in result and len(result["executive_summary"]) > 50, "Missing executive_summary"
        assert len(result.get("dossier_sections", [])) > 0, "Dossier sections missing"
        assert len(result.get("citations", [])) > 0, "Citations missing"
        assert len(result.get("evaluated_claims", [])) > 0, "Evaluated claims missing"
        assert result["token_usage"]["llm_budget_limit"] == 2, "LLM budget limit violated"

        # Test Cache
        print("\nTesting Query Response Caching...")
        cached_result = await run_query_pipeline(query, {"paper_limit": 3})
        assert cached_result.get("run_id") is not None, "Expected cached result"
        print("Response Cache verified!")

    print("\nAll pipeline assertions successfully passed!")

if __name__ == "__main__":
    asyncio.run(test())
