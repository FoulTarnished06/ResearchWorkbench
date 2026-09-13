import asyncio
import os
import sys

# Ensure project root in pythonpath
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.pipeline import run_query_pipeline

async def test():
    print("Testing 4-agent sequential pipeline...")
    result = await run_query_pipeline("Quantum Error Mitigation in Neutral Atom Qubits", {"paper_limit": 3})
    print("\n--- PIPELINE EXECUTION SUCCESS ---")
    print(f"Run ID: {result['run_id']}")
    print(f"Elapsed: {result['elapsed_seconds']}s")
    print(f"Total Tokens Used: {result['token_usage']['total_tokens']} (LLM Calls: {result['token_usage']['llm_calls_count']} / Limit: {result['token_usage']['llm_budget_limit']})")
    print(f"Agent 1 (Scraper): {result['token_usage']['breakdown']['agent1_scraper']} tokens (Zero LLM)")
    print(f"Agent 2 (Drafter): {result['token_usage']['breakdown']['agent2_drafter']} tokens (LLM Call 1)")
    print(f"Agent 3 (Cacher): {result['token_usage']['breakdown']['agent3_cacher']} tokens (Zero LLM)")
    print(f"Agent 4 (Fact-Check): {result['token_usage']['breakdown']['agent4_fact_checker']} tokens (LLM Call 2)")
    print(f"Total Claims: {len(result['agent4_data']['evaluated_claims'])}")
    print(f"Total Citations: {len(result['citations'])}")
    print("Test passed!")

if __name__ == "__main__":
    asyncio.run(test())
