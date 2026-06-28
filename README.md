# NetScanner - Monitor de Rede Local

Um aplicativo gráfico moderno, rápido e leve construído com **Python 3** e **PySide6 (Qt6)** para varredura e monitoramento de redes locais domésticas ou empresariais.

Projetado especificamente para ser compatível com as principais distribuições Linux, incluindo **Debian, Ubuntu, Mint, Manjaro, BigLinux** e seus derivados.

---

## 🚀 Principais Funcionalidades

1. **Varredura Completa da Rede Local**:
   - Identifica instantaneamente todos os dispositivos conectados à mesma rede local.
   - Exibe o **Endereço IP Local**, **MAC Address** e fabricante da placa de rede (vendor).
   - Realiza varreduras assíncronas ultra-rápidas usando pings paralelos sem travar a interface.

2. **Personalização de Dispositivos**:
   - Permite dar nomes amigáveis (ex: "Meu Celular", "TV da Sala", "Computador do Trabalho") a qualquer dispositivo encontrado.
   - Os nomes editados são persistidos automaticamente e associados ao endereço MAC do aparelho.

3. **Monitoramento do Roteador (Gateway)**:
   - Identifica o roteador principal da rede de forma automática.
   - Monitora em segundo plano a conectividade com o roteador.
   - Registra um histórico persistente e avisa em tempo real caso o roteador sofra uma queda ou seja reiniciado.

4. **Status de IP Público**:
   - Exibe em tempo real o seu IP Público externo tanto para **IPv4** quanto para **IPv6** (caso disponível na sua rede).

---

## 🖥️ Pré-requisitos do Sistema
Para rodar a aplicação a partir do código-fonte, instale o Python 3 e as bibliotecas Qt6:

* **Em derivados do Debian/Ubuntu (APT)**:
  ```bash
  sudo apt install python3 python3-pip python3-pyside6
  ```
* **Em derivados do Arch Linux/Manjaro/BigLinux (Pacman)**:
  ```bash
  sudo pacman -S python python-pip python-pyside6
  ```

---

## 📦 Como Instalar

### 1. No Debian / Ubuntu / Mint / BigLinux antigo (.deb)
Você pode fazer o download do arquivo `.deb` pronto na aba de **Releases** deste repositório e instalá-lo:
```bash
sudo apt install ./net-scanner_1.0.0_amd64.deb
```
Isso adicionará o atalho diretamente ao seu Menu Iniciar.

### 2. No Manjaro / BigLinux / Arch Linux (Nativo)
Como o BigLinux moderno é baseado em Manjaro, você pode instalar nativamente compilando a receita `PKGBUILD` fornecida neste repositório:
```bash
# Clone este repositório
git clone https://github.com/alaxricardsilva/net-scanner.git
cd net-scanner

# Compile e instale nativamente no sistema
makepkg -si
```
Isso instalará todas as dependências oficiais do sistema e colocará o atalho no seu Menu Iniciar.

---

## 🛠️ Como rodar em Modo de Desenvolvimento
Se quiser executar o aplicativo sem instalar no sistema:
```bash
# Entre na pasta do projeto
cd net-scanner

# Crie e ative um ambiente virtual (opcional)
python3 -m venv venv
source venv/bin/activate
pip install PySide6

# Execute
python3 src/main.py
```

---

## 📂 Estrutura de Arquivos do Projeto
* `src/main.py` - Ponto de entrada do aplicativo.
* `src/ui.py` - Layout gráfico moderno, folhas de estilo e processamento assíncrono (threads).
* `src/scanner.py` - Lógica de pings paralelos, tabela ARP e consultas de rede.
* `src/database.py` - Salva os nomes personalizados e histórico em arquivos JSON locais (`~/.config/net-scanner/`).
* `resources/net-scanner.svg` - Ícone vetorial da aplicação.
* `PKGBUILD` - Script de empacotamento oficial para Manjaro/Arch Linux.
* `build_package.sh` - Script de compilação automatizada que gera o executável em PyInstaller e o pacote `.deb`.
