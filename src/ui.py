import datetime
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
    QInputDialog, QListWidget, QTabWidget, QMessageBox, QFrame,
    QDialog
)
from PySide6.QtGui import QFont, QIcon, QColor

import database
import scanner

class ScanThread(QThread):
    finished_signal = Signal(list)

    def __init__(self, subnet_prefix):
        super().__init__()
        self.subnet_prefix = subnet_prefix

    def run(self):
        # Escaneia a rede local pingando todos os IPs
        scanner.scan_network(self.subnet_prefix)
        # Lê a tabela ARP para obter todos os dispositivos e seus MACs
        arp_devices = scanner.get_arp_table()
        
        devices_list = []
        # Carrega nomes personalizados
        custom_names = database.load_devices()
        
        # Cria lista com os resultados da tabela ARP
        for ip, mac in arp_devices.items():
            mac_lower = mac.lower()
            custom_name = custom_names.get(mac_lower, "")
            vendor = scanner.get_mac_vendor(mac)
            devices_list.append({
                "ip": ip,
                "mac": mac,
                "custom_name": custom_name,
                "vendor": vendor,
                "status": "Online"
            })
            
        self.finished_signal.emit(devices_list)

class RouterMonitorThread(QThread):
    status_signal = Signal(bool, str) # (is_online, time_str)
    restart_detected = Signal(str, str, str) # (ip, mac, time_str)

    def __init__(self, gateway_ip):
        super().__init__()
        self.gateway_ip = gateway_ip
        self.is_running = True
        self.last_state = True # True para online, False para offline
        self.offline_count = 0

    def run(self):
        import time
        while self.is_running:
            if not self.gateway_ip:
                # Tenta redescobrir o gateway se não foi detectado
                self.gateway_ip = scanner.get_default_gateway()
                if not self.gateway_ip:
                    time.sleep(5)
                    continue

            # Pega o MAC do gateway
            arp_table = scanner.get_arp_table()
            gateway_mac = arp_table.get(self.gateway_ip, "Desconhecido")

            # Pinga o gateway
            _, success = scanner.ping_ip(self.gateway_ip)
            now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            if not success:
                self.offline_count += 1
                # Se falhar 3 vezes consecutivas, assume que está offline/reiniciando
                if self.offline_count >= 3 and self.last_state:
                    self.last_state = False
                    self.status_signal.emit(False, now_str)
            else:
                self.offline_count = 0
                if not self.last_state:
                    # Estava offline e voltou online -> Indica reinicialização do roteador
                    self.last_state = True
                    self.status_signal.emit(True, now_str)
                    self.restart_detected.emit(self.gateway_ip, gateway_mac, now_str)
                else:
                    self.status_signal.emit(True, now_str)

            time.sleep(4)

    def stop(self):
        self.is_running = False

class PublicIPThread(QThread):
    finished_signal = Signal(str, str) # ipv4, ipv6

    def run(self):
        ipv4 = scanner.get_public_ip(ipv6=False)
        ipv6 = scanner.get_public_ip(ipv6=True)
        self.finished_signal.emit(ipv4, ipv6)

class PortScanThread(QThread):
    finished_signal = Signal(list)

    def __init__(self, ip):
        super().__init__()
        self.ip = ip

    def run(self):
        open_ports = scanner.scan_ports(self.ip)
        self.finished_signal.emit(open_ports)

class DeviceDetailsDialog(QDialog):
    def __init__(self, dev_info, parent=None):
        super().__init__(parent)
        self.dev_info = dev_info
        self.setWindowTitle(f"Detalhes - {dev_info['ip']}")
        self.resize(400, 320)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.setStyleSheet("""
            QDialog {
                background-color: #15161e;
                border: 1px solid #2d3748;
                border-radius: 8px;
            }
            QLabel {
                color: #cbd5e1;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6366f1;
            }
        """)

        title = QLabel(f"Informações Gerais:")
        title.setFont(QFont("Outfit", 12, QFont.Bold))
        layout.addWidget(title)

        name_display = self.dev_info['custom_name'] if self.dev_info['custom_name'] else "Sem Nome Personalizado"
        layout.addWidget(QLabel(f"<b>Nome Personalizado:</b> {name_display}"))
        layout.addWidget(QLabel(f"<b>Endereço IP:</b> {self.dev_info['ip']}"))
        layout.addWidget(QLabel(f"<b>Endereço MAC:</b> {self.dev_info['mac']}"))
        layout.addWidget(QLabel(f"<b>Fabricante:</b> {self.dev_info['vendor']}"))

        # Linha divisória
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #2d3748;")
        layout.addWidget(line)

        ports_title = QLabel("Varredura de Portas Comuns:")
        ports_title.setFont(QFont("Outfit", 11, QFont.Bold))
        layout.addWidget(ports_title)

        self.lbl_ports = QLabel("Realizando varredura em segundo plano...")
        self.lbl_ports.setStyleSheet("color: #94a3b8;")
        layout.addWidget(self.lbl_ports)

        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        # Inicia varredura
        self.thread = PortScanThread(self.dev_info['ip'])
        self.thread.finished_signal.connect(self.on_scan_finished)
        self.thread.start()

    def on_scan_finished(self, open_ports):
        if open_ports:
            self.lbl_ports.setText("Portas Abertas Encontradas:\n" + "\n".join([f"• {p}" for p in open_ports]))
            self.lbl_ports.setStyleSheet("color: #00e676;")
        else:
            self.lbl_ports.setText("Nenhuma porta comum aberta encontrada.")
            self.lbl_ports.setStyleSheet("color: #cbd5e1;")

class NetScannerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NetScanner - Monitor de Rede Local")
        self.resize(850, 600)
        
        # Inicializa banco de dados
        database.init_db()
        
        # Detecta IP local e gateway
        self.local_ip = scanner.get_local_ip()
        self.gateway_ip = scanner.get_default_gateway()
        
        # Calcula prefixo de sub-rede
        if self.local_ip and self.local_ip != '127.0.0.1':
            parts = self.local_ip.split('.')
            self.subnet_prefix = f"{parts[0]}.{parts[1]}.{parts[2]}."
        else:
            self.subnet_prefix = "192.168.1."
            
        self.devices_data = []
        
        self.init_ui()
        self.load_styles()
        
        # Inicia threads
        self.start_ip_lookup()
        self.start_router_monitor()
        self.trigger_scan()

    def init_ui(self):
        # Widget Central
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # Layout Principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Header Info Card
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(15, 15, 15, 15)
        
        # Local Network Info
        local_info_layout = QVBoxLayout()
        self.lbl_local_ip = QLabel(f"Seu IP Local: {self.local_ip}")
        self.lbl_gateway = QLabel(f"Gateway (Roteador): {self.gateway_ip or 'Não detectado'}")
        self.lbl_subnet = QLabel(f"Sub-rede: {self.subnet_prefix}0/24")
        
        for lbl in [self.lbl_local_ip, self.lbl_gateway, self.lbl_subnet]:
            lbl.setFont(QFont("Outfit", 10))
            local_info_layout.addWidget(lbl)
            
        header_layout.addLayout(local_info_layout)
        header_layout.addStretch()

        # Public IP Info
        public_info_layout = QVBoxLayout()
        self.lbl_pub_ipv4 = QLabel("IP Público IPv4: Carregando...")
        self.lbl_pub_ipv6 = QLabel("IP Público IPv6: Carregando...")
        
        for lbl in [self.lbl_pub_ipv4, self.lbl_pub_ipv6]:
            lbl.setFont(QFont("Outfit", 10))
            lbl.setAlignment(Qt.AlignRight)
            public_info_layout.addWidget(lbl)
            
        header_layout.addLayout(public_info_layout)
        main_layout.addWidget(header_card)

        # Tabs Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # TAB 1: Dispositivos da Rede
        tab_devices = QWidget()
        tab_devices_layout = QVBoxLayout(tab_devices)
        tab_devices_layout.setContentsMargins(10, 10, 10, 10)
        
        # Botões de Ação do Scan
        actions_layout = QHBoxLayout()
        self.btn_scan = QPushButton("Escanear Rede")
        self.btn_scan.clicked.connect(self.trigger_scan)
        self.lbl_scan_status = QLabel("Pronto")
        actions_layout.addWidget(self.btn_scan)
        actions_layout.addWidget(self.lbl_scan_status)
        actions_layout.addStretch()
        
        tab_devices_layout.addLayout(actions_layout)

        # Tabela de Dispositivos
        self.table = QTableWidget(0, 5)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["IP Local (Clique p/ detalhes)", "MAC Address", "Nome do Dispositivo", "Fabricante", "Ações"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 120)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellClicked.connect(self.on_cell_clicked)
        
        tab_devices_layout.addWidget(self.table)
        self.tabs.addTab(tab_devices, "Dispositivos Conectados")

        # TAB 2: Monitor do Roteador / Histórico
        tab_router = QWidget()
        tab_router_layout = QVBoxLayout(tab_router)
        tab_router_layout.setContentsMargins(10, 10, 10, 10)

        # Status do Roteador
        self.lbl_router_status = QLabel("Monitorando Roteador...")
        self.lbl_router_status.setObjectName("RouterStatusLabel")
        self.lbl_router_status.setFont(QFont("Outfit", 12, QFont.Bold))
        tab_router_layout.addWidget(self.lbl_router_status)

        # Histórico de Reinicialização
        tab_router_layout.addWidget(QLabel("Histórico de Quedas e Reinicializações:"))
        self.history_list = QListWidget()
        tab_router_layout.addWidget(self.history_list)

        self.tabs.addTab(tab_router, "Histórico do Roteador")
        
        # Carrega o histórico inicial do banco de dados
        self.refresh_history_list()

    def load_styles(self):
        # Folha de estilo QSS para visual Dark moderno premium (Glassmorphism e Neon accents)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0d0e12;
            }
            QWidget {
                color: #e2e8f0;
                font-family: "Outfit", "Inter", "Segoe UI", sans-serif;
            }
            QFrame#HeaderCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a1c24, stop:1 #15161e);
                border: 1px solid #2d3748;
                border-radius: 12px;
            }
            QLabel {
                color: #cbd5e1;
            }
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6366f1;
            }
            QPushButton:pressed {
                background-color: #4338ca;
            }
            QPushButton.rename-btn {
                background-color: #27272a;
                color: #38bdf8;
                border: 1px solid #3f3f46;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QPushButton.rename-btn:hover {
                background-color: #3f3f46;
                color: #7dd3fc;
            }
            QTableWidget {
                background-color: #15161e;
                border: 1px solid #2d3748;
                gridline-color: #2d3748;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #2d3748;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #1a1c24;
                color: #94a3b8;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QTabWidget::pane {
                border: 1px solid #2d3748;
                border-radius: 8px;
                background-color: #15161e;
            }
            QTabBar::tab {
                background-color: #1a1c24;
                color: #94a3b8;
                padding: 10px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #15161e;
                color: #ffffff;
                border-bottom: 2px solid #4f46e5;
            }
            QListWidget {
                background-color: #15161e;
                border: 1px solid #2d3748;
                border-radius: 8px;
                padding: 8px;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #0d0e12;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background-color: #4b5563;
                border-radius: 4px;
            }
        """)

    def start_ip_lookup(self):
        self.ip_thread = PublicIPThread()
        self.ip_thread.finished_signal.connect(self.update_public_ips)
        self.ip_thread.start()

    @Slot(str, str)
    def update_public_ips(self, ipv4, ipv6):
        self.lbl_pub_ipv4.setText(f"IP Público IPv4: {ipv4}")
        self.lbl_pub_ipv6.setText(f"IP Público IPv6: {ipv6}")

    def start_router_monitor(self):
        self.router_thread = RouterMonitorThread(self.gateway_ip)
        self.router_thread.status_signal.connect(self.update_router_status)
        self.router_thread.restart_detected.connect(self.handle_router_restart)
        self.router_thread.start()

    @Slot(bool, str)
    def update_router_status(self, is_online, time_str):
        if is_online:
            self.lbl_router_status.setText(f"Status do Roteador: ONLINE (Último check: {time_str})")
            self.lbl_router_status.setStyleSheet("color: #00e676;")
        else:
            self.lbl_router_status.setText(f"Status do Roteador: INDISPONÍVEL / OFFLINE (Desde: {time_str})")
            self.lbl_router_status.setStyleSheet("color: #ff1744;")

    @Slot(str, str, str)
    def handle_router_restart(self, ip, mac, time_str):
        # Salva o evento no histórico JSON
        database.add_router_restart_log(ip, mac, time_str)
        self.refresh_history_list()
        
        # Mostra um alerta amigável na tela
        QMessageBox.warning(
            self, 
            "Roteador Reiniciado", 
            f"O roteador principal ({ip}) foi reiniciado ou restabeleceu a conexão em {time_str}!"
        )

    def refresh_history_list(self):
        self.history_list.clear()
        history = database.load_router_history()
        for item in history:
            text = f"[{item['timestamp']}] {item['message']}"
            self.history_list.addItem(text)

    def trigger_scan(self):
        self.btn_scan.setEnabled(False)
        self.lbl_scan_status.setText("Realizando varredura na rede...")
        
        self.scan_thread = ScanThread(self.subnet_prefix)
        self.scan_thread.finished_signal.connect(self.display_devices)
        self.scan_thread.start()

    @Slot(list)
    def display_devices(self, devices):
        self.devices_data = devices
        self.table.setRowCount(len(devices))
        
        for row, dev in enumerate(devices):
            # Estiliza o IP como um link clicável
            ip_item = QTableWidgetItem(dev["ip"])
            ip_item.setForeground(QColor("#38bdf8"))
            font = ip_item.font()
            font.setUnderline(True)
            font.setBold(True)
            ip_item.setFont(font)
            ip_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, ip_item)
            
            # Centraliza o MAC
            mac_item = QTableWidgetItem(dev["mac"])
            mac_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, mac_item)
            
            # Nome customizado ou vazio
            display_name = dev["custom_name"] if dev["custom_name"] else "Sem Nome Personalizado"
            name_item = QTableWidgetItem(display_name)
            if not dev["custom_name"]:
                name_item.setForeground(QColor("#64748b"))
            self.table.setItem(row, 2, name_item)
            
            self.table.setItem(row, 3, QTableWidgetItem(dev["vendor"]))
            
            # Botão de Ação para renomear
            btn_rename = QPushButton("Renomear")
            btn_rename.setProperty("mac", dev["mac"])
            btn_rename.setProperty("current_name", dev["custom_name"])
            btn_rename.setProperty("row", row)
            btn_rename.setObjectName("RenameButton")
            btn_rename.setProperty("class", "rename-btn")
            btn_rename.setStyleSheet("""
                background-color: #27272a;
                color: #38bdf8;
                border: 1px solid #3f3f46;
                padding: 4px 8px;
                border-radius: 4px;
            """)
            btn_rename.clicked.connect(self.rename_device_dialog)
            
            # Container para centralizar o botão e evitar distorções
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.addWidget(btn_rename)
            btn_layout.setAlignment(Qt.AlignCenter)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            
            self.table.setCellWidget(row, 4, btn_container)
            
        self.btn_scan.setEnabled(True)
        self.lbl_scan_status.setText(f"Varredura concluída! {len(devices)} dispositivos encontrados.")

    def rename_device_dialog(self):
        button = self.sender()
        mac = button.property("mac")
        current_name = button.property("current_name")
        row = button.property("row")
        
        new_name, ok = QInputDialog.getText(
            self, 
            "Renomear Dispositivo", 
            f"Digite um nome amigável para o MAC {mac}: ", 
            text=current_name
        )
        
        if ok:
            new_name = new_name.strip()
            # Salva no banco
            database.save_device_name(mac, new_name)
            
            # Atualiza a tabela diretamente
            display_text = new_name if new_name else "Sem Nome Personalizado"
            item = QTableWidgetItem(display_text)
            if not new_name:
                item.setForeground(QColor("#64748b"))
            self.table.setItem(row, 2, item)
            
            # Atualiza a propriedade do botão
            button.setProperty("current_name", new_name)

    def on_cell_clicked(self, row, col):
        # Abre o diálogo de detalhes ao clicar na coluna 0 (IP Local)
        if col == 0:
            self.show_device_details(row)

    def show_device_details(self, row):
        if row < len(self.devices_data):
            dev_info = self.devices_data[row]
            dialog = DeviceDetailsDialog(dev_info, self)
            dialog.exec()

    def closeEvent(self, event):
        # Garante o encerramento correto das threads
        if hasattr(self, 'router_thread'):
            self.router_thread.stop()
            self.router_thread.wait()
        event.accept()
