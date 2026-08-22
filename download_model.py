import sys
import os
import time

# Força suporte a ANSI Colors no Windows PowerShell
os.system("")

model_choice = sys.argv[1] if len(sys.argv) > 1 else "small"

print("\033[96m=" * 65 + "\033[0m", flush=True)
print(f"\033[93m  BAIXANDO MODELO DE INTELIGENCIA ARTIFICIAL: \033[95m{model_choice.upper()}\033[0m", flush=True)
print("\033[90m  Aguarde o download completo dos arquivos de rede neural...\033[0m", flush=True)
print("\033[96m=" * 65 + "\033[0m\n", flush=True)

try:
    import tqdm
    import tqdm.auto
    
    # Customiza o TQDM para ter a barra verde brilhante e estilo Pip
    orig_init = tqdm.tqdm.__init__
    def custom_init(self, *args, **kwargs):
        kwargs["colour"] = "green"
        kwargs["ascii"] = False
        orig_init(self, *args, **kwargs)
    
    tqdm.tqdm.__init__ = custom_init
    if hasattr(tqdm.auto, "tqdm"):
        tqdm.auto.tqdm.__init__ = custom_init

    from faster_whisper.utils import download_model
    os.environ["PYTHONUNBUFFERED"] = "1"
    
    model_path = download_model(model_choice)
    
    print("\n" + "\033[92m=" * 65, flush=True)
    print(f"  ✅ MODELO '{model_choice}' 100% PRONTO EM: {model_path}", flush=True)
    print("=" * 65 + "\033[0m\n", flush=True)
except Exception as e:
    print(f"\n\033[91m❌ Erro ao baixar modelo: {e}\033[0m", flush=True)
    sys.exit(1)
