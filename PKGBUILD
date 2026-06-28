# Maintainer: Alax Ricard <alaxricard@example.com>
pkgname=net-scanner
pkgver=1.0.0
pkgrel=2
pkgdesc="Scanner de rede local e monitoramento de reinicialização de roteador"
arch=('any')
url="https://github.com/alaxricardsilva/net-scanner"
license=('GPL')
depends=('python' 'pyside6')
source=('net-scanner.desktop' 'net-scanner.svg')
sha256sums=('SKIP' 'SKIP')

package() {
    # Cria diretórios de destino
    install -d "${pkgdir}/usr/share/${pkgname}"
    install -d "${pkgdir}/usr/bin"
    install -d "${pkgdir}/usr/share/applications"
    install -d "${pkgdir}/usr/share/icons/hicolor/scalable/apps"

    # Instala arquivos de código diretamente da pasta original (startdir)
    install -m644 "${startdir}/net_scanner_src/main.py" "${pkgdir}/usr/share/${pkgname}/main.py"
    install -m644 "${startdir}/net_scanner_src/ui.py" "${pkgdir}/usr/share/${pkgname}/ui.py"
    install -m644 "${startdir}/net_scanner_src/scanner.py" "${pkgdir}/usr/share/${pkgname}/scanner.py"
    install -m644 "${startdir}/net_scanner_src/database.py" "${pkgdir}/usr/share/${pkgname}/database.py"
    install -m644 "${startdir}/resources/oui.json" "${pkgdir}/usr/share/${pkgname}/oui.json"

    # Cria script executável de inicialização
    echo "#!/bin/sh" > "${pkgdir}/usr/bin/net-scanner"
    echo "python3 /usr/share/${pkgname}/main.py \"\$@\"" >> "${pkgdir}/usr/bin/net-scanner"
    chmod +x "${pkgdir}/usr/bin/net-scanner"

    # Instala o atalho de menu e ícone copiados pelo makepkg para o srcdir
    install -m644 "${srcdir}/net-scanner.desktop" "${pkgdir}/usr/share/applications/net-scanner.desktop"
    install -m644 "${srcdir}/net-scanner.svg" "${pkgdir}/usr/share/icons/hicolor/scalable/apps/net-scanner.svg"
}
