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
    """Executa um ping rápido em um IP."""
    try:
        # -c 1 (1 pacote), -W 1 (timeout de 1 segundo)
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

def get_mac_vendor(mac):
    """Tenta obter a fabricante do dispositivo a partir do MAC OUI usando um serviço online leve."""
    try:
        oui = mac.replace(":", "")[:6]
        url = f"https://api.macvendors.com/{oui}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.read().decode('utf-8')
    except Exception:
        return "Desconhecido"

def get_public_ip(ipv6=False):
    """Consulta o IP público (IPv4 ou IPv6)."""
    url = "https://api64.ipify.org?format=json" if ipv6 else "https://api.ipify.org?format=json"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get("ip", "Não disponível")
    except Exception:
        return "Não disponível"
