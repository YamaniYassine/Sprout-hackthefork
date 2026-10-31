"""
Bedrock access layer: boto3 clients, a single global throttle shared by every
call (retrieve + converse), retry with exponential backoff on
ThrottlingException, and a disk cache keyed by a hash of the request so the
same call is never made twice.

Everything else in the app must call Bedrock only through this module.
"""

import hashlib
import json
import os
import time

import boto3
from botocore.exceptions import ClientError

from core import config

_last_call_time = 0.0  # module-level: shared by every call, enforces the global throttle

_agent_runtime_client = None
_bedrock_runtime_client = None


def _get_agent_runtime_client():
    global _agent_runtime_client
    if _agent_runtime_client is None:
        _agent_runtime_client = boto3.client("bedrock-agent-runtime", region_name=config.AWS_REGION)
    return _agent_runtime_client


def _get_bedrock_runtime_client():
    global _bedrock_runtime_client
    if _bedrock_runtime_client is None:
        _bedrock_runtime_client = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
    return _bedrock_runtime_client


def _throttle():
    """Block until at least MIN_SECONDS_BETWEEN_CALLS has passed since the last Bedrock call."""
    global _last_call_time
    elapsed = time.time() - _last_call_time
    wait = config.MIN_SECONDS_BETWEEN_CALLS - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_call_time = time.time()


def _cache_path(cache_key):
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    return os.path.join(config.CACHE_DIR, f"{cache_key}.json")


def _request_hash(payload):
    """Deterministic hash of a JSON-serializable request payload."""
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cache_get(cache_key):
    path = _cache_path(cache_key)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def _cache_set(cache_key, value):
    path = _cache_path(cache_key)
    with open(path, "w") as f:
        json.dump(value, f)


def _call_with_retry(fn):
    """Run fn() with the global throttle and exponential backoff on ThrottlingException."""
    last_error = None
    for attempt in range(config.MAX_RETRIES):
        _throttle()
        try:
            return fn()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            last_error = e
            if error_code == "ThrottlingException":
                delay = config.RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
                time.sleep(delay)
                continue
            raise
    raise last_error


def retrieve(query_text, number_of_results=None):
    """
    Call bedrock-agent-runtime retrieve against the FlavorGap knowledge base.
    Cached on disk keyed by a hash of (knowledge_base_id, query_text, n_results).
    Returns the raw list of retrievalResults (each with content.text, score, metadata).
    """
    n = number_of_results or config.KB_NUMBER_OF_RESULTS
    cache_key = "retrieve_" + _request_hash({
        "kb": config.KNOWLEDGE_BASE_ID,
        "query": query_text,
        "n": n,
    })

    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    def do_call():
        client = _get_agent_runtime_client()
        resp = client.retrieve(
            knowledgeBaseId=config.KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": query_text},
            retrievalConfiguration={"managedSearchConfiguration": {"numberOfResults": n}},
        )
        return resp.get("retrievalResults", [])

    results = _call_with_retry(do_call)
    _cache_set(cache_key, results)
    return results


def converse(model_id, messages, system=None, tool_config=None, max_tokens=2048, temperature=0.0):
    """
    Call bedrock-runtime converse. Cached on disk keyed by a hash of the full request.
    Returns the raw response dict from converse().
    """
    cache_key = "converse_" + _request_hash({
        "model_id": model_id,
        "messages": messages,
        "system": system,
        "tool_config": tool_config,
        "max_tokens": max_tokens,
        "temperature": temperature,
    })

    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    def do_call():
        client = _get_bedrock_runtime_client()
        kwargs = {
            "modelId": model_id,
            "messages": messages,
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        if system:
            kwargs["system"] = system
        if tool_config:
            kwargs["toolConfig"] = tool_config
        return client.converse(**kwargs)

    response = _call_with_retry(do_call)
    _cache_set(cache_key, response)
    return response
