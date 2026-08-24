# 🎙️ Digitador IA (Voz para Texto - Local e Nuvem)

Substituto de alta performance para o digitador por voz nativo do Windows. Oferece suporte **Híbrido (Dual Engine)**:
1. **🖥️ Modo Local (Offline / Privacidade Total)**: Executa redes neurais **Whisper** da OpenAI **100% localmente no seu computador**, sem internet, sem mensalidades e com total privacidade dos seus dados.
2. **⚡ Modo Groq Cloud (Nuvem Instantânea)**: Transcrição ultrarrápida em **menos de 0.3 segundos** utilizando chips LPU da Groq, com **zero consumo de CPU e memória RAM** — perfeito para notebooks e PCs mais modestos!

---

## ✨ Principais Funcionalidades

### ⚡ 1. Sistema Dual Engine (Local + Groq Cloud)
- **Modo IA Local (Offline)**:
  - **🟢 Placas NVIDIA (CUDA)**: Aceleração nativa por GPU com cascateamento automático (`FP16` ➔ `INT8` ➔ `FLOAT32`), garantindo suporte total desde placas mobile (como MX250 e série GTX 10xx) até placas topo de linha da série RTX.
  - **🔴 Placas AMD & Intel (DirectML)**: Aceleração universal via DirectX 12 / ONNX DirectML sem exigir instalação de bibliotecas proprietárias pesadas da NVIDIA.
  - **⚪ Processadores (CPU)**: Algoritmo de **Alocação Inteligente de Núcleos**. O aplicativo analisa quantos núcleos seu processador possui e utiliza quase todos para dar um "pico de velocidade" na transcrição, enquanto reserva núcleos para o Windows não travar a tela.
- **Modo Groq Cloud (Nuvem Instantânea)**:
  - Digite sua Chave de API gratuita da Groq (`gsk_...`) e desfrute de transcrição instantânea com modelos `whisper-large-v3` ou `whisper-large-v3-turbo`.
  - **Monitor de Cota ao Vivo**: Acompanhe o consumo da sua cota diária diretamente pelo painel do aplicativo.
  - **Alternância Rápida em 1 Clique**: Alterne entre o Modo Local e Modo Groq diretamente no ícone ao lado do relógio do Windows (System Tray).

### 🎛️ 2. Escolha de Modelos de IA
- **Local**: IA Leve / Rápida (`small`) ou IA Pesada / Ultra (`large-v3`).
- **Groq Cloud**: `whisper-large-v3` (Máxima precisão) ou `whisper-large-v3-turbo` (Velocidade máxima).

### 🎨 3. Animação Flutuante Arrastável (Overlay Visual)
- **Onda de Áudio Neon**: Ao iniciar a escuta, uma barra visual flutuante reage à sua voz em tempo real.
- **Badge de Motor Ativo**: Identificador visual (`⚡ GROQ` ou `🖥️ LOCAL`) exibido no overlay.
- **Indicador "Transcrevendo..."**: Ao encerrar a gravação, a animação de processamento mantém você informado até o texto ser digitado.
- **Totalmente Arrastável**: Clique com o mouse em qualquer ponto da barra flutuante para movê-la para qualquer canto da sua tela! A nova posição fica salva automaticamente.

### ⌨️ 4. Atalho Global Personalizável
- Pressione o atalho global (Padrão: `Ctrl + Espaço`) em qualquer programa (Word, Bloco de Notas, Navegador, WhatsApp, IDE) para iniciar a gravação.
- Pressione novamente para transcrever e digitar o texto instantaneamente no local onde seu cursor estiver focado.
- Troque o atalho facilmente pelo Painel do aplicativo.

### 📜 5. Gerenciador de Histórico e Tray System
- **Ícone na Bandeja (System Tray)**: O programa roda silenciosamente ao lado do relógio do Windows com menu de alternância rápida de motores.
- **Histórico Completo**: O Dashboard guarda todas as suas transcrições anteriores para você pesquisar, copiar ou apagar quando quiser.

---

## 🚀 Instalação Rápida (Recomendada)

### 📦 Opção 1: Instalador Executável `.exe` (Visual Nativo do Windows)
Baixe o instalador oficial, dê **2 cliques** e siga o assistente passo a passo:
- [📥 **Download do Instalador_DigitadorIA.exe (Servidor Direto)**](https://lip.tec.br/instalador.exe)
- [📦 **Download via GitHub Releases (Versão v0.11)**](https://github.com/Lipsandf/digitacaoIAlocal/releases)
- [📄 **Download do Instalador_DigitadorIA.exe (GitHub Raw)**](https://github.com/Lipsandf/digitacaoIAlocal/raw/main/Instalador_DigitadorIA.exe)

---

### 💻 Opção 2: Instalação via PowerShell
Abra o seu **PowerShell** no Windows, cole o comando abaixo e pressione `Enter`:

```powershell
irm https://lip.tec.br/instalar.ps1 | iex
```

### O que o instalador automatizado faz:
1. **Verificação do Python**: Garante o ambiente estável com **Python 3.11**.
2. **Scanner de GPU**: Identifica sua placa (NVIDIA, AMD ou CPU) e baixa **exclusivamente os pacotes necessários** para a sua máquina.
3. **Criação de Atalhos**: Cria atalho na Área de Trabalho e adiciona a inicialização silenciosa junto com o Windows.
4. **Opção de Desinstalação Cirúrgica**: O instalador possui o menu `[2] Desinstalar` que remove 100% dos modelos de IA, venv, caches e atalhos sem afetar o Python nem os drivers do seu sistema.

---

## 📖 Como Usar no Dia a Dia

1. Certifique-se de que o aplicativo está rodando (procure o ícone de microfone roxo perto do relógio do Windows).
2. Clique no campo de texto onde deseja escrever (ex: no chat do WhatsApp ou no Word).
3. Pressione `Ctrl + Espaço`. Fale a frase desejada enquanto vê a onda visual reagir.
4. Pressione `Ctrl + Espaço` novamente. O texto aparecerá digitado automaticamente no seu cursor!
5. Para alternar entre o modo Local e Groq Cloud, abra o Painel ou clique com o botão direito no ícone do relógio.

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.11**: Linguagem base do projeto.
- **PyQt6**: Interface gráfica avançada em Dark Mode e janela transparente flutuante.
- **Groq Cloud LPU API**: Motor de transcrição em nuvem ultrarrápido (<0.3s).
- **Faster-Whisper / CTranslate2**: Motor neural local de alta velocidade para modelos Whisper da OpenAI.
- **ONNX Runtime DirectML**: Suporte a GPUs AMD e Intel via DirectX 12.
- **PyAudio & SoundFile**: Captura de áudio de alta qualidade e pré-processamento.
- **Pynput**: Captura de atalhos globais no teclado no nível do sistema operacional.

---

## 👤 Desenvolvido por

**Felipe**
- 🌐 Website: [lip.tec.br](https://lip.tec.br)
- ✉️ Contato: [felipe@lip.tec.br](mailto:felipe@lip.tec.br)
- 🐙 GitHub: [Lipsandf/digitacaoIAlocal](https://github.com/Lipsandf/digitacaoIAlocal)
