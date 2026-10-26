import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app.core.config import settings
from llama_cpp import Llama

llm_model_path = os.path.join(settings.BASE_DIR, "storage", "models", "llama-2-7b.gguf")
print("Model path:", llm_model_path, "Exists:", os.path.exists(llm_model_path))

llm = Llama(model_path=llm_model_path, n_ctx=4096, n_gpu_layers=0, verbose=False)
print("type(llm.n_ctx):", type(llm.n_ctx))
if callable(llm.n_ctx):
    print("llm.n_ctx():", llm.n_ctx())
else:
    print("llm.n_ctx:", llm.n_ctx)

# Test tokenize
t1 = llm.tokenize(b"Hello world")
print("Tokens for b'Hello world':", len(t1))
t2 = llm.tokenize("Hello world".encode("utf-8"))
print("Tokens for encoded string:", len(t2))

# Test chat completion
messages = [
    {"role": "system", "content": "You are a helpful assistant. Be concise."},
    {"role": "user", "content": "Say hello in 3 words."}
]
res = llm.create_chat_completion(messages=messages, max_tokens=64)
print("Chat completion:", res["choices"][0]["message"]["content"])
