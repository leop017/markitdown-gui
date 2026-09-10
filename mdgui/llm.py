"""LLM client helpers: build kwargs and test connectivity."""
import time


def _build_llm_kwargs(enable_llm, llm_base_url, llm_api_key, llm_model, llm_prompt=""):
    kwargs = {}
    if enable_llm and llm_base_url and llm_api_key and llm_model:
        try:
            import openai
            kwargs["llm_client"] = openai.OpenAI(
                base_url=llm_base_url,
                api_key=llm_api_key,
            )
            kwargs["llm_model"] = llm_model
            if llm_prompt:
                kwargs["llm_prompt"] = llm_prompt
        except Exception:
            pass
    return kwargs


def on_test_llm(llm_base_url, llm_api_key, llm_model):
    """Send a minimal chat request to the configured LLM endpoint and return status."""
    if not llm_base_url or not llm_api_key or not llm_model:
        return "❌ 请先填写 Base URL、API Key 和模型名称"
    try:
        import openai
        client = openai.OpenAI(base_url=llm_base_url, api_key=llm_api_key)
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
        )
        elapsed = time.perf_counter() - t0
        choice = resp.choices[0] if resp.choices else None
        return f"✅ 连接成功 · {elapsed:.1f}s · 模型: {llm_model}" + (
            f"\n响应: {choice.message.content.strip()[:80]}" if choice else ""
        )
    except Exception as e:
        return f"❌ 连接失败 · {type(e).__name__}: {e}"
