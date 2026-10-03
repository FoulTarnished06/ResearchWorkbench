import asyncio
import random
from typing import Callable, Any
from backend.logger import get_logger

logger = get_logger("RetryManager")

async def retry_async(
    fn: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    retryable_codes: set = None,
    **kwargs: Any
) -> Any:
    """
    Executes an async callable with exponential backoff and jitter.
    Never retries permanent client errors (400, 401, 403, 404).
    """
    if retryable_codes is None:
        retryable_codes = {429, 500, 502, 503, 504}

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            err_msg = str(e)
            
            # Do not retry on permanent client-side authentication/malformed issues
            is_permanent = False
            # Check if exception has response or status_code attribute
            resp = getattr(e, "response", None)
            status_code = getattr(resp, "status_code", None) or getattr(e, "status_code", None)
            if status_code in (400, 401, 403, 404):
                is_permanent = True
            else:
                # Structural regex matching (e.g. "status_code: 400" or "HTTP 401" or "(404)")
                import re as _re
                match = _re.search(r'(?:status[_ ]?code|http|error|code)[:\s(]*\b(4\d{2})\b', err_msg, _re.IGNORECASE)
                if match and int(match.group(1)) in (400, 401, 403, 404):
                    is_permanent = True

            if is_permanent:
                logger.error(f"Permanent HTTP error detected ({e}). Aborting retry.")
                raise

            if attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed ({e}). "
                    f"Retrying in {delay:.2f}s with exponential backoff..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {max_retries} retries exhausted. Operation failed: {e}")
                raise last_error
