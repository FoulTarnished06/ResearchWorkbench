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
from backend.agents.agent2_drafter import safe_parse_json, TokenCount, resolve_anthropic_model, resolve_openai_model, get_wire_openai_model, is_openai_reasoning_model, is_openai_provider
from backend.agents.agent1_scraper import classify_paper_provenance

logger = get_logger("Agent4_Synthesizer")

def parse_factcheck_response(raw_text: str) -> Dict[str, Any]:
    if not raw_text or not isinstance(raw_text, str):
        return {}
    clean_text = raw_text.strip()
    match = re.search(r'```(?:json|yaml)?\s*([\s\S]*?)\s*```', clean_text)
    if match:
        clean_text = match.group(1).strip()
    else:
        clean_text = re.sub(r'^```[a-zA-Z]*', '', clean_text, flags=re.MULTILINE).strip()
        clean_text = re.sub(r'```$', '', clean_text).strip()
    try:
        data = safe_parse_json(clean_text)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {
                str(item.get("claim_id") or item.get("id") or f"c{i+1}"): item
                for i, item in enumerate(data)
                if isinstance(item, dict)
            }
    except Exception:
        pass
    try:
        data = json.loads(clean_text, strict=False)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {
                str(item.get("claim_id") or item.get("id") or f"c{i+1}"): item
                for i, item in enumerate(data)
                if isinstance(item, dict)
            }
    except Exception:
        pass
    try:
        data = yaml.safe_load(clean_text)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {
                str(item.get("claim_id") or item.get("id") or f"c{i+1}"): item
                for i, item in enumerate(data)
                if isinstance(item, dict)
            }
    except Exception:
        pass
    return {}

def build_factcheck_prompt(claims_to_check: List[Dict[str, Any]], context_sentences: List[Dict[str, Any]]) -> str:
    claims_payload = []
    for c in claims_to_check:
        raw_snips = c.get("candidate_evidence") or c.get("candidate_snippets") or []
        clean_snips = []
        if isinstance(raw_snips, list):
            for s in raw_snips[:4]:
                if isinstance(s, dict):
                    t = (s.get("text") or s.get("matched_sentence") or "").strip()
                    title = s.get("paper_title") or s.get("paper_id") or ""
                    if t:
                        clean_snips.append(f"[{title}] {t}" if title else t)
                elif isinstance(s, str) and s.strip():
                    clean_snips.append(s.strip())
        if not clean_snips and context_sentences:
            clean_snips = [s.get("text", "").strip() for s in context_sentences[:3] if s.get("text")]
        claims_payload.append({
            "claim_id": c.get("claim_id") or c.get("id"),
            "claim_text": c.get("claim_text") or c.get("text"),
            "candidate_evidence": clean_snips
        })
    claims_str = json.dumps(claims_payload, indent=2)
    return f"""You are a Principal Scientific Fact-Checker and Senior Peer-Reviewer.
Evaluate each unverified claim strictly against its matched candidate evidence from the retrieved academic literature.

For each claim:
- "status": "Supported" (empirically/theoretically entailed by evidence), "Partially Supported" (partial entailment or directional match), or "Unsupported" (no evidence found, contradictory, or orthogonal).
- "confidence_score": Float from 0.0 to 1.0 (0.85-1.0 for Supported, 0.50-0.80 for Partially Supported, 0.0-0.30 for Unsupported).
- "rationale": 1-2 concise sentences explaining why the claim is or is not entailed by the candidate evidence.
- "supporting_quote": Verbatim excerpt from the candidate evidence that supports the claim, or null if unsupported.

Return strictly a valid JSON object mapping each claim_id to its evaluation object:
{{
  "c1": {{
    "status": "Supported",
    "confidence_score": 0.95,
    "rationale": "Directly corroborated by reported benchmark measurements.",
    "supporting_quote": "..."
  }}
}}

Claims and Targeted Evidence:
{claims_str}
"""

def resolve_gemini_factcheck_model(model_pref: str, default: str = "gemini-2.5-flash") -> str:
    pref = (model_pref or "").lower().strip()
    if pref in {"gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"}:
        return pref
    if "pro" in pref:
        if "1.5" in pref:
            return "gemini-1.5-pro"
        return "gemini-2.5-pro"
    if "1.5" in pref:
        return "gemini-1.5-flash"
    return default

async def _post_gemini_factcheck(url: str, payload: dict, headers: dict) -> tuple[Dict[str, Any], TokenCount]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=20.0)) as client:
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
            ret_dict = parse_factcheck_response(raw_text)
            if tot_tok <= 0:
                p_tok = max(1, len(str(payload).split()))
                c_tok = max(1, len(raw_text.split()))
                tot_tok = p_tok + c_tok
            elif p_tok <= 0 and c_tok <= 0 and tot_tok > 0:
                p_tok = round(tot_tok * 0.6)
                c_tok = tot_tok - p_tok
            return ret_dict, TokenCount(tot_tok, p_tok, c_tok)
        else:
            raise RuntimeError(f"Gemini Fact-Check error ({resp.status_code}): {resp.text}")

async def call_gemini_factcheck(claims_to_check: List[Dict[str, Any]], context_sentences: List[Dict[str, Any]], api_key: str, model_pref: str = "gemini-2.5-flash") -> tuple[Dict[str, Any], TokenCount]:
    prompt = build_factcheck_prompt(claims_to_check, context_sentences)
    model = resolve_gemini_factcheck_model(model_pref)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
            "response_mime_type": "application/json"
        }
    }
    return await retry_async(_post_gemini_factcheck, url, payload, headers, max_retries=2, base_delay=1.0)

async def _post_anthropic_factcheck(url: str, payload: dict, headers: dict) -> tuple[Dict[str, Any], TokenCount]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=20.0)) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            raw_text = data.get("content", [{}])[0].get("text", "")
            usage = data.get("usage", {})
            p_tok = int(usage.get("input_tokens", 0))
            c_tok = int(usage.get("output_tokens", 0))
            tot_tok = p_tok + c_tok
            ret_dict = parse_factcheck_response(raw_text)
            if tot_tok <= 0:
                p_tok = max(1, len(str(payload).split()))
                c_tok = max(1, len(raw_text.split()))
                tot_tok = p_tok + c_tok
            elif p_tok <= 0 and c_tok <= 0 and tot_tok > 0:
                p_tok = round(tot_tok * 0.6)
                c_tok = tot_tok - p_tok
            return ret_dict, TokenCount(tot_tok, p_tok, c_tok)
        else:
            raise RuntimeError(f"Anthropic Fact-Check error ({resp.status_code}): {resp.text}")

async def call_anthropic_factcheck(claims_to_check: List[Dict[str, Any]], context_sentences: List[Dict[str, Any]], api_key: str, model_pref: str) -> tuple[Dict[str, Any], TokenCount]:
    prompt = build_factcheck_prompt(claims_to_check, context_sentences)
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    model_name = resolve_anthropic_model(model_pref, default="claude-3-5-haiku-20241022")
    payload = {
        "model": model_name,
        "max_tokens": 4096,
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
                val = curr_payload.pop("max_completion_tokens")
                curr_payload["max_tokens"] = val
                payload.pop("max_completion_tokens", None)
                payload["max_tokens"] = val
                modified = True
            elif "max_tokens" in err_text and "max_tokens" in curr_payload:
                val = curr_payload.pop("max_tokens")
                curr_payload["max_completion_tokens"] = val
                payload.pop("max_tokens", None)
                payload["max_completion_tokens"] = val
                modified = True
            if "temperature" in err_text and "temperature" in curr_payload:
                curr_payload.pop("temperature", None)
                payload.pop("temperature", None)
                modified = True
            if "response_format" in err_text and "response_format" in curr_payload:
                curr_payload.pop("response_format", None)
                payload.pop("response_format", None)
                modified = True
            if modified:
                resp = await client.post(url, json=curr_payload, headers=headers)

        if resp.status_code == 404 or any(k in resp.text.lower() for k in ("model_not_found", "does not exist", "not found")):
            raise RuntimeError(f"OpenAI Fact-Check model '{curr_payload.get('model')}' was not found or is unavailable on endpoint ({resp.status_code}): {resp.text}")

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
            ret_dict = parse_factcheck_response(raw_text)
            if tot_tok <= 0:
                p_tok = max(1, len(str(payload).split()))
                c_tok = max(1, len(raw_text.split()))
                tot_tok = p_tok + c_tok
            elif p_tok <= 0 and c_tok <= 0 and tot_tok > 0:
                p_tok = round(tot_tok * 0.6)
                c_tok = tot_tok - p_tok
            return ret_dict, TokenCount(tot_tok, p_tok, c_tok)
        else:
            raise RuntimeError(f"OpenAI Fact-Check error ({resp.status_code}): {resp.text}")

async def call_openai_factcheck(claims_to_check: List[Dict[str, Any]], context_sentences: List[Dict[str, Any]], api_key: str, model_pref: str) -> tuple[Dict[str, Any], TokenCount]:
    prompt = build_factcheck_prompt(claims_to_check, context_sentences)
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    canonical_model = resolve_openai_model(model_pref, default="gpt-6-luna")
    wire_model = get_wire_openai_model(canonical_model)
    payload = {
        "model": wire_model,
        "max_completion_tokens": 8192,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}]
    }
    if not is_openai_reasoning_model(wire_model):
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
        "gpt-6-sol": "GPT-6.1 Sol",
        "gpt-6-luna": "GPT-6 Luna",
        "gpt-6-astra": "GPT-6 Astra",
        "gpt-5.5": "GPT-5.5",
        "gemini-2.5-flash": "Gemini 2.5 Flash",
        "gemini-2.5-pro": "Gemini 2.5 Pro",
        "gemini-1.5-flash": "Gemini 1.5 Flash",
        "gemini-1.5-pro": "Gemini 1.5 Pro",
        "claude-3-7-sonnet-20250219": "Claude 3.7 Sonnet",
        "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
        "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
        "claude-3-opus-20240229": "Claude 3 Opus"
    }
    display_provider = provider_labels.get(provider, provider)

    tokens_used = TokenCount(0, 0, 0)
    checked_claims = []
    
    if unverified_claims:
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
            display_provider = "Gemini 2.5 Flash (Auto-Routed)"

        if not active_key:
            raise RuntimeError(f"Agent 4 requires an API key for {display_provider}. No offline fallback is permitted. Please configure your API key in Settings.")

        try:
            # Single LLM Bulk Verification for extreme token efficiency
            if is_openai:
                eval_map_tuple = await call_openai_factcheck(unverified_claims, dense_sentences, active_key, provider)
            elif is_claude:
                eval_map_tuple = await call_anthropic_factcheck(unverified_claims, dense_sentences, active_key, provider)
            else:
                eval_map_tuple = await call_gemini_factcheck(unverified_claims, dense_sentences, active_key, provider)
            
            eval_map, tok = eval_map_tuple
            tokens_used = tok
            
            if isinstance(eval_map, list):
                eval_map = {e.get("claim_id"): e for e in eval_map if isinstance(e, dict)}
            
            if not isinstance(eval_map, dict):
                eval_map = {}
            
            # Build normalized lookup mapping (e.g., 'c1', '1', 'claim1', 'claim_1')
            normalized_eval_map = {}
            for k, v in eval_map.items():
                if k is not None:
                    k_str = str(k).strip().lower()
                    normalized_eval_map[k_str] = v
                    k_clean = re.sub(r'^(?:claim|c)[\-_]?', '', k_str)
                    if k_clean:
                        normalized_eval_map[k_clean] = v

            for c in unverified_claims:
                cid = str(c.get("claim_id") or c.get("id") or "")
                cid_clean = re.sub(r'^(?:claim|c)[\-_]?', '', cid.lower().strip())
                eval_entry = eval_map.get(cid) or normalized_eval_map.get(cid.lower().strip()) or normalized_eval_map.get(cid_clean)
                if eval_entry:
                    if isinstance(eval_entry, dict):
                        status_val = str(eval_entry.get("status", "Supported"))
                        conf_val = float(eval_entry.get("confidence_score", 0.90 if "support" in status_val.lower() else 0.10))
                        rat_val = str(eval_entry.get("rationale") or f"Entailment evaluation: {status_val}.")
                        quote_val = eval_entry.get("supporting_quote")
                    else:
                        is_supp = eval_entry in (1, True, "1", "true", "True", "supported", "verified")
                        status_val = "Supported" if is_supp else "Unsupported"
                        conf_val = 0.90 if is_supp else 0.10
                        rat_val = "Corroborated by retrieved literature." if is_supp else "No empirical evidence identified."
                        quote_val = None

                    c["confidence_score"] = round(conf_val, 2)
                    c["status"] = "LLM-Verified" if ("support" in status_val.lower() and conf_val >= 0.50) else "Unverified"
                    c["verified_by"] = f"Agent 4 Fact-Checker ({display_provider})"
                    c["rationale"] = rat_val
                    c["reviewer_2_caveat"] = f"Peer-Reviewed ({status_val})" if conf_val >= 0.50 else "Unsupported Claim"
                    if quote_val:
                        c["supporting_quote"] = quote_val
                else:
                    c["confidence_score"] = 0.0
                    c["status"] = "Unverified"
                    c["verified_by"] = f"Ungrounded ({display_provider})"
                    c["rationale"] = "No matching empirical evidence identified in retrieved literature."
                    c["reviewer_2_caveat"] = "Unsupported."
                checked_claims.append(c)
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Live fact-check failed ({display_provider}): {error_msg}")
            raise RuntimeError(f"Agent 4 Live Fact-Checker Failed ({display_provider}): {error_msg}. Offline fallback is completely disabled.")
    else:
        logger.info("Point 25: All claims verified locally by Agent 3 cache; 1-Call Early Exit activated (0 LLM tokens used).")
    
    # Merge all evaluated claims without polluting dictionary with alias duplicates
    all_evaluated_claims = {}
    for idx, c in enumerate(verified_from_cache):
        if not c.get("verification_tier"):
            c["verification_tier"] = "auto_cache"
        if not c.get("reviewer_2_caveat"):
            c["reviewer_2_caveat"] = "Locally verified via high-confidence n-gram token overlap against source corpus."
        cid = str(c.get("claim_id") or c.get("id") or f"c_cache_{idx+1}")
        c["claim_id"] = cid
        c["id"] = cid
        all_evaluated_claims[cid] = c

    for idx, c in enumerate(checked_claims):
        if c.get("status") in ["verified_by_llm", "plausible", "LLM-Verified"]:
            c["verification_tier"] = "llm_rag"
        else:
            c["verification_tier"] = "no_source"
        cid = str(c.get("claim_id") or c.get("id") or f"c_check_{idx+1}")
        c["claim_id"] = cid
        c["id"] = cid
        all_evaluated_claims[cid] = c

    def get_evaluated_claim(target_cid: str) -> Dict[str, Any]:
        if not target_cid:
            return {}
        if target_cid in all_evaluated_claims:
            return all_evaluated_claims[target_cid]
        c_low = target_cid.lower().strip()
        if c_low in all_evaluated_claims:
            return all_evaluated_claims[c_low]
        c_clean = re.sub(r'^(?:claim|c)[\-_]?', '', c_low)
        for variant in (c_clean, f"c{c_clean}", f"c_{c_clean}", f"claim{c_clean}", f"claim_{c_clean}"):
            if variant in all_evaluated_claims:
                return all_evaluated_claims[variant]
        return {}
        
    # Build citation index matching claims to sources
    citations = []
    citation_id_map = {}
    
    for idx, p in enumerate(papers):
        c_id = f"REF-{idx+1}"
        p_unique_id = p.get("id")
        if p_unique_id:
            citation_id_map[str(p_unique_id)] = c_id
            citation_id_map[str(p_unique_id).lower()] = c_id
        if p.get("paper_idx"):
            p_idx_str = str(p["paper_idx"]).strip()
            citation_id_map[p_idx_str] = c_id
            citation_id_map[p_idx_str.upper()] = c_id
            citation_id_map[p_idx_str.lower()] = c_id
            clean_num = re.sub(r'^P', '', p_idx_str, flags=re.I)
            if clean_num:
                citation_id_map[clean_num] = c_id
        citation_id_map[str(idx+1)] = c_id
        citation_id_map[f"P{idx+1}"] = c_id
        citation_id_map[f"p{idx+1}"] = c_id

        authors = p.get("authors", [])
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "") if authors else "Author Unknown"
        
        prov_tier = p.get("provenance_tier")
        prov_lbl = p.get("provenance_label")
        if not prov_tier or not prov_lbl:
            prov_tier, prov_lbl = classify_paper_provenance(p)
            
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
            "provenance_tier": prov_tier,
            "provenance_label": prov_lbl,
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

    claim_tag_regex = re.compile(r'<claim\b([^>]*)>([\s\S]*?)<\/claim>', re.IGNORECASE)

    def replace_claim_tag(match):
        attrs_str = match.group(1)
        raw_inner = match.group(2)
        id_m = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attrs_str, re.IGNORECASE)
        p_m = re.search(r'\bpaper\s*=\s*["\']([^"\']+)["\']', attrs_str, re.IGNORECASE)
        c_id = id_m.group(1).strip() if id_m else ""
        p_tag = p_m.group(1).strip() if p_m else ""
        safe_inner_text = html.escape(raw_inner or "")
        
        eval_info = get_evaluated_claim(c_id)
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
                p_idx = (p.get("paper_idx") or "").upper().strip()
                if p_idx in (resolved_ptag, f"P{resolved_ptag}") or resolved_ptag in (p_idx, f"P{p_idx}"):
                    p_id = p.get("id") or p.get("paper_idx")
                    break
        
        ref_id = citation_id_map.get(str(p_id)) if p_id else None
        if not ref_id and p_tag:
            p_tag_clean = p_tag.upper().strip()
            ref_id = citation_id_map.get(p_tag_clean) or citation_id_map.get(p_tag_clean.lower()) or citation_id_map.get(re.sub(r'^P', '', p_tag_clean))
        if not ref_id and tier in ("llm_rag", "auto_cache", "auto_cache_preprint") and citations:
            ref_id = citations[0]["ref_id"]

        paper_url = ""
        matched_paper = next((p for p in papers if p.get("id") == p_id or p.get("paper_idx") == p_id), None)
        if matched_paper:
            paper_url = matched_paper.get("url") or (f"https://doi.org/{matched_paper.get('doi')}" if matched_paper.get("doi") else "")

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
    formatted_sections = []
    for sec in sections:
        sec_html = sec.get("answer_html", "")
        clean_html = clean_monograph_text(sec_html)
        annotated_html = claim_tag_regex.sub(replace_claim_tag, clean_html)
        safe_clean_html = _sanitize_markup(annotated_html)
        
        formatted_sections.append({
            "sub_question": sec.get("sub_question"),
            "content_html": safe_clean_html
        })

    clean_exec_summary = clean_monograph_text(executive_summary_raw) if executive_summary_raw else ""
    annotated_exec_summary = claim_tag_regex.sub(replace_claim_tag, clean_exec_summary)
    safe_exec_summary = _sanitize_markup(annotated_exec_summary)

    p_tok = getattr(tokens_used, "prompt_tokens", 0) or round(int(tokens_used) * 0.6)
    c_tok = getattr(tokens_used, "completion_tokens", 0) or (int(tokens_used) - p_tok)

    # Prune bibliography to strictly cited references in text or verified claims
    full_monograph_text = f"{safe_exec_summary} " + " ".join(s["content_html"] for s in formatted_sections)
    cited_p_tags = {p.upper() for p in re.findall(r'\[(P\d+)\]', full_monograph_text, re.IGNORECASE)}
    cited_ref_ids = {r.upper() for r in re.findall(r'data-ref-id="([^"]+)"', full_monograph_text, re.IGNORECASE)}
    cited_ref_brackets = {r.upper() for r in re.findall(r'\[(REF-\d+)\]', full_monograph_text, re.IGNORECASE)}

    active_citations = []
    for cit in citations:
        p_idx = str(cit.get("paper_idx", "")).upper()
        r_id = str(cit.get("ref_id", "")).upper()
        if (p_idx and p_idx in cited_p_tags) or (r_id and r_id in cited_ref_ids) or (r_id and r_id in cited_ref_brackets) or (cit.get("verified_claims_count", 0) > 0):
            active_citations.append(cit)

    final_citations = active_citations if active_citations else citations[:4]

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
        "citations": final_citations,
        "evaluated_claims": list(all_evaluated_claims.values()),
        "comparison_table": agent2_data.get("comparison_table", []),
        "dialectical_friction": agent2_data.get("dialectical_friction", {}),
        "epistemic_limitations": agent2_data.get("epistemic_limitations", [])
    }
