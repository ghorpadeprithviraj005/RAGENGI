import os, sys, json, traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = BASE_DIR / 'storage' / 'models' / 'llama-2-7b.gguf'

def check_model_file(path):
    if not path.is_file():
        print(f"MODEL FILE MISSING: {path}")
        return False
    size = path.stat().st_size
    print(f"MODEL FILE FOUND: {path} (size {size/1e9:.2f} GB)")
    return True

def try_import_llama_cpp():
    try:
        import llama_cpp
        print('llama_cpp import SUCCESS')
        return True
    except Exception as e:
        print('llama_cpp import FAILED:', e)
        traceback.print_exc()
        return False

def try_faiss():
    try:
        import faiss
        print('faiss import SUCCESS')
        return True
    except Exception as e:
        print('faiss import FAILED:', e)
        traceback.print_exc()
        return False

if __name__ == '__main__':
    ok = True
    ok &= check_model_file(MODEL_PATH)
    ok &= try_import_llama_cpp()
    ok &= try_faiss()
    sys.exit(0 if ok else 1)
