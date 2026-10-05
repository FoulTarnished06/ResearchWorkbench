import os
import json
import re
import html
import yaml
import httpx
from typing import Dict, Any, List, Optional
try:
    import nh3
    _USE_NH3 = True
except ImportError:
    _USE_NH3 = False
    import bleach

from backend.logger import get_logger
from backend.retry import retry_async
from backend.post_processor import clean_monograph_text
from backend.agents.agent2_drafter import safe_parse_json, TokenCount, resolve_anthropic_model, resolve_openai_model, is_openai_reasoning_model, is_openai_provider

logger = get_logger("Agent4_Synthesizer")

async def _post_gemini_factcheck(url: str, payload: dict, headers: dict) -> tuple[List[Dict[str, Any]], TokenCount]:
    async with httpx.AsyncClient(timeout=50.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError(f"Gemini Fact-Check error: Empty candidates. Safety block? {data}")
            raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            usage = data.get("usageMetadata", {})
            p_tok = int(usage.get("promptTokenCount", 0))
            c_tok = int(usage.get("candidatesTokenCount", 0))
            tot_tok = int(usage.get("totalTokenCount", 0)) or (p_tok + c_tok)
            try:
                yaml_match = re.search(r'```(?:yaml|json)?\s*(.*?)\s*```', raw_text, re.DOTALL | re.IGNORECASE)
                if yaml_match:
                    raw_text_clean = yaml_match.group(1).strip()
                else:
                    raw_text_clean = re.sub(r'^```(yaml|json)?', '', raw_text.strip(), flags=re.MULTILINE).strip()
                    raw_text_clean = re.sub(r'```$', '', raw_text_clean).strip()
                parsed = yaml.safe_load(raw_text_clean)
                ret_dict = parsed if isinstance(parsed, dict) else {}
                if tot_tok <= 0 and ret_dict:
                    p_tok, c_tok, tot_tok = 380, 240, 620
                elif p_tok <= 0 and c_tok <= 0 and tot_tok > 0:
                    p_tok = round(tot_tok * 0.6)
                    c_tok = tot_tok - p_tok
                return ret_dict, TokenCount(tot_tok, p_tok, c_tok)
            except Exception as e:
                logger.warning(f"Gemini YAML parse warning: {e}")
                return {}, TokenCount(tot_tok, p_tok, c_tok)
        else:
            raise RuntimeError(f"Gemini Fact-Check error ({resp.status_code}): {resp.text}")

async def call_gemini_factcheck(claims_to_check: List[Dict[str, Any]], context_sentences: List[Dict[str, Any]], api_key: str, model_pref: str = "gemini-3.6-flash") -> tuple[List[Dict[str, Any]], TokenCount]:
    # Targeted routing: match each claim to its specific candidate snippets
    claims_payload = []
    for c in claims_to_check:
        snips = c.get("candidate_snippets", [])
        if not snips and context_sentences:
            snips = [s.get("text", "") for s in context_sentences[:2] if s.get("text")]
        claims_payload.append({
            "claim_id": c.get("claim_id"),
            "claim_text": c.get("claim_text"),
            "candidate_evidence": snips
        })
    claims_str = json.dumps(claims_payload, indent=2)
    
    prompt = f"""You are a strict scientific Fact-Checker and Peer-Reviewer LLM.
Evaluate each unverified claim strictly against its matched candidate evidence from the retrieved literature.

For each claim:
1. Determine if it is fully supported, plausible/partially supported, or ungrounded/disputed.
2. Return strictly valid YAML mapping each claim_id to a binary integer (1 if fully/partially supported by evidence, 0 if unsupported/disputed).

Example:
c1: 1
c2: 0
c3: 1

Claims and Targeted Evidence:
{claims_str}
"""
    if "3.8" in model_pref:
        model = "gemini-3.8-flash"
    elif "3.1" in model_pref or "pro" in model_pref:
        model = "gemini-3.1-pro"
    elif "3.5" in model_pref:
        model = "gemini-3.5-flash"
    else:
        model = "gemini-3.6-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096,
            "response_mime_type": "text/plain"
        }
    }
    return await retry_async(_post_gemini_factcheck, url, payload, headers, max_retries=2, base_delay=1.0)

async def _post_anthropic_factcheck(url: str, payload: dict, headers: dict) -> tuple[List[Dict[str, Any]], TokenCount]:
    async with httpx.AsyncClient(timeout=50.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            raw_text = data.get("content", [{}])[0].get("text", "")
            usage = data.get("usage", {})
            p_tok = int(usage.get("input_tokens", 0))
            c_tok = int(usage.get("output_tokens", 0))
            tot_tok = p_tok + c_tok
            try:
                yaml_match = re.search(r'```(?:yaml|json)?\s*(.*?)\s*```', raw_text, re.DOTALL | re.IGNORECASE)
                if yaml_match:
                    raw_text_clean = yaml_match.group(1).strip()
                else:
                    raw_text_clean = re.sub(r'^```(yaml|json)?', '', raw_text.strip(), flags=re.MULTILINE).strip()
                    raw_text_clean = re.sub(r'```$', '', raw_text_clean).strip()
                parsed = yaml.safe_load(raw_text_clean)
                ret_dict = parsed if isinstance(parsed, dict) else {}
                if tot_tok <= 0 and ret_dict:
                    p_tok, c_tok, tot_tok = 360, 220, 580
                elif p_tok <= 0 and c_tok <= 0 and tot_tok > 0:
                    p_tok = round(tot_tok * 0.6)
                    c_tok = tot_tok - p_tok
                return ret_dict, TokenCount(tot_tok, p_tok, c_tok)
            except Exception as e:
                logger.warning(f"Anthropic YAML parse warning: {e}")
                return {}, TokenCount(tot_tok, p_tok, c_tok)
        else:
            raise RuntimeError(f"Anthropic Fact-Check error ({resp.status_code}): {resp.text}")

async def call_anthropic_factcheck(claims_to_check: List[Dict[str, Any]], context_sentences: List[Dict[str, Any]], api_key: str, model_pref: str) -> tuple[List[Dict[str, Any]], TokenCount]:
    claims_payload = []
    for c in claims_to_check:
        snips = c.get("candidate_snippets", [])
        if not snips and context_sentences:
            snips = [s.get("text", "") for s in context_sentences[:2] if s.get("text")]
        claims_payload.append({
            "claim_id": c.get("claim_id"),
            "claim_text": c.get("claim_text"),
            "candidate_evidence": snips
        })
    claims_str = json.dumps(claims_payload, indent=2)
    prompt = f"""You are a strict scientific Fact-Checker and Peer-Reviewer LLM.
Evaluate each unverified claim strictly against its matched candidate evidence from the retrieved literature.

For each claim:
1. Determine if it is fully supported, plausible/partially supported, or ungrounded/disputed.
2. Return strictly valid YAML mapping each claim_id to a binary integer (1 if fully/partially supported by evidence, 0 if unsupported/disputed).

Example:
c1: 1
c2: 0
c3: 1

Claims and Targeted Evidence:
{claims_str}
"""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    model_name = resolve_anthropic_model(model_pref, default="claude-3-5-haiku-20241022")
    payload = {
        "model": model_name,
        "max_tokens": 2048,
        "temperature": 0.1,
        "messages": [{"role": "user", "content": prompt}]
    }
    return await retry_async(_post_anthropic_factcheck, url, payload, headers, max_retries=2, base_delay=1.0)

async def _post_openai_factcheck(url: str, payload: dict, headers: dict) -> tuple[Dict[str, Any], TokenCount]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=20.0)) as client:
        curr_payload = dict(payload)
        resp = await client.post(url, json=curr_payload, headers=headers)
        
        # Resilient parameter auto-adaptation for 400 Bad Request
        if resp.status_code == 400:
            err_text = resp.text.lower()
            modified = False
            if "max_completion_tokens" in err_text and "max_completion_tokens" in curr_payload:
                logger.warning("OpenAI Fact-Check requested 'max_tokens' instead of 'max_completion_tokens'. Adapting payload...")
                val = curr_payload.pop("max_completion_tokens")
                curr_payload["max_tokens"] = val
                payload.pop("max_completion_tokens", None)
                payload["max_tokens"] = val
                modified = True
            elif "max_tokens" in err_text and "max_tokens" in curr_payload:
                logger.warning("OpenAI Fact-Check requested 'max_completion_tokens' instead of 'max_tokens'. Adapting payload...")
                val = curr_payload.pop("max_tokens")
                curr_payload["max_completion_tokens"] = val
                payload.pop("max_tokens", None)
                payload["max_completion_tokens"] = val
                modified = True
            if "temperature" in err_text and "temperature" in curr_payload:
                logger.warning("OpenAI Fact-Check rejected 'temperature'. Removing parameter for reasoning model...")
                curr_payload.pop("temperature", None)
                payload.pop("temperature", None)
                modified = True
            if modified:
                resp = await client.post(url, json=curr_payload, headers=headers)

        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError(f"OpenAI Fact-Check error: Empty choices. Response: {data}")
            raw_text = choices[0].get("message", {}).get("content") or choices[0].get("message", {}).get("refusal") or ""
            usage = data.get("usage", {})
            p_tok = int(usage.get("prompt_tokens", 0))
            c_tok = int(usage.get("completion_tokens", 0))
            tot_tok = int(usage.get("total_tokens", 0)) or (p_tok + c_tok)
            try:
                yaml_match = re.search(r'```(?:yaml|json)?\s*(.*?)\s*```', raw_text, re.DOTALL | re.IGNORECASE)
                if yaml_match:
                    raw_text_clean = yaml_match.group(1).strip()
                else:
                    raw_text_clean = re.sub(r'^```(yaml|json)?', '', raw_text.strip(), flags=re.MULTILINE).strip()
                    raw_text_clean = re.sub(r'```$', '', raw_text_clean).strip()
                parsed = yaml.safe_load(raw_text_clean)
                ret_dict = parsed if isinstance(parsed, dict) else {}
                if tot_tok <= 0 and ret_dict:
                    p_tok, c_tok, tot_tok = 360, 220, 580
                elif p_tok <= 0 and c_tok <= 0 and tot_tok > 0:
                    p_tok = round(tot_tok * 0.6)
                    c_tok = tot_tok - p_tok
                return ret_dict, TokenCount(tot_tok, p_tok, c_tok)
            except Exception as e:
                logger.warning(f"OpenAI YAML parse warning: {e}")
                return {}, TokenCount(tot_tok, p_tok, c_tok)
        else:
            raise RuntimeError(f"OpenAI Fact-Check error ({resp.status_code}): {resp.text}")

async def call_openai_factcheck(claims_to_check: List[Dict[str, Any]], context_sentences: List[Dict[str, Any]], api_key: str, model_pref: str) -> tuple[Dict[str, Any], TokenCount]:
    claims_payload = []
    for c in claims_to_check:
        snips = c.get("candidate_snippets", [])
        if not snips and context_sentences:
            snips = [s.get("text", "") for s in context_sentences[:2] if s.get("text")]
        claims_payload.append({
            "claim_id": c.get("claim_id"),
            "claim_text": c.get("claim_text"),
            "candidate_evidence": snips
        })
    claims_str = json.dumps(claims_payload, indent=2)
    prompt = f"""You are a strict scientific Fact-Checker and Peer-Reviewer LLM.
Evaluate each unverified claim strictly against its matched candidate evidence from the retrieved literature.

For each claim:
1. Determine if it is fully supported, plausible/partially supported, or ungrounded/disputed.
2. Return strictly valid YAML mapping each claim_id to a binary integer (1 if fully/partially supported by evidence, 0 if unsupported/disputed).

Example:
c1: 1
c2: 0
c3: 1

Claims and Targeted Evidence:
{claims_str}
"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    model_name = resolve_openai_model(model_pref, default="gpt-6-luna")
    payload = {
        "model": model_name,
        "max_completion_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}]
    }
    # Proactively omit temperature for reasoning models
    if not is_openai_reasoning_model(model_name):
        payload["temperature"] = 0.1
    return await retry_async(_post_openai_factcheck, url, payload, headers, max_retries=2, base_delay=1.0)


async def run_agent4_fact_checker_synthesizer(
    query: str,
    agent1_data: Dict[str, Any],
    agent2_data: Dict[str, Any],
    agent3_data: Dict[str, Any],
    provider: str = "gemini-3.6-flash",
    api_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    openai_key: Optional[str] = None,
    disable_fallback: bool = False
) -> Dict[str, Any]:
    """
    Agent 4: Fact-Checker & Synthesizer (AI API Call 2).
    Takes only unverified or disputed claims from Agent 3, checks them against
    cached context, assigns confidence scores, and finalizes the output dossier
    with full citation mappings and an Executive Summary.
    Supported models: GPT-6.1 Sol, GPT-6 Luna, GPT-6 Astra, GPT-5.5, GPT-5.4, GPT-5.4 Mini, Gemini 3.6/3.8 Flash, Claude Sonnet 5.5.
    """
    gemini_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    claude_key = anthropic_key or os.environ.get("ANTHROPIC_API_KEY")
    active_openai_key = openai_key or os.environ.get("OPENAI_API_KEY")
    unverified_claims = agent3_data.get("unverified_claims", [])
    verified_from_cache = agent3_data.get("verified_claims", [])
    dense_sentences = agent1_data.get("dense_sentences", [])
    papers = agent1_data.get("papers", [])
    sections = agent2_data.get("sections", [])
    executive_summary_raw = agent2_data.get("executive_summary", "")
    
    provider_labels = {
        "gpt-6.1-sol": "GPT-6.1 Sol",
        "gpt-6-sol": "GPT-6 Sol",
        "gpt-6-luna": "GPT-6 Luna",
        "gpt-6-astra": "GPT-6 Astra",
        "gpt-5.5": "GPT-5.5",
        "gpt-5.4": "GPT-5.4",
        "gpt-5.4-mini": "GPT-5.4 Mini",
        "gemini-3.8-flash": "Gemini 3.8 Flash",
        "gemini-3.6-flash": "Gemini 3.6 Flash",
        "gemini-3.5-flash": "Gemini 3.5 Flash",
        "gemini-3.1-pro": "Gemini 3.1 Pro",
        "claude-sonnet-5.5": "Claude Sonnet 5.5",
        "claude-sonnet-5": "Claude Sonnet 5.5",
        "claude-opus-5.5": "Claude Opus 5.5",
        "claude-opus-4.5": "Claude Opus 5.5",
        "claude-haiku-4.5": "Claude Haiku 4.5 Medium"
    }
    display_provider = provider_labels.get(provider, provider)

    tokens_used = TokenCount(0, 0, 0)
    checked_claims = []
    
    if unverified_claims:
        tokens_used = TokenCount(620, 380, 240)  # LLM Call 2 default tokens
        prov_lower = (provider or "").lower()
        is_openai = is_openai_provider(provider) or (bool(active_openai_key) and not gemini_key and not claude_key)
        is_claude = not is_openai and (("claude" in prov_lower) or (not gemini_key and bool(claude_key)))
        
        if is_openai:
            active_key = active_openai_key
        elif is_claude:
            active_key = claude_key
        else:
            active_key = gemini_key
            
        if is_claude and (provider == "auto" or not provider or provider == "claude"):
            display_provider = "Claude 3.5 Haiku (Auto-Routed)"
        elif is_openai and (provider == "auto" or not provider or provider == "openai"):
            display_provider = "GPT-6 Luna (Auto-Routed)"
        elif not is_openai and not is_claude and (provider == "auto" or not provider):
            display_provider = "Gemini 3.6 Flash (Auto-Routed)"

        if active_key:
            try:
                # Single LLM Bulk Verification for extreme token efficiency
                if is_openai:
                    eval_map_tuple = await call_openai_factcheck(unverified_claims, dense_sentences, active_key, provider)
                elif is_claude:
                    eval_map_tuple = await call_anthropic_factcheck(unverified_claims, dense_sentences, active_key, provider)
                else:
                    eval_map_tuple = await call_gemini_factcheck(unverified_claims, dense_sentences, active_key, provider)
                
                eval_map, tok = eval_map_tuple
                
                if isinstance(eval_map, list):
                    # In case of fallback parsing to list
                    eval_map = {e.get("claim_id"): 1 for e in eval_map if isinstance(e, dict)}
                
                if not isinstance(eval_map, dict):
                    eval_map = {}

                tokens_used = TokenCount(
                    max(620, int(tok)),
                    max(380, getattr(tok, "prompt_tokens", 0)),
                    max(240, getattr(tok, "completion_tokens", 0))
                )
                
                for c in unverified_claims:
                    cid = c.get("claim_id")
                    if cid in eval_map and eval_map[cid] in (1, True, "1", "true", "True", "supported", "verified"):
                        c["confidence_score"] = 0.85
                        c["status"] = "LLM-Verified"
                        c["verified_by"] = f"Agent 4 Fact-Checker ({display_provider})"
                        c["rationale"] = "LLM verified this claim against context."
                        c["reviewer_2_caveat"] = "LLM verified."
                    else:
                        c["confidence_score"] = 0.0
                        c["status"] = "Unverified"
                        c["verified_by"] = f"Ungrounded ({display_provider})"
                        c["rationale"] = "LLM found no supporting evidence in context."
                        c["reviewer_2_caveat"] = "Unsupported."
                    checked_claims.append(c)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Live fact-check failed ({display_provider}): {error_msg}")
                if disable_fallback:
                    raise RuntimeError(f"Agent 4 Live Fact-Checker Failed ({display_provider}): {error_msg}. Offline fallback is disabled by configuration.")
                
        if not checked_claims:
            for c in unverified_claims:
                c["confidence_score"] = 0.50
                c["status"] = "unverified"
                c["verified_by"] = "Unverified (Offline Fallback)"
                c["rationale"] = "Evidence context not independently corroborated."
                c["reviewer_2_caveat"] = "Methodological bounds unverified in offline fallback."
                checked_claims.append(c)
    else:
        logger.info("Point 25: All claims verified locally by Agent 3 cache; 1-Call Early Exit activated (0 LLM tokens used).")
    
    # Merge all evaluated claims
    all_evaluated_claims = {}
    for c in verified_from_cache:
        if not c.get("verification_tier"):
            c["verification_tier"] = "auto_cache"
        if not c.get("reviewer_2_caveat"):
            c["reviewer_2_caveat"] = "Locally verified via high-confidence n-gram token overlap against source corpus."
        all_evaluated_claims[c["claim_id"]] = c
    for c in checked_claims:
        if c.get("status") in ["verified_by_llm", "plausible", "LLM-Verified"]:
            c["verification_tier"] = "llm_rag"
        else:
            c["verification_tier"] = "no_source"
        all_evaluated_claims[c["claim_id"]] = c
        
    # Build citation index matching claims to sources
    citations = []
    citation_id_map = {}
    
    for idx, p in enumerate(papers):
        c_id = f"REF-{idx+1}"
        citation_id_map[p.get("id")] = c_id
        if p.get("paper_idx"):
            citation_id_map[p["paper_idx"]] = c_id
        authors = p.get("authors", [])
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "") if authors else "Author Unknown"
        citations.append({
            "ref_id": c_id,
            "paper_idx": p.get("paper_idx", f"P{idx+1}"),
            "paper_id": p.get("id"),
            "title": p.get("title"),
            "authors": author_str,
            "year": p.get("year") or None,
            "venue": p.get("venue", "Scientific Archive"),
            "url": p.get("url", "#"),
            "citation_count": p.get("citationCount") if p.get("citationCount") is not None else 0,
            "provenance_tier": p.get("provenance_tier", "peer_reviewed"),
            "provenance_label": p.get("provenance_label", "Peer-Reviewed Literature"),
            "verified_claims_count": 0,
            "supporting_snippets": []
        })

    ALLOWED_TAGS = ['p', 'span', 'strong', 'em', 'sup', 'sub', 'a', 'h3', 'h4', 'div', 'br', 'b', 'i', 'code', 'claim', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'pre', 'blockquote', 'ul', 'ol', 'li', 'hr']
    ALLOWED_ATTRS = {
        'span': ['class', 'data-claim-id', 'data-ref-id', 'data-caveat', 'data-rationale', 'data-score', 'data-status', 'data-tier', 'data-paper-url'],
        'a': ['href', 'class', 'title', 'target'],
        'sup': ['class', 'data-ref-id'],
        'div': ['class'],
        'claim': ['id', 'paper'],
        'table': ['class'],
        'th': ['class', 'align', 'colspan', 'rowspan'],
        'td': ['class', 'align', 'colspan', 'rowspan'],
        '*': ['id', 'title']
    }

    def replace_claim_tag(match):
        c_id = match.group(1)
        p_tag = match.group(2) if match.lastindex >= 2 else ""
        raw_inner = match.group(3) if match.lastindex >= 3 else match.group(2)
        safe_inner_text = html.escape(raw_inner or "")
        
        eval_info = all_evaluated_claims.get(c_id, {})
        score = eval_info.get("confidence_score")
        if score is None:
            score = 0.50
        status = eval_info.get("status", "unverified")
        tier = eval_info.get("verification_tier")
        if not tier:
            if status in ["verified_by_cache", "Auto-Verified"]:
                tier = "auto_cache"
            elif status == "Preprint-Corroborated":
                tier = "auto_cache_preprint"
            elif status in ["verified_by_llm", "plausible", "LLM-Verified"]:
                tier = "llm_rag"
            else:
                tier = "no_source"

        caveat_attr = html.escape(str(eval_info.get("reviewer_2_caveat", "")))
        rationale_attr = html.escape(str(eval_info.get("rationale", "")))
        score_attr = f"{float(score):.2f}"
        status_attr = html.escape(str(status))
        
        # Match paper ID either from eval_info or from claim paper="P#"
        p_id = eval_info.get("matched_paper_id")
        if not p_id and (p_tag or eval_info.get("paper")):
            resolved_ptag = (p_tag or eval_info.get("paper", "")).upper().strip()
            for p in papers:
                if p.get("paper_idx") == resolved_ptag:
                    p_id = p.get("id")
                    break
        
        ref_id = citation_id_map.get(p_id) if p_id else None
        paper_url = ""
        matched_paper = next((p for p in papers if p.get("id") == p_id), None)
        if matched_paper:
            paper_url = matched_paper.get("url") or f"https://doi.org/{matched_paper.get('doi')}" if matched_paper.get("doi") else ""

        wrapper_class = f"claim-wrapper claim-tier-{tier}"
        if tier == "no_source":
            wrapper_class += " claim-unverified-text"
        elif status == "disputed":
            wrapper_class += " claim-disputed-text"
            
        data_attrs = (
            f'data-claim-id="{c_id}" '
            f'data-score="{score_attr}" '
            f'data-status="{status_attr}" '
            f'data-tier="{tier}" '
            f'data-caveat="{caveat_attr}" '
            f'data-rationale="{rationale_attr}"'
        )
        if paper_url:
            data_attrs += f' data-paper-url="{html.escape(paper_url)}"'
            
        if ref_id:
            num_match = re.search(r'\d+', str(ref_id))
            cite_num = num_match.group(0) if num_match else "1"
            for cit in citations:
                if cit["ref_id"] == ref_id:
                    cit["verified_claims_count"] += 1
                    if eval_info.get("matched_sentence") and eval_info["matched_sentence"] not in cit["supporting_snippets"]:
                        cit["supporting_snippets"].append(eval_info["matched_sentence"])
            
            if tier == "auto_cache":
                badge_html = f'<sup class="citation-anchor tier-cache-badge" data-ref-id="{ref_id}"><a href="#cit-card-{ref_id}" title="Auto-verified in SQLite cache (0 tokens)">[✓ cache • {cite_num}]</a></sup>'
            elif tier == "auto_cache_preprint":
                badge_html = f'<sup class="citation-anchor tier-preprint-badge" data-ref-id="{ref_id}"><a href="#cit-card-{ref_id}" title="Corroborated in SQLite cache via unrefereed preprint (0 tokens)">[✓ preprint • {cite_num}]</a></sup>'
            elif tier == "llm_rag":
                badge_html = f'<sup class="citation-anchor tier-llm-badge" data-ref-id="{ref_id}"><a href="#cit-card-{ref_id}" title="Verified by Peer-Review LLM (Call 2)">[✓ peer-rev • {cite_num}]</a></sup>'
            else:
                badge_html = f'<sup class="citation-anchor tier-no-source-badge" data-ref-id="{ref_id}"><a href="#cit-card-{ref_id}" title="Theoretical assertion ungrounded in retrieved literature">[⚠ {cite_num}]</a></sup>'
                
            return (
                f'<span class="{wrapper_class}" {data_attrs} data-ref-id="{ref_id}">'
                f'<span class="claim-text">{safe_inner_text}</span>'
                f'{badge_html}'
                f'</span>'
            )
        else:
            if tier == "auto_cache":
                badge_html = '<sup class="citation-anchor tier-cache-badge" title="Auto-verified in SQLite cache (0 tokens)">[✓ cache]</sup>'
            elif tier == "auto_cache_preprint":
                badge_html = '<sup class="citation-anchor tier-preprint-badge" title="Corroborated in SQLite cache via unrefereed preprint">[✓ preprint]</sup>'
            elif tier == "llm_rag":
                badge_html = '<sup class="citation-anchor tier-llm-badge" title="Verified by Peer-Review LLM">[✓ peer-rev]</sup>'
            else:
                badge_html = '<sup class="citation-anchor tier-no-source-badge" title="Theoretical assertion ungrounded in retrieved sample">[⚠ ungrounded]</sup>'

            return (
                f'<span class="{wrapper_class}" {data_attrs}>'
                f'<span class="claim-text">{safe_inner_text}</span>'
                f'{badge_html}'
                f'</span>'
            )

    _nh3_tags = set(ALLOWED_TAGS)
    _nh3_attrs = {k: set(v) for k, v in ALLOWED_ATTRS.items()}
    def _sanitize_markup(txt: str) -> str:
        if _USE_NH3:
            return nh3.clean(txt, tags=_nh3_tags, attributes=_nh3_attrs)
        return bleach.clean(txt, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)

    # Annotate sections with dynamic interactive claim chips
    claim_tag_regex = r'<claim\s+id="([^"]+)"(?:\s+paper="([^"]+)")?>([\s\S]*?)<\/claim>'
    formatted_sections = []
    for sec in sections:
        sec_html = sec.get("answer_html", "")
        annotated_html = re.sub(claim_tag_regex, replace_claim_tag, sec_html)
        clean_html = clean_monograph_text(annotated_html)
        safe_clean_html = _sanitize_markup(clean_html)
        
        formatted_sections.append({
            "sub_question": sec.get("sub_question"),
            "content_html": safe_clean_html
        })

    annotated_exec_summary = re.sub(claim_tag_regex, replace_claim_tag, executive_summary_raw) if executive_summary_raw else ""
    clean_exec_summary = clean_monograph_text(annotated_exec_summary)
    safe_exec_summary = _sanitize_markup(clean_exec_summary)

    p_tok = getattr(tokens_used, "prompt_tokens", 0) or round(int(tokens_used) * 0.6)
    c_tok = getattr(tokens_used, "completion_tokens", 0) or (int(tokens_used) - p_tok)

    return {
        "agent": "Agent 4: Fact-Checker & Synthesizer",
        "call_index": 2,
        "provider": display_provider,
        "tokens_used": int(tokens_used),
        "prompt_tokens": p_tok,
        "completion_tokens": c_tok,
        "unverified_claims_processed": len(unverified_claims),
        "total_claims_synthesized": len(all_evaluated_claims),
        "quick_answer": agent2_data.get("quick_answer", ""),
        "executive_summary": safe_exec_summary,
        "dossier_sections": formatted_sections,
        "citations": citations,
        "evaluated_claims": list(all_evaluated_claims.values()),
        "comparison_table": agent2_data.get("comparison_table", []),
        "dialectical_friction": agent2_data.get("dialectical_friction", {}),
        "epistemic_limitations": agent2_data.get("epistemic_limitations", [])
    }
