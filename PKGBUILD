# Maintainer: Alax Ricard <suporte@ricardtech.top>
pkgname=net-scanner
pkgver=1.0.0
pkgrel=1
pkgdesc="Scanner de rede local e monitoramento de reinicialização de roteador"
arch=('any')
url="https://github.com/alaxricard/net-scanner"
license=('GPL')
depends=('python' 'pyside6')
source=('net-scanner.desktop' 'net-scanner.svg' 'main.py' 'ui.py' 'scanner.py' 'database.py')
sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP')

package() {
    # Cria diretórios de destino
    install -d "${pkgdir}/usr/share/${pkgname}"
    install -d "${pkgdir}/usr/bin"
    install -d "${pkgdir}/usr/share/applications"
    install -d "${pkgdir}/usr/share/icons/hicolor/scalable/apps"

    # Instala arquivos de código
    install -m644 main.py "${pkgdir}/usr/share/${pkgname}/main.py"
    install -m644 ui.py "${pkgdir}/usr/share/${pkgname}/ui.py"
    install -m644 scanner.py "${pkgdir}/usr/share/${pkgname}/scanner.py"
    install -m644 database.py "${pkgdir}/usr/share/${pkgname}/database.py"

    # Cria script executável de inicialização em /usr/bin/net-scanner
    echo "#!/bin/sh" > "${pkgdir}/usr/bin/net-scanner"
    echo "python3 /usr/share/${pkgname}/main.py \"\$@\"" >> "${pkgdir}/usr/bin/net-scanner"
    chmod +x "${pkgdir}/usr/bin/net-scanner"

    # Instala o atalho de menu e ícone
    install -m644 net-scanner.desktop "${pkgdir}/usr/share/applications/net-scanner.desktop"
    install -m644 net-scanner.svg "${pkgdir}/usr/share/icons/hicolor/scalable/apps/net-scanner.svg"
}
