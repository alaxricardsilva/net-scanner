#!/bin/bash
set -e

echo "=== Iniciando processo de compilação e empacotamento ==="

# Diretórios do projeto
PROJECT_DIR="/home/alaxricard/Documentos/Projetos/net-scanner"
SRC_DIR="$PROJECT_DIR/net_scanner_src"
BUILD_DIR="$PROJECT_DIR/build_env"
PKG_DIR="$PROJECT_DIR/net-scanner_1.0.0_amd64"

# 1. Configurando ambiente virtual temporário
echo "[1/5] Configurando ambiente virtual Python..."
python3 -m venv "$BUILD_DIR"
source "$BUILD_DIR/bin/activate"

# Instalar dependências necessárias
pip install --upgrade pip
pip install PySide6 pyinstaller

# 2. Gerando banco de dados de fabricantes offline (IEEE OUI)
echo "[2/6] Baixando e estruturando base de dados OUI completa..."
python3 -c "
import urllib.request, json, os
try:
    url = 'https://raw.githubusercontent.com/Ringmast4r/OUI-Master-Database/master/LISTS/master_oui.json'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    print('Fazendo download da base unificada (Ringmast4r OUI)...')
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.loads(r.read().decode('utf-8'))
    
    oui_db = {}
    for prefix, info in data.items():
        manufacturer = info.get('manufacturer')
        if manufacturer:
            oui_db[prefix.lower()] = manufacturer
            
    os.makedirs('resources', exist_ok=True)
    with open('resources/oui.json', 'w', encoding='utf-8') as f:
        json.dump(oui_db, f, indent=4, ensure_ascii=False)
    print(f'Sucesso! Banco OUI gerado com {len(oui_db)} fabricantes.')
except Exception as e:
    print('Erro ao gerar base OUI durante o build:', e)
"

# 3. Compilando com PyInstaller (incluindo o oui.json embutido)
echo "[3/6] Compilando aplicativo com PyInstaller..."
cd "$PROJECT_DIR"
pyinstaller --onefile --windowed \
    --add-data "resources/oui.json:." \
    --add-data "resources/net-scanner.svg:." \
    --name=net-scanner "$SRC_DIR/main.py"

# 4. Criando estrutura do pacote Debian
echo "[4/6] Estruturando diretórios do pacote .deb..."
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/net-scanner"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/icons/hicolor/scalable/apps"

# Copiar executável compilado
cp "$PROJECT_DIR/dist/net-scanner" "$PKG_DIR/usr/bin/"
chmod +x "$PKG_DIR/usr/bin/net-scanner"

# Copiar ícone SVG e o oui.json
cp "$PROJECT_DIR/resources/net-scanner.svg" "$PKG_DIR/usr/share/icons/hicolor/scalable/apps/"
cp "$PROJECT_DIR/resources/oui.json" "$PKG_DIR/usr/share/net-scanner/oui.json"

# Criar arquivo control para o Debian
cat <<EOT > "$PKG_DIR/DEBIAN/control"
Package: net-scanner
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Alax Ricard <alaxricard@example.com>
Description: Scanner de rede local e monitoramento de roteador
 Aplicativo gráfico em PySide6 para escanear a rede local,
 renomear dispositivos e monitorar reinicializações do roteador.
EOT

# Criar arquivo de atalho de menu (.desktop)
cat <<EOT > "$PKG_DIR/usr/share/applications/net-scanner.desktop"
[Desktop Entry]
Version=1.0.0
Type=Application
Name=NetScanner
Comment=Varredura e monitor de rede local
Exec=/usr/bin/net-scanner
Icon=net-scanner
Terminal=false
Categories=Utility;Network;
EOT

# 5. Construindo o pacote Debian (.deb) usando Python (portável)
echo "[5/6] Construindo arquivo .deb..."
python3 -c "
import os, tarfile

project_dir = '$PROJECT_DIR'
pkg_dir = '$PKG_DIR'
output_deb = os.path.join(project_dir, 'net-scanner_1.0.0_amd64.deb')

# 1. Criar control.tar.gz
with tarfile.open('control.tar.gz', 'w:gz') as tar:
    tar.add(os.path.join(pkg_dir, 'DEBIAN'), arcname='.')

# 2. Criar data.tar.xz
with tarfile.open('data.tar.xz', 'w:xz') as tar:
    tar.add(os.path.join(pkg_dir, 'usr'), arcname='usr')

# 3. Criar debian-binary
with open('debian-binary', 'wb') as f:
    f.write(b'2.0\n')

# 4. Empacotar formato AR
def write_ar_header(f, name, size):
    # Formato do cabeçalho AR: 16 bytes nome, 12 bytes mod_time, 6 owner, 6 group, 8 mode, 10 size, 2 magic
    header = f'{name:<16}{0:<12}{0:<6}{0:<6}{100644:<8}{size:<10}\x60\x0a'
    f.write(header.encode('ascii'))

with open(output_deb, 'wb') as f:
    f.write(b'!<arch>\n')
    
    # debian-binary
    size = os.path.getsize('debian-binary')
    write_ar_header(f, 'debian-binary', size)
    with open('debian-binary', 'rb') as src:
        f.write(src.read())
    if size % 2 != 0: f.write(b'\n')
    
    # control.tar.gz
    size = os.path.getsize('control.tar.gz')
    write_ar_header(f, 'control.tar.gz', size)
    with open('control.tar.gz', 'rb') as src:
        f.write(src.read())
    if size % 2 != 0: f.write(b'\n')
    
    # data.tar.xz
    size = os.path.getsize('data.tar.xz')
    write_ar_header(f, 'data.tar.xz', size)
    with open('data.tar.xz', 'rb') as src:
        f.write(src.read())
    if size % 2 != 0: f.write(b'\n')

# Limpa temporários
for temp in ['control.tar.gz', 'data.tar.xz', 'debian-binary']:
    if os.path.exists(temp):
        os.remove(temp)
"

# 6. Criando a atalho de Menu Iniciar para o usuário atual (local)
echo "[6/6] Instalando atalho no menu iniciar do usuário atual..."
mkdir -p ~/.local/share/applications/
mkdir -p ~/.local/share/icons/hicolor/scalable/apps/
cp "$PROJECT_DIR/resources/net-scanner.svg" ~/.local/share/icons/hicolor/scalable/apps/
cp "$PKG_DIR/usr/share/applications/net-scanner.desktop" ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/

# Desativa o ambiente virtual
deactivate

echo "=== Processo Concluído! ==="
echo "Arquivo .deb gerado em: $PROJECT_DIR/net-scanner_1.0.0_amd64.deb"
echo "Atalho local instalado no menu iniciar!"
