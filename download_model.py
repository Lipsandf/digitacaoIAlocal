import sys
import os

model_choice = sys.argv[1] if len(sys.argv) > 1 else "small"

print("=" * 60, flush=True)
print(f"  VERIFICANDO / BAIXANDO MODELO DE IA: {model_choice.upper()}", flush=True)
print("  Aguarde o download completo da Inteligencia Artificial...", flush=True)
print("=" * 60, flush=True)

try:
    from faster_whisper.utils import download_model
    # Garante que o tqdm do huggingface imprima barras de progresso
    os.environ["PYTHONUNBUFFERED"] = "1"
    model_path = download_model(model_choice)
    print("\n" + "=" * 60, flush=True)
    print(f"  ✅ MODELO '{model_choice}' 100% PRONTO EM: {model_path}", flush=True)
    print("=" * 60 + "\n", flush=True)
except Exception as e:
    print(f"\n❌ Erro ao baixar modelo: {e}", flush=True)
    sys.exit(1)
