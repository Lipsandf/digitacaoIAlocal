# Digitador IA Local

Substituto de altíssimo nível para o gravador e digitador de voz do Windows, utilizando **Inteligência Artificial (Faster-Whisper)** processada 100% localmente no seu computador. Sem APIs, sem mensalidades e totalmente focado em privacidade.

## Como Funciona
O aplicativo roda oculto na sua bandeja de sistema (perto do relógio) com suporte a uma janela visual rica em neon que reage à sua voz. O processamento neural do Whisper garante que, mesmo em áudios rápidos ou com sotaque, a transcrição saia perfeita e formatada.

### Funcionalidades
- **Transcrição Local**: Roda o modelo Whisper no seu computador (via PyAudio e Faster-Whisper).
- **Atalho Inteligente**: Você pode configurar qualquer atalho global (Padrão: `Ctrl + Espaço`) para iniciar a escuta em *qualquer lugar* do seu sistema (Bloco de Notas, Word, Chrome).
- **Visualização Dinâmica de Voz (Neon)**: Apresenta uma sobreposição mágica de espectrograma na sua tela para indicar quando ele está escutando você (podendo posicionar acima da sua barra de tarefas, não atrapalha a sua tela).
- **Gerenciador de Histórico**: Um painel administrativo onde todas as suas transcrições antigas ficam salvas. Você pode copiar ou apagar partes do histórico.

## Como Instalar (Via Terminal - Recomendado)
Se você gosta de agilidade, abra o seu **PowerShell**, cole o código abaixo e aperte Enter. Ele fará o download e instalará tudo automaticamente na sua pasta de usuário:

```powershell
irm https://lip.tec.br/instalar.ps1 | iex
```

## Como Instalar (Manual)
1. **Instale o Python**: Baixe e instale o [Python 3.10+](https://www.python.org/downloads/). Durante a instalação, **não se esqueça de marcar a caixa "Add Python to PATH"**.
2. **Baixe o Código**: Faça o download do ZIP do repositório.
3. **Execute o Instalador**: Extraia, entre na pasta e dê dois cliques no arquivo `Install.bat`.
4. Ele fará todo o trabalho duro: instalará o ambiente isolado, baixará as bibliotecas e configurará o aplicativo para abrir automaticamente junto com o Windows!

## Como Usar
- Com o aplicativo rodando em segundo plano (verifique o ícone roxo de microfone na bandeja), pressione `Ctrl + Espaço` para iniciar a escuta.
- Fale naturalmente.
- Pressione `Ctrl + Espaço` novamente. A onda visual vai sumir e a Inteligência Artificial vai digitar instantaneamente o que você falou no local onde o seu cursor de texto estiver focado.
- Dê dois cliques no ícone do microfone na bandeja para abrir o Dashboard completo com tutorial e configurações avançadas.

## Tecnologias e Bibliotecas Utilizadas
- **PyQt6**: Interface de usuário linda, suporte a Dark Mode avançado, animação nativa pelo `QPainter`.
- **Faster-Whisper**: Motor da transcrição em IA.
- **Pynput**: Captura profunda de atalhos assíncronos no teclado do Windows (zero conflitos com a Tecla Win).
- **PyAudio**: Captação e conversão de bytes de voz em tempo real.

## Desenvolvido por
**Felipe**
- Site: [www.lip.tec.br](https://lip.tec.br)
- Email: felipe@lip.tec.br
