import os
import socket
import struct
import subprocess
import urllib.request
import json
from concurrent.futures import ThreadPoolExecutor

def get_local_ip():
    """Retorna o IP local da interface ativa conectando temporariamente a um IP externo."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Não estabelece conexão real, apenas descobre a interface de saída
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_default_gateway():
    """Obtém o IP do Gateway Padrão (roteador) analisando /proc/net/route."""
    try:
        with open("/proc/net/route", "r") as f:
            for line in f:
                fields = line.strip().split()
                if len(fields) >= 3 and fields[1] == '00000000':
                    # O gateway está em formato hexadecimal (ex: 0101A8C0 -> 192.168.1.1)
                    val = int(fields[2], 16)
                    return socket.inet_ntoa(struct.pack("<L", val))
    except Exception as e:
        print(f"Erro ao obter gateway de /proc/net/route: {e}")
    
    # Fallback usando comando ip route
    try:
        out = subprocess.check_output("ip route | grep default", shell=True, text=True)
        parts = out.split()
        if len(parts) >= 3:
            return parts[2]
    except Exception:
        pass
    return None

def ping_ip(ip):
    """Tenta forçar a resolução ARP enviando pacotes dummy UDP/TCP e pingando."""
    # 1. Envia pacotes UDP dummy (mDNS 5353 e NetBIOS 137) para forçar resolução ARP no kernel
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.05)
        # Envia para mDNS e NetBIOS
        s.sendto(b'', (ip, 5353))
        s.sendto(b'', (ip, 137))
        s.close()
    except Exception:
        pass

    # 2. Tenta uma conexão TCP rápida na porta 80 (HTTP)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.05)
        s.connect_ex((ip, 80))
        s.close()
    except Exception:
        pass

    # 3. Executa o ping ICMP tradicional
    try:
        res = subprocess.run(["ping", "-c", "1", "-W", "1", ip], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
        return ip, res.returncode == 0
    except Exception:
        return ip, False

def scan_network(subnet_prefix):
    """
    Realiza o ping em toda a sub-rede /24 para atualizar a tabela ARP do Linux.
    Exemplo de subnet_prefix: '192.168.1.'
    """
    ips = [f"{subnet_prefix}{i}" for i in range(1, 255)]
    active_ips = []
    
    # Pinga em paralelo (ThreadPoolExecutor) para ser rápido
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(ping_ip, ips)
        for ip, is_up in results:
            if is_up:
                active_ips.append(ip)
                
    return active_ips

def get_arp_table():
    """Lê a tabela ARP do sistema (/proc/net/arp) para associar IP ao MAC."""
    devices = {}
    try:
        with open("/proc/net/arp", "r") as f:
            # Pula o cabeçalho
            next(f)
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    ip = parts[0]
                    mac = parts[3].lower()
                    # Ignora MACs inválidos ou incompletos
                    if mac != '00:00:00:00:00:00' and len(mac) == 17:
                        devices[ip] = mac
    except Exception as e:
        print(f"Erro ao ler /proc/net/arp: {e}")
    return devices

# Cache local de fabricantes para evitar consultas excessivas à API
VENDOR_CACHE = {}

# Diretório de configurações para carregar/salvar o banco de dados OUI completo
CONFIG_DIR = os.path.expanduser("~/.config/net-scanner")
OUI_FILE_PATH = os.path.join(CONFIG_DIR, "oui.json")

# Banco de dados básico de OUI para fallback se estiver sem internet no primeiro uso
LOCAL_OUI_DB = {
    "6c999d": "Amazon Technologies",
    "a88055": "Tuya Smart Inc.",
    "808544": "Intelbras",
    "d8c80c": "Tuya Smart Inc.",
    "508b96": "Huawei Device Co.",
    "c07982": "TCL King Electrical",
    "503d93": "Samsung Electronics",
    "8ef1b1": "Espressif Inc.",
    "a020a6": "Espressif Inc.",
    "240ac4": "Espressif Inc.",
    "3c5ab4": "Google LLC",
    "001c42": "Parallels / Apple",
    "002500": "Apple Inc.",
    "b827eb": "Raspberry Pi Foundation",
    "dca632": "Raspberry Pi Foundation",
    "e45f01": "Raspberry Pi Foundation",
    "982a0a": "Desconhecido",
    "503dd1": "Intel Corporation",
    "e26faf": "Dispositivo Móvel (MAC Rotativo)",
}

def load_oui_database():
    """Tenta carregar o banco de dados OUI completo da IEEE a partir de fontes locais ou remotas."""
    # 1. Tenta carregar da pasta de configurações do usuário
    if os.path.exists(OUI_FILE_PATH):
        try:
            with open(OUI_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # 2. Tenta carregar do diretório do script / instalação
    import sys
    sys_path = os.path.join(os.path.dirname(__file__), "oui.json")
    if os.path.exists(sys_path):
        try:
            with open(sys_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # 3. Tenta carregar da pasta temporária do PyInstaller
    if hasattr(sys, "_MEIPASS"):
        meipass_path = os.path.join(sys._MEIPASS, "oui.json")
        if os.path.exists(meipass_path):
            try:
                with open(meipass_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
            
    # 4. Se não existir localmente, tenta baixar a base oficial da IEEE
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        url = "https://standards-oui.ieee.org/oui/oui.txt"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as response:
            content = response.read().decode('utf-8', errors='ignore')
            
        oui_db = {}
        for line in content.splitlines():
            if "(base 16)" in line:
                parts = line.split("(base 16)")
                if len(parts) == 2:
                    oui_prefix = parts[0].strip().lower()
                    company = parts[1].strip()
                    oui_db[oui_prefix] = company
                    
        # Salva para uso offline subsequente
        with open(OUI_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(oui_db, f, indent=4, ensure_ascii=False)
        return oui_db
    except Exception as e:
        print(f"Erro ao baixar banco OUI da IEEE (usando fallback): {e}")
        
    return LOCAL_OUI_DB

def get_mac_vendor(mac):
    """Obtém o fabricante a partir do MAC, usando banco completo da IEEE/Ringmast4r ou fallback local."""
    mac_clean = mac.replace(":", "").lower()
    oui = mac_clean[:6]
    
    # 1. Verifica no cache temporário de execução
    if oui in VENDOR_CACHE:
        return VENDOR_CACHE[oui]

    # 2. Se for MAC aleatório/rotativo de celular (caractere 2 é 2, 6, a ou e)
    if len(mac_clean) > 1 and mac_clean[1] in ['2', '6', 'a', 'e']:
        vendor = "Dispositivo Privado (MAC Aleatório)"
        VENDOR_CACHE[oui] = vendor
        return vendor

    # 3. Carrega do banco de dados completo e busca por prefixos de tamanho decrescente (MA-S, MA-M, MA-L)
    oui_db = load_oui_database()
    for length in [9, 8, 7, 6]:
        prefix = mac_clean[:length]
        if prefix in oui_db:
            vendor = oui_db[prefix]
            VENDOR_CACHE[oui] = vendor
            return vendor
        
    # 4. Fallback se não encontrar (API online)
    try:
        url = f"https://api.macvendors.com/{oui}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2) as response:
            vendor = response.read().decode('utf-8')
            VENDOR_CACHE[oui] = vendor
            return vendor
    except Exception:
        pass

    return "Desconhecido"

def get_public_ip(ipv6=False):
    """Consulta o IP público (IPv4 ou IPv6). Usa api6.ipify.org para IPv6 real."""
    url = "https://api6.ipify.org?format=json" if ipv6 else "https://api.ipify.org?format=json"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get("ip", "Não disponível")
    except Exception:
        return "Não disponível"

def get_local_ipv6(mac):
    """Obtém os endereços IPv6 (Link-Local e Global/Público) associados ao MAC na rede local."""
    ipv6s = {"link_local": "Não detectado", "global": "Não detectado"}
    try:
        out = subprocess.check_output(["ip", "-6", "neighbor", "show"], text=True)
        for line in out.splitlines():
            parts = line.strip().split()
            if "lladdr" in parts:
                idx = parts.index("lladdr")
                if idx + 1 < len(parts):
                    line_mac = parts[idx + 1].lower()
                    if line_mac == mac.lower():
                        ip = parts[0]
                        if ip.lower().startswith("fe80"):
                            ipv6s["link_local"] = ip
                        else:
                            ipv6s["global"] = ip
    except Exception:
        pass
    return ipv6s

def scan_ports(ip):
    """Realiza uma varredura rápida nas portas comuns de um IP."""
    common_ports = {
        21: "FTP",
        22: "SSH",
        23: "Telnet",
        80: "HTTP",
        443: "HTTPS",
        445: "SMB",
        3389: "RDP",
        8080: "HTTP-ALT"
    }
    open_ports = []
    for port, name in common_ports.items():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3) # Aumentado para 0.3 para maior confiabilidade
        result = s.connect_ex((ip, port))
        if result == 0:
            open_ports.append(f"{port} ({name})")
        s.close()
    return open_ports
