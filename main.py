#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立 LAN-Play / ldn_mitm 房间监控网页（零第三方依赖版）

完全使用 Python 标准库：
- http.server 替代 Flask
- urllib.request 替代 requests
- 所有 UDP 扫描、房间解析逻辑保持不变

启动：
    python Lan-Play房间监控2.0.py
    # 浏览器打开 http://0.0.0.0:5000/

局域网访问：
    HOST=0.0.0.0 python Lan-Play房间监控2.0.py

可选，创建 servers.json 文件（放在本脚本同目录）内容格式为：
[
  {
    "id":"my-server", 
    "name": "我的服务器",
    "host": "example.com",
    "port": 11451,
    "type": "graphql",
    "region": "🇨🇳"
  }
]
注意：servers.json 中的服务器会与内置列表**合并**（同 id 以 json 为准），
      而非替换。环境变量 SERVERS_FILE 指定其他路径时则仅使用该文件。
"""

from __future__ import annotations

import copy
import json
import os
import re
import socket
import struct
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import http.client
import urllib.request
import urllib.error
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

# ══════════════════════════════════════════════════════════════════════════════
# 常量 & 配置（已优化刷新速度相关参数）
# ══════════════════════════════════════════════════════════════════════════════

APP_NAME = "direct-lan-play-monitor"
CACHE_TTL = max(1, int(os.getenv("CACHE_TTL", "12")))
REQUEST_TIMEOUT = max(1.0, float(os.getenv("REQUEST_TIMEOUT", "3"))) # 优化：适当缩短单次请求超时上限
MAX_WORKERS = 32 # 优化：增大并发线程数，让多服务器同时扫描

DEFAULT_SERVERS: list[dict[str, Any]] = [
    {
      "id": "1",
      "name": "tekn0",
      "host": "tekn0.net",
      "port": 11451,
      "type": "graphql",
      "region": "🇺🇸 美国 加利福尼亚 旧金山 DigitalOcean"
    },
    {
      "id": "2",
      "name": "jaxlewis",
      "host": "srv.jaxlewis.top",
      "port": 11451,
      "type": "graphql",
      "region": "🇨🇳 中国 河南 郑州 联通"
    },
    {
      "id": "3",
      "name": "jaysea1",
      "host": "switch.jayseateam.nl",
      "port": 11451,
      "type": "graphql",
      "region": "🇳🇱  荷兰 北荷兰 阿姆斯特丹"
    },
    {
      "id": "4",
      "name": "jaysea2",
      "host": "switch.jayseateam.nl",
      "port": 11453,
      "type": "graphql",
      "region": "🇳🇱 荷兰 北荷兰 阿姆斯特丹"
    },
    {
      "id": "5",
      "name": "lbxmb",
      "host": "lan.lbxmb.fr",
      "port": 11451,
      "type": "graphql",
      "region": "🇫🇷 法国 法兰西岛 巴黎"
    },
    {
      "id": "6",
      "name": "muitxobem",
      "host": "muitxobem-lanplay.ddns.net",
      "port": 11451,
      "type": "graphql",
      "region": "🇺🇸 美国"
    },   
    {
      "id": "7",
      "name": "lp1",
      "host": "lp1.cpalm.org",
      "port": 11451,
      "type": "graphql",
      "region": "🇨🇳 中国 台湾 高雄 中華電信"
    },
    {
      "id": "8",
      "name": "owlet",
      "host": "www.grayowlet.cn",
      "port": 11451,
      "type": "graphql",
      "region": "🇨🇳 中国 内蒙古 锡林郭勒 联通"
    },
    {
      "id": "9",
      "name": "olunira",
      "host": "olunira.fun",
      "port": 11451,
      "type": "graphql",
      "region": "🇨🇳 中国 北京 阿里云"
    },
    {
      "id": "10",
      "name": "mulaosi",
      "host": "ns.mulaosi.cn",
      "port": 11451,
      "type": "graphql",
      "region": "🇨🇳 广东 清远 电信"
    },
    {
      "id": "11",
      "name": "r3ps4j",
      "host": "switch.r3ps4j.nl",
      "port": 11452,
      "type": "graphql",
      "region": "🇨🇳 丹麦 首都 哥本哈根"
    },
    {
      "id": "12",
      "name": "erdbeerbaerlp",
      "host": "erdbeerbaerlp.de",
      "port": 11451,
      "type": "graphql",
      "region": "🇩🇪 德国 萨克森"
    },
    {
      "id": "13",
      "name": "tomodachilife",
      "host": "8.138.237.87",
      "port": 11451,
      "type": "graphql",
      "region": "🇨🇳 中国 广东 广州 阿里云"
    }
]

BUILTIN_GAME_TITLES: dict[str, str] = {
    "FFFFFFFFFFFFFFFF": "未知游戏",
    "01006A800016E000": "任天堂明星大乱斗 特别版",
    "0100152000022000": "马里奥赛车8 豪华版",
    "010029F00FCC4000": "马里奥网球 ACE",
    "010028600EBDA000": "超级马里奥3D世界+狂怒世界",
    "0100DCA0064A6000": "路易吉洋馆3",
    "01006F8002326000": "集合啦！动物森友会",
    "0100F8F0000A2000": "喷射战士2",
    "0100C2500FC20000": "喷射战士3",
    "0100D71004694000": "我的世界",
    "01006FD0080B2000": "胡闹厨房2",
    "01001B300B9BE000": "暗黑破坏神III 永恒收藏版",
    "010060A00B53C000": "武装原型",
    "01000BF0152FA000": "僵尸部队4 死亡战争",
    "010007B010FCC000": "狙击精英4",
    "010018100CD46000": "生化危机5",
    "01002A000CD48000": "生化危机6",
    "0100C8A00B8A2000": "生化危机 启示录1",
    "0100E0B0093F0000": "生化危机 启示录2",
    "01001C700873E000": "噬神者3",
    "01008C8012920000": "消逝的光芒",
    "010078D000F88000": "龙珠 超宇宙2",
    "0100B3C00C6C2000": "龙珠斗士Z",
    "010035F022078000": "龙珠 电光炸裂！ZERO",
    "01008DB008C2C000": "宝可梦 剑",
    "0100ABF008968000": "宝可梦 盾",
    "0100A3D008C5C000": "宝可梦 朱",
    "01008F6008C5E000": "宝可梦 紫",
    "0100F43008C44000": "宝可梦 传说 Z-A",
    "0100770008DD8000": "怪物猎人 XX 终极版",
    "0100559011740000": "怪物猎人崛起 曙光",
    "0100E65002BB8000": "星露谷物语",
    "01007960049A0000": "猎天使魔女2",
    "010092A0172E4000": "双人成行",
    "010051F0207B2000": "朋友收集 梦想生活",
    "01009970122E4000": "无主之地3 终极版",
    "0100CBF022E18000": "NBA 2K26",
    "0100E4700C648000": "刀剑神域 夺命凶弹",
    "0100EF200DA60000": "岛屿生存者",
    "010090400D366000": "火炬之光2",
    "0100C0401921A000": "热血物语SP",
    "01003EB01C2F0000": "百万吨级武藏W",
    "01005ED00CD70000": "破门而入：行动小队",
    "01005FF00C7CC000": "极速俱乐部2",
    "010001300D14A000": "城堡破坏者 重制版",
}

REMOTE_CHINESE_DB_URL = "https://v6.gh-proxy.org/https://raw.githubusercontent.com/jieluojun/lan-play-monitor/refs/heads/main/chinese_db.json"

import ssl

def load_game_titles() -> dict[str, str]:
    """从远程仓库直接读取标题映射内容，并与内置映射合并（同键以远程为准）"""
    merged_titles = dict(BUILTIN_GAME_TITLES)
    print(f"[配置] 正在从远程仓库读取标题映射: {REMOTE_CHINESE_DB_URL}")
    try:
        req = urllib.request.Request(
            REMOTE_CHINESE_DB_URL,
            headers={"User-Agent": f"{APP_NAME}/1.0", "Accept": "application/json"}
        )
        
        # 建立一个不验证 SSL 证书的上下文
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        # 将 context 传入 urlopen
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8-sig"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if k and v:
                        merged_titles[str(k).upper()] = str(v)
                print(f"[配置] 成功加载远程标题映射，共计 {len(data)} 条，合并后总数: {len(merged_titles)}")
            else:
                print("[配置警告] 远程标题映射格式不正确（非 JSON 对象），将仅使用内置映射")
    except Exception as exc:
        print(f"[配置警告] 无法从远程读取标题映射（{exc}），将降级使用内置映射")
    return merged_titles

# 启动时不直接加载远程标题，初始仅使用内置映射
GAME_TITLES = dict(BUILTIN_GAME_TITLES)

GRAPHQL_QUERY = """
query PublicRoomSnapshot {
  serverInfo { online idle }
  room {
    sessionId
    contentId
    hostPlayerName
    nodeCount
    nodeCountMax
    advertiseData
    nodes { playerName }
  }
}
""".strip()

UDP_SCAN_SECONDS = max(0.5, float(os.getenv("UDP_SCAN_SECONDS", "1.2"))) # 优化：适当缩短 UDP 扫描等待时间，提速响应
LDN_PORT = 11452
LDN_MAGIC = bytes.fromhex("00144511")
LDN_SCAN_HEADER = LDN_MAGIC + bytes(8)
SCANNER_VIRTUAL_IP = "10.13.37.0"
LDN_BROADCAST_IP = "10.13.255.255"
MAX_REASSEMBLED_PACKET = 65535

HOST_RE = re.compile(r"^(?:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?|\[[0-9A-Fa-f:]+\])$")
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# ══════════════════════════════════════════════════════════════════════════════
# TTL 缓存
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CacheItem:
    value: Any
    expires_at: float

class TTLCache:
    def __init__(self) -> None:
        self._items: dict[str, CacheItem] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            if item.expires_at <= now:
                self._items.pop(key, None)
                return None
            return copy.deepcopy(item.value)

    def set(self, key: str, value: Any, ttl: int = CACHE_TTL) -> None:
        with self._lock:
            self._items[key] = CacheItem(copy.deepcopy(value), time.monotonic() + ttl)

cache = TTLCache()

# ══════════════════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════════════════

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def int_or_zero(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0

def get_game_info(content_id: str) -> dict[str, str]:
    normalized = str(content_id or "").upper()
    game_name = GAME_TITLES.get(normalized)
    if not game_name:
        game_name = f"未知游戏 ({normalized})" if normalized else "未知游戏"
    return {
        "name": game_name,
        "icon": f"https://tinfoil.media/ti/{normalized or 'FFFFFFFFFFFFFFFF'}/48/48"
    }

# ══════════════════════════════════════════════════════════════════════════════
# HTTP 请求（urllib 替代 requests）
# ══════════════════════════════════════════════════════════════════════════════

class HTTPResponse:
    def __init__(self, raw: http.client.HTTPResponse | None, body: bytes, url: str, error: str | None = None):
        self._raw = raw
        self._body = body
        self.url = url
        self.error = error
        self.status_code = raw.status if raw else 0
        self.reason = raw.reason if raw else (error or "")
        self.headers = {k.lower(): v for k, v in raw.getheaders()} if raw else {}
        self._json: Any = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400 and not self.error

    @property
    def is_redirect(self) -> bool:
        return 300 <= self.status_code < 400

    def raise_for_status(self) -> None:
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code} {self.reason}")

    def json(self) -> Any:
        if self._json is None:
            self._json = json.loads(self._body.decode("utf-8"))
        return self._json

    @property
    def text(self) -> str:
        return self._body.decode("utf-8", errors="replace")

class HTTPClient:
    def __init__(self, user_agent: str = "", default_timeout: float = REQUEST_TIMEOUT):
        self.user_agent = user_agent or f"{APP_NAME}/1.0 (read-only room monitor)"
        self.default_timeout = default_timeout

    def _open(self, method: str, url: str, data: bytes | None = None,
              headers: dict[str, str] | None = None, timeout: float | None = None,
              allow_redirects: bool = True, **_: Any) -> HTTPResponse:
        req_headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, data=data, method=method, headers=req_headers)
        opener = urllib.request.build_opener()
        if not allow_redirects:
            opener = urllib.request.build_opener(urllib.request.HTTPErrorProcessor())
        started = time.monotonic()
        try:
            resp = opener.open(req, timeout=timeout or self.default_timeout)
            body = resp.read()
            return HTTPResponse(resp, body, url)
        except urllib.error.HTTPError as e:
            body = e.read() or b""
            return HTTPResponse(e, body, url, str(e))
        except (urllib.error.URLError, socket.timeout, OSError) as e:
            err_msg = e.reason if hasattr(e, 'reason') else str(e)
            elapsed_ms = max(1, int((time.monotonic() - started) * 1000))
            dummy = HTTPResponse(None, b"", url, err_msg)
            dummy._elapsed_ms = elapsed_ms
            raise RuntimeError(err_msg) from e

    def get(self, url: str, **kw: Any) -> HTTPResponse:
        return self._open("GET", url, **kw)

    def post(self, url: str, json_body: Any = None, **kw: Any) -> HTTPResponse:
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers = kw.pop("headers", {}) or {}
            headers.setdefault("Content-Type", "application/json")
            return self._open("POST", url, data=data, headers=headers, **kw)
        return self._open("POST", url, **kw)

http = HTTPClient()

# ══════════════════════════════════════════════════════════════════════════════
# LDN / LAN-Play UDP 扫描
# ══════════════════════════════════════════════════════════════════════════════

def internet_checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    words = struct.unpack(f"!{len(data) // 2}H", data)
    total = sum(words)
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF

def build_ldn_scan_frame() -> bytes:
    source = socket.inet_aton(SCANNER_VIRTUAL_IP)
    destination = socket.inet_aton(LDN_BROADCAST_IP)
    udp_length = 8 + len(LDN_SCAN_HEADER)
    udp_without_checksum = struct.pack("!HHHH", LDN_PORT, LDN_PORT, udp_length, 0)
    pseudo_header = source + destination + struct.pack("!BBH", 0, socket.IPPROTO_UDP, udp_length)
    udp_checksum = internet_checksum(pseudo_header + udp_without_checksum + LDN_SCAN_HEADER)
    udp_header = struct.pack("!HHHH", LDN_PORT, LDN_PORT, udp_length, udp_checksum)
    total_length = 20 + udp_length
    ip_without_checksum = struct.pack(
        "!BBHHHBBH4s4s",
        0x45, 0, total_length, 0, 0x4000, 64, socket.IPPROTO_UDP, 0,
        source, destination,
    )
    ip_checksum = internet_checksum(ip_without_checksum)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45, 0, total_length, 0, 0x4000, 64, socket.IPPROTO_UDP, ip_checksum,
        source, destination,
    )
    return b"\x01" + ip_header + udp_header + LDN_SCAN_HEADER

LDN_SCAN_FRAME = build_ldn_scan_frame()

def decompress_ldn(data: bytes, expected_size: int) -> bytes:
    if expected_size <= 0 or expected_size > 8192:
        raise ValueError("ldn_mitm 解压长度异常")
    output = bytearray()
    index = 0
    while index < len(data) and len(output) < expected_size:
        value = data[index]; index += 1
        output.append(value)
        if value == 0:
            if index >= len(data):
                raise ValueError("ldn_mitm 压缩数据不完整")
            repeat = data[index]; index += 1
            output.extend(b"\x00" * repeat)
        if len(output) > expected_size:
            raise ValueError("ldn_mitm 解压数据越界")
    if index != len(data) or len(output) != expected_size:
        raise ValueError("ldn_mitm 解压长度不匹配")
    return bytes(output)

def decode_player_name(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()

def parse_network_info(payload: bytes, source_ip: str) -> dict[str, Any]:
    if len(payload) < 0x480:
        raise ValueError("NetworkInfo 长度不足")
    payload = payload[:0x480]
    content_id = payload[0:8][::-1].hex().upper()
    session_id = payload[16:32].hex()
    node_count_max = min(payload[0x66], 8)
    node_count = min(payload[0x67], 8)
    players: list[str] = []
    nodes: list[dict[str, str]] = []
    for index in range(node_count):
        start = 0x68 + 0x40 * index
        node = payload[start : start + 0x40]
        if len(node) < 0x40:
            break
        player_name = decode_player_name(node[0x0C : 0x2C])
        if not player_name:
            player_name = "未命名玩家"
        players.append(player_name)
        nodes.append({"playerName": player_name})
    host = decode_player_name(payload[0x74 : 0x94])
    if not host:
        host = players[0] if players else "未命名玩家"
    elif not players:
        players.append(host)

    advertise_length = min(int.from_bytes(payload[0x26A:0x26C], "little"), 384)
    advertise_data = payload[0x26C : 0x26C + advertise_length].hex()
    return {
        "sessionId": session_id or f"{source_ip}-{content_id}",
        "contentId": content_id,
        "hostPlayerName": host,
        "nodeCount": node_count,
        "nodeCountMax": node_count_max,
        "advertiseData": advertise_data,
        "nodes": nodes,
        "sourceIp": source_ip,
        "players": players,
    }

def parse_ipv4_ldn_response(packet: bytes) -> dict[str, Any] | None:
    if len(packet) < 20 or packet[0] >> 4 != 4:
        return None
    header_length = (packet[0] & 0x0F) * 4
    if header_length < 20 or len(packet) < header_length + 8:
        return None
    total_length = int.from_bytes(packet[2:4], "big")
    if total_length >= header_length + 8:
        packet = packet[: min(total_length, len(packet))]
    if packet[9] != socket.IPPROTO_UDP:
        return None
    source_ip = socket.inet_ntoa(packet[12:16])
    udp = packet[header_length:]
    source_port, destination_port, udp_length, _checksum = struct.unpack("!HHHH", udp[:8])
    if source_port != LDN_PORT or destination_port != LDN_PORT or udp_length < 8:
        return None
    ldn = udp[8 : min(len(udp), udp_length)]
    if len(ldn) < 12 or ldn[:4] != LDN_MAGIC:
        return None
    packet_type = ldn[4]
    compressed = ldn[5] == 1
    body_length = int.from_bytes(ldn[6:8], "little")
    decompressed_length = int.from_bytes(ldn[8:10], "little")
    if body_length > len(ldn) - 12:
        return None
    body = ldn[12 : 12 + body_length]
    if packet_type != 1:
        return None
    if compressed:
        body = decompress_ldn(body, decompressed_length)
    return parse_network_info(body, source_ip)

class FragmentCollector:
    def __init__(self) -> None:
        self.parts: dict[tuple[bytes, int], dict[str, Any]] = {}

    def add(self, frame: bytes) -> bytes | None:
        if len(frame) < 16:
            return None
        source = frame[0:4]
        identification = int.from_bytes(frame[8:10], "big")
        part = frame[10]
        total_parts = frame[11]
        part_length = int.from_bytes(frame[12:14], "little")
        pmtu = int.from_bytes(frame[14:16], "big")
        if not 1 <= total_parts <= 64 or part >= total_parts or pmtu <= 0:
            return None
        if part_length > len(frame) - 16:
            return None
        key = (source, identification)
        item = self.parts.setdefault(key, {"total": total_parts, "pmtu": pmtu, "parts": {}})
        if item["total"] != total_parts or item["pmtu"] != pmtu:
            self.parts.pop(key, None)
            return None
        item["parts"][part] = frame[16 : 16 + part_length]
        if len(item["parts"]) != total_parts:
            return None
        final_size = max(i * pmtu + len(v) for i, v in item["parts"].items())
        if final_size <= 0 or final_size > MAX_REASSEMBLED_PACKET:
            self.parts.pop(key, None)
            return None
        output = bytearray(final_size)
        for i, v in item["parts"].items():
            output[i * pmtu : i * pmtu + len(v)] = v
        self.parts.pop(key, None)
        return bytes(output)

class ActiveRoomScanner:
    def __init__(self, server: dict[str, Any]) -> None:
        self.server = server
        self.sock: socket.socket | None = None
        self.lock = threading.Lock()

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    def ensure_socket(self) -> socket.socket:
        if self.sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.2)
            sock.connect((self.server["host"], self.server["port"]))
            self.sock = sock
        return self.sock

    @staticmethod
    def drain(sock: socket.socket) -> None:
        sock.setblocking(False)
        try:
            while True:
                sock.recv(65535)
        except (BlockingIOError, OSError):
            pass
        finally:
            sock.settimeout(None)

    def scan(self) -> tuple[list[dict[str, Any]], str]:
        with self.lock:
            try:
                sock = self.ensure_socket()
                self.drain(sock)
                collector = FragmentCollector()
                found: dict[str, dict[str, Any]] = {}
                deadline = time.monotonic() + UDP_SCAN_SECONDS
                next_send = 0.0
                while time.monotonic() < deadline:
                    now = time.monotonic()
                    if now >= next_send:
                        sock.send(LDN_SCAN_FRAME)
                        next_send = now + 0.7
                    timeout = min(0.2, max(0.01, deadline - time.monotonic()))
                    sock.settimeout(timeout)
                    try:
                        frame = sock.recv(65535)
                    except socket.timeout:
                        continue
                    if not frame:
                        continue
                    packet: bytes | None = None
                    if frame[0] == 1:
                        packet = frame[1:]
                    elif frame[0] == 3:
                        packet = collector.add(frame[1:])
                    if packet is None:
                        continue
                    try:
                        room = parse_ipv4_ldn_response(packet)
                    except (ValueError, struct.error, OSError):
                        continue
                    if room is not None:
                        key = room.get("sessionId") or f"{room.get('sourceIp')}:{room.get('contentId')}"
                        found[str(key)] = room
                return list(found.values()), ""
            except (OSError, socket.gaierror) as exc:
                self.close()
                return [], str(exc)

# ══════════════════════════════════════════════════════════════════════════════
# 服务器配置
# ══════════════════════════════════════════════════════════════════════════════

def validate_server(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("服务器配置项必须是对象")
    server_id = str(raw.get("id", "")).strip()
    name = str(raw.get("name", server_id)).strip()
    host = str(raw.get("host", "")).strip()
    protocol = str(raw.get("type", "graphql")).strip().lower()
    region = str(raw.get("region", "")).strip()
    try:
        port = int(raw.get("port", 11451))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"服务器 {server_id or host} 的端口无效") from exc
    if not ID_RE.fullmatch(server_id):
        raise ValueError(f"服务器 id 无效：{server_id!r}")
    if not name or len(name) > 100:
        raise ValueError(f"服务器 {server_id} 的名称无效")
    if not HOST_RE.fullmatch(host) or ".." in host:
        raise ValueError(f"服务器 {server_id} 的主机名无效")
    if not 1 <= port <= 65535:
        raise ValueError(f"服务器 {server_id} 的端口无效")
    if protocol not in {"graphql", "rest"}:
        raise ValueError(f"服务器 {server_id} 的 type 仅支持 graphql/rest")
    return {"id": server_id, "name": name, "host": host, "port": port, "type": protocol, "region": region}

def load_servers() -> list[dict[str, Any]]:
    configured = os.getenv("SERVERS_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_file():
            raise RuntimeError(f"指定的服务器配置文件不存在：{path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            print(f"[配置] 已读取 {path}")
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"无法读取服务器配置 {path}：{exc}") from exc
        if not isinstance(raw, list) or not raw:
            raise RuntimeError("服务器配置必须是非空 JSON 数组")
        servers = [validate_server(item) for item in raw]
    else:
        path = Path(__file__).with_name("servers.json")
        merged: dict[str, dict] = {s["id"]: dict(s) for s in DEFAULT_SERVERS}
        if path.is_file():
            try:
                extra = json.loads(path.read_text(encoding="utf-8"))
                print(f"[配置] 已读取 {path}，将与内置服务器合并")
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"无法读取服务器配置 {path}：{exc}") from exc
            if not isinstance(extra, list):
                raise RuntimeError("servers.json 必须是 JSON 数组")
            for item in extra:
                srv = validate_server(item)
                merged[srv["id"]] = srv
        else:
            print(f"[配置] 未找到 {path}，使用内置服务器列表（{len(merged)} 个）")
        servers = list(merged.values())
    ids = [item["id"] for item in servers]
    if len(ids) != len(set(ids)):
        raise RuntimeError("服务器配置中存在重复 id")
    return servers

# 启动时不加载 servers.json，仅使用默认内置列表
SERVERS = list(DEFAULT_SERVERS)
SERVERS_BY_ID = {item["id"]: item for item in SERVERS}
ACTIVE_SCANNERS = {item["id"]: ActiveRoomScanner(item) for item in SERVERS}

def refresh_config_and_servers() -> None:
    """每次刷新/扫描服务器列表时，动态加载远程标题映射和 servers.json"""
    global GAME_TITLES, SERVERS, SERVERS_BY_ID, ACTIVE_SCANNERS
    try:
        GAME_TITLES = load_game_titles()
    except Exception as e:
        print(f"[配置错误] 刷新远程标题映射失败: {e}")

    try:
        new_servers = load_servers()
        SERVERS = new_servers
        SERVERS_BY_ID = {item["id"]: item for item in SERVERS}
        
        current_ids = set(SERVERS_BY_ID.keys())
        for sid in list(ACTIVE_SCANNERS.keys()):
            if sid not in current_ids:
                ACTIVE_SCANNERS[sid].close()
                del ACTIVE_SCANNERS[sid]
        for s in SERVERS:
            if s["id"] not in ACTIVE_SCANNERS:
                ACTIVE_SCANNERS[s["id"]] = ActiveRoomScanner(s)
    except Exception as e:
        print(f"[配置错误] 刷新服务器配置失败: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# 房间数据规范化 & 扫描逻辑
# ══════════════════════════════════════════════════════════════════════════════

def normalize_room(raw: Any, server: dict[str, Any], index: int) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    content_id = str(raw.get("contentId") or raw.get("content_id") or "").upper()
    g_info = get_game_info(content_id)
    nodes = raw.get("nodes") if isinstance(raw.get("nodes"), list) else []
    players: list[str] = []
    for node in nodes:
        if isinstance(node, dict):
            name = str(node.get("playerName") or node.get("player_name") or "").strip()
        else:
            name = str(node).strip()
        if not name:
            name = "未命名玩家"
        players.append(name)
    host = str(raw.get("hostPlayerName") or raw.get("host_player_name") or "").strip()
    if not host:
        host = players[0] if players else "未知玩家"
    elif not players:
        players.append(host)
    node_count = int_or_zero(raw.get("nodeCount", raw.get("node_count", len(players))))
    node_max = int_or_zero(raw.get("nodeCountMax", raw.get("node_count_max", 0)))
    return {
        "id": str(raw.get("sessionId") or raw.get("session_id") or f"{server['id']}-{index}"),
        "server_id": server["id"],
        "server_name": server["name"],
        "server_address": f"{server['host']}:{server['port']}",
        "content_id": content_id,
        "game": g_info["name"],
        "game_icon": g_info["icon"],
        "host": host,
        "node_count": node_count or len(players),
        "node_count_max": node_max,
        "players": players,
    }

def base_result(server: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": server["id"], "name": server["name"], "host": server["host"],
        "port": server["port"], "address": f"{server['host']}:{server['port']}",
        "type": server["type"], "region": server.get("region", ""),
        "status": "offline", "online": 0, "idle": 0, "active": 0,
        "room_count": 0, "rooms": [], "latency_ms": None, "error": "",
        "scanner_error": "", "detection": "active-udp-scan",
        "checked_at": utc_now(),
    }

def scan_graphql(server: dict[str, Any]) -> dict[str, Any]:
    result = base_result(server)
    url = f"http://{server['host']}:{server['port']}/"
    started = time.monotonic()
    try:
        response = http.post(url, json_body={"query": GRAPHQL_QUERY}, timeout=REQUEST_TIMEOUT, allow_redirects=False)
        elapsed_ms = max(1, int((time.monotonic() - started) * 1000))
        result["latency_ms"] = elapsed_ms
        if response.is_redirect:
            raise RuntimeError("服务器返回意外重定向")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("响应不是 JSON 对象")
        if payload.get("errors"):
            first = payload["errors"][0] if isinstance(payload["errors"], list) else payload["errors"]
            message = first.get("message") if isinstance(first, dict) else str(first)
            raise RuntimeError(f"GraphQL：{message}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("GraphQL 缺少 data")
        info = data.get("serverInfo") if isinstance(data.get("serverInfo"), dict) else {}
        online = int_or_zero(info.get("online"))
        idle = int_or_zero(info.get("idle"))
        raw_rooms = data.get("room") if isinstance(data.get("room"), list) else []
        rooms = [normalize_room(item, server, i + 1) for i, item in enumerate(raw_rooms)]
        result.update({"status": "online", "online": online, "idle": idle,
                       "active": max(0, online - idle), "room_count": len(rooms), "rooms": rooms})
    except Exception as exc:
        if result["latency_ms"] is None:
            result["latency_ms"] = max(1, int((time.monotonic() - started) * 1000))
        result["error"] = str(exc)
    return result

def scan_rest(server: dict[str, Any]) -> dict[str, Any]:
    result = base_result(server)
    url = f"http://{server['host']}:{server['port']}/info"
    started = time.monotonic()
    try:
        response = http.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=False)
        elapsed_ms = max(1, int((time.monotonic() - started) * 1000))
        result["latency_ms"] = elapsed_ms
        if response.is_redirect:
            raise RuntimeError("服务器返回意外重定向")
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("响应不是 JSON 对象")
        online = int_or_zero(data.get("online", data.get("clientCount", 0)))
        idle = int_or_zero(data.get("idle", 0))
        raw_rooms = data.get("rooms") if isinstance(data.get("rooms"), list) else []
        rooms = [normalize_room(item, server, i + 1) for i, item in enumerate(raw_rooms)]
        result.update({"status": "online", "online": online, "idle": idle,
                       "active": max(0, online - idle), "room_count": len(rooms), "rooms": rooms})
    except Exception as exc:
        if result["latency_ms"] is None:
            result["latency_ms"] = max(1, int((time.monotonic() - started) * 1000))
        result["error"] = str(exc)
    return result

def scan_server(server: dict[str, Any], force: bool = False) -> tuple[dict[str, Any], bool]:
    key = f"scan:{server['id']}"
    if not force:
        cached = cache.get(key)
        if cached is not None:
            return cached, True
    result = scan_graphql(server) if server["type"] == "graphql" else scan_rest(server)
    active_scanner = ACTIVE_SCANNERS.get(server["id"])
    active_raw_rooms, scanner_error = active_scanner.scan() if active_scanner else ([], "Scanner not found")
    active_rooms = [normalize_room(item, server, i + 1) for i, item in enumerate(active_raw_rooms)]
    merged: dict[str, dict[str, Any]] = {}
    for room in [*result.get("rooms", []), *active_rooms]:
        room_id = str(room.get("id") or f"{room.get('server_id')}:{room.get('host')}:{room.get('content_id')}")
        merged[room_id] = room
    rooms = list(merged.values())
    result["rooms"] = rooms
    result["room_count"] = len(rooms)
    result["scanner_error"] = scanner_error
    result["detection"] = "active-udp-scan+monitor-api"
    if rooms and result.get("status") != "online":
        result["status"] = "online"
        result["online"] = max(int_or_zero(result.get("online")), sum(max(1, r["node_count"]) for r in rooms))
        result["active"] = max(0, result["online"] - int_or_zero(result.get("idle")))
        result["error"] = ""
    if result.get("latency_ms") is None:
        result["latency_ms"] = -1
    cache.set(key, result)
    return result, False

def scan_all(force: bool = False) -> tuple[list[dict[str, Any]], bool]:
    # 每次刷新服务器列表时加载最新配置
    refresh_config_and_servers()
    
    results: dict[str, dict[str, Any]] = {}
    all_cached = True
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(SERVERS))) as executor:
        futures = {executor.submit(scan_server, s, force): s["id"] for s in SERVERS}
        for future in as_completed(futures):
            sid = futures[future]
            try:
                result, hit = future.result()
                results[sid] = result
                all_cached = all_cached and hit
            except Exception as exc:
                fallback = base_result(SERVERS_BY_ID[sid])
                fallback["error"] = str(exc)
                fallback["latency_ms"] = -1
                results[sid] = fallback
                all_cached = False
    return [results[item["id"]] for item in SERVERS], all_cached

# ══════════════════════════════════════════════════════════════════════════════
# 参数解析 & 响应辅助
# ══════════════════════════════════════════════════════════════════════════════

def parse_query(query_string: str) -> dict[str, str]:
    if not query_string:
        return {}
    parsed = urllib.parse.parse_qs(query_string, keep_blank_values=True)
    return {k: v[0] for k, v in parsed.items()}

def wants_refresh(query: dict[str, str]) -> bool:
    return query.get("refresh", "0").strip().lower() in {"1", "true", "yes"}

def bounded_int(query: dict[str, str], name: str, default: int, minimum: int, maximum: int) -> int:
    raw = query.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"参数 {name} 必须是整数") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"参数 {name} 必须在 {minimum} 到 {maximum} 之间")
    return value

def make_json_response(data: dict[str, Any], cache_hit: bool = False,
                       status: int = 200) -> tuple[bytes, dict[str, str], int]:
    body = json.dumps(data, ensure_ascii=False, sort_keys=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-Cache": "HIT" if cache_hit else "MISS",
        "Cache-Control": f"public, max-age={CACHE_TTL}",
        "Access-Control-Allow-Origin": "*",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    }
    return body, headers, status

# ══════════════════════════════════════════════════════════════════════════════
# 前端页面
# ══════════════════════════════════════════════════════════════════════════════

PAGE_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#dff3ff" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#0f1923" media="(prefers-color-scheme: dark)">
  <title>Direct LDN</title>
  <style>
    :root{
      --bg:#dff3ff;--card:rgba(255,255,255,.82);--white:#fff;--ink:#0c3154;--muted:#50728d;
      --blue:#d8effd;--cyan:#19c8ae;--red:#dc3048;--line:rgba(55,130,175,.12);
      --shadow:0 16px 44px rgba(65,136,178,.11);
      --green:#178a78;--green-bg:#dcf6f1;--orange:#e8820c;
      --radius-lg:28px;--radius-md:20px;--radius-sm:14px;
      --font:"Segoe UI","PingFang SC","Microsoft YaHei",system-ui,sans-serif;
      --transition:all .25s cubic-bezier(.4,0,.2,1);
    }
    @media (prefers-color-scheme: dark){
      :root{
        --bg:#0f1923;--card:rgba(22,34,46,.85);--white:#16222e;--ink:#e0eef8;
        --muted:#7a9bb5;--blue:#1a3344;--cyan:#2ee6c8;--red:#ff5a6e;
        --line:rgba(255,255,255,.06);--shadow:0 16px 44px rgba(0,0,0,.4);
        --green:#3dd9b8;--green-bg:rgba(61,217,184,.12);--orange:#ffb347;
      }
    }
    *,*::before,*::after{box-sizing:border-box}
    html{background:var(--bg);scroll-behavior:smooth}
    body{
      margin:0;min-height:100vh;color:var(--ink);font-family:var(--font);
      background:radial-gradient(circle at 8% 6%,rgba(255,255,255,.9),transparent 25%),
                 radial-gradient(circle at 92% 42%,rgba(176,224,252,.55),transparent 28%),
                 linear-gradient(180deg,#e4f5ff,#d9f0ff);
      transition:background .4s ease,color .4s ease;
      -webkit-tap-highlight-color:transparent;overflow-x:hidden;
    }
    @media (prefers-color-scheme: dark){
      body{background:radial-gradient(circle at 8% 6%,rgba(30,55,75,.6),transparent 25%),
                        radial-gradient(circle at 92% 42%,rgba(20,45,65,.5),transparent 28%),
                        linear-gradient(180deg,#0f1923,#0a1218)}
    }
    a{color:inherit;text-decoration:none}
    button{font:inherit}
    ::selection{background:var(--cyan);color:#fff}

    .page{width:min(1100px,calc(100%-32px));margin:auto;padding:24px 0 24px;animation:fadeIn .5s ease}
    @keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
    .glass{border:1px solid rgba(255,255,255,.8);background:var(--card);box-shadow:var(--shadow);backdrop-filter:blur(15px);-webkit-backdrop-filter:blur(15px);transition:var(--transition)}
    @media (prefers-color-scheme: dark){.glass{border-color:rgba(255,255,255,.05)}}

    .hero{margin-top:0;min-height:68px;border-radius:var(--radius-lg);padding:12px 24px;display:flex;align-items:center;justify-content:space-between;gap:16px;position:sticky;top:12px;z-index:100}
    .brand{display:flex;align-items:center;gap:12px;min-width:0;flex-shrink:0}
    .logo{width:46px;height:46px;border-radius:14px;display:grid;place-items:center;background:linear-gradient(145deg,#fff970,#ffd626);box-shadow:inset 0 0 0 2px rgba(255,255,255,.7),0 4px 12px rgba(255,200,40,.25);font-size:20px;animation:pulse 3s ease-in-out infinite;flex-shrink:0}
    @keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.05)}}
    .brand strong{display:block;font:italic 700 22px Georgia,serif;letter-spacing:.3px}
    .brand small{display:block;color:var(--muted);font-size:11.5px;margin-top:1px}
    .dot{width:10px;height:10px;border-radius:50%;background:var(--cyan);box-shadow:0 0 0 6px rgba(25,200,174,.13);animation:pulse-dot 2s ease-in-out infinite}
    @keyframes pulse-dot{0%,100%{box-shadow:0 0 0 6px rgba(25,200,174,.13)}50%{box-shadow:0 0 0 10px rgba(25,200,174,.06)}}
    .scan{display:flex;align-items:center;gap:10px;color:var(--muted);font-weight:700;font-size:13px;flex-shrink:0}
    .refresh{border:0;border-radius:12px;padding:10px 18px;background:#e1f1fa;color:var(--ink);font-weight:750;cursor:pointer;font-size:13.5px;transition:var(--transition);display:inline-flex;align-items:center;gap:6px}
    .refresh:hover{background:#cce9f9;transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.08)}
    .refresh:active{transform:translateY(0)}
    .refresh.loading{pointer-events:none;opacity:.7}
    .refresh .spinner{width:14px;height:14px;border:2.5px solid currentColor;border-top-color:transparent;border-radius:50%;animation:spin .6s linear infinite;display:none}
    .refresh.loading .spinner{display:block}
    .refresh.loading .refresh-text::before{content:'刷新中'}
    .refresh.loading .refresh-text span{display:none}
    @keyframes spin{to{transform:rotate(360deg)}}

    .overview{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:18px}
    .ov-card{padding:18px 16px;background:var(--white);border-radius:var(--radius-md);box-shadow:0 6px 20px rgba(82,142,178,.06);text-align:center;transition:var(--transition)}
    .ov-card:hover{transform:translateY(-2px);box-shadow:0 10px 28px rgba(82,142,178,.1)}
    .ov-card span{display:block;color:var(--muted);font-size:12px;font-weight:600;margin-bottom:3px}
    .ov-card b{font-size:26px;font-weight:900}
    .ov-card.online b{color:#2b8a6f}.ov-card.idle b{color:#b8860b}.ov-card.rooms b{color:#1a73c0}.ov-card.servers b{color:#6f42c1}
    @media (prefers-color-scheme: dark){.ov-card.online b{color:#3dd9b8}.ov-card.idle b{color:#ffb347}.ov-card.rooms b{color:#7ab8ff}.ov-card.servers b{color:#c4a7ff}}

    .server-list{margin-top:18px;display:grid;gap:12px;contain:layout style}
    .server-group{
      background:var(--white);border-radius:var(--radius-md);box-shadow:0 6px 20px rgba(82,142,178,.06);
      overflow:hidden;will-change:transform;contain:layout style paint;
    }
    .server-group:hover{box-shadow:0 10px 30px rgba(82,142,178,.1)}

    .server-head{
      display:flex;align-items:center;gap:14px;padding:18px 22px;cursor:pointer;
      user-select:none;position:relative;-webkit-tap-highlight-color:transparent;
      touch-action:manipulation;
    }
    .server-head:hover{background:rgba(125,175,210,.06)}
    @media (prefers-color-scheme: dark){.server-head:hover{background:rgba(255,255,255,.03)}}

    .server-status-dot{width:12px;height:12px;border-radius:50%;flex-shrink:0;position:relative}
    .server-status-dot.online{background:#19c8ae;box-shadow:0 0 0 4px rgba(25,200,174,.15)}
    .server-status-dot.offline{background:#dc3048;box-shadow:0 0 0 4px rgba(220,48,72,.12)}
    .server-status-dot.checking{background:#e8820c;box-shadow:0 0 0 4px rgba(232,130,12,.12);animation:pulse-dot 1.5s ease-in-out infinite}

    .server-info{flex:1;min-width:0}
    .server-name{font-size:16px;font-weight:800;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
    .server-name .region{font-size:11px;font-weight:600;padding:2px 8px;border-radius:999px;background:rgba(125,175,210,.12);color:var(--muted)}
    .server-detail{font-size:12.5px;color:var(--muted);margin-top:3px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
    .addr-text{cursor:pointer;user-select:all;transition:color .2s,background .2s;padding:1px 6px;border-radius:6px}
    .addr-text:hover{color:var(--ink);background:rgba(125,175,210,.12)}
    .addr-text:active{background:rgba(25,200,174,.15)}
    .addr-copied{color:#19c8ae!important;background:rgba(25,200,174,.12)!important}

    .server-stats{
      display:grid;
      grid-template-columns:repeat(4, 1fr);
      width:280px;
      gap:8px;
      align-items:start;
      flex-shrink:0;
    }
    .stat-item{
      display:flex;
      flex-direction:column;
      align-items:center;
      text-align:center;
      min-width:0;
    }
    .stat-item span{
      display:block;
      font-size:10.5px;
      color:var(--muted);
      font-weight:600;
      margin-bottom:2px;
      line-height:1.2;
    }
    .stat-item b{
      font-size:18px;
      font-weight:900;
      line-height:22px;
      height:22px;
      display:flex;
      align-items:center;
      justify-content:center;
    }
    .stat-item.online b{color:#2b8a6f} .stat-item.idle b{color:#b8860b} .stat-item.rooms b{color:#1a73c0}
    @media (prefers-color-scheme: dark){.stat-item.online b{color:#3dd9b8}.stat-item.idle b{color:#ffb347}.stat-item.rooms b{color:#7ab8ff}}

    .stat-item.latency b{
      font-size:15px;
      line-height:22px;
      height:22px;
    }
    .latency-badge{display:flex;align-items:center;justify-content:center;background:transparent!important;}
    .latency-badge.fast{color:#17776b;}
    .latency-badge.normal{color:var(--muted);}
    .latency-badge.slow{color:#a52639;}
    .latency-badge.error{color:var(--muted);font-weight:900;}
    @media (prefers-color-scheme: dark){
      .latency-badge.fast{color:#3dd9b8;}
      .latency-badge.normal{color:var(--muted);}
      .latency-badge.slow{color:#ff5a6e;}
      .latency-badge.error{color:var(--muted);}
    }

    .server-body{
      display:grid;grid-template-rows:0fr;overflow:hidden;
      transition:grid-template-rows .3s cubic-bezier(.4,0,.2,1);
    }
    .server-body > .body-inner{overflow:hidden;min-height:0}
    .server-group.open .server-body{grid-template-rows:1fr}
    .server-group.open .server-body > .body-inner{padding:0 22px 20px}

    .server-error{padding:14px 18px;border-radius:14px;background:#fff0f2;color:#a52639;font-size:13px;font-weight:600;margin-top:4px;display:flex;align-items:center;gap:8px}
    @media (prefers-color-scheme: dark){.server-error{background:rgba(255,90,110,.08);color:#ff5a6e}}

    .room-list{display:grid;gap:10px;margin-top:8px}
    .room-item{
      padding:16px 18px;border-radius:16px;background:var(--card);
      box-shadow:0 4px 14px rgba(82,142,178,.05);transition:transform .15s ease,box-shadow .15s ease;
      contain:layout style paint;
    }
    .room-item:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(82,142,178,.09)}
    .room-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
    .room-host{font-size:16px;font-weight:800;display:flex;align-items:center;gap:8px}
    .room-host::before{content:'🏠';font-size:15px}
    .room-host-icon{width:22px;height:22px;border-radius:4px;object-fit:cover;flex-shrink:0;vertical-align:middle}
    .room-game{font-size:12.5px;padding:4px 12px;border-radius:999px;background:#e9f5fb;color:#326887;font-weight:700;white-space:nowrap}
    @media (prefers-color-scheme: dark){.room-game{background:rgba(97,194,233,.12);color:#7dd3fc}}
    .room-meta{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px;font-size:13px;color:#376482;font-weight:600}
    .room-meta .green{color:var(--green);font-weight:750}
    .room-meta .red{color:var(--red);font-weight:800}
    .room-players{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px}
    .room-players .player{padding:3px 10px;border-radius:999px;background:var(--green-bg);color:#17776b;font-size:11.5px;font-weight:600}
    @media (prefers-color-scheme: dark){.room-players .player{background:rgba(61,217,184,.12);color:#3dd9b8}}

    .no-rooms{padding:20px;text-align:center;color:var(--muted);font-size:13px;background:rgba(125,175,210,.04);border-radius:14px;margin-top:8px}
    .no-rooms-match{padding:14px 18px;text-align:center;color:var(--muted);font-size:12.5px;background:rgba(125,175,210,.03);border-radius:12px;margin-top:6px}

    .skeleton{height:60px;border-radius:14px;background:linear-gradient(100deg,#f0f6fa 20%,#e2eef5 38%,#f0f6fa 56%);background-size:300% 100%;animation:shine 1.4s infinite;margin-top:8px}
    @media (prefers-color-scheme: dark){.skeleton{background:linear-gradient(100deg,#1a2530 20%,#243240 38%,#1a2530 56%);background-size:300% 100%}}
    @keyframes shine{to{background-position-x:-100%}}

    .filters{display:flex;gap:8px;overflow-x:auto;padding:14px 0 4px;scrollbar-width:none}
    .filters::-webkit-scrollbar{display:none}
    .filter-tab{flex:0 0 auto;border:0;border-radius:999px;padding:9px 18px;background:#e8f3f9;color:var(--ink);font-weight:700;cursor:pointer;font-size:13px;transition:var(--transition);white-space:nowrap}
    .filter-tab:hover{background:#d8eaf3}
    .filter-tab.active{background:#cde9fa;color:#0c5d91;font-weight:800;box-shadow:0 2px 8px rgba(97,194,233,.25)}
    @media (prefers-color-scheme: dark){.filter-tab{background:rgba(255,255,255,.06)}.filter-tab:hover{background:rgba(255,255,255,.10)}.filter-tab.active{background:rgba(97,194,233,.20);color:#7dd3fc}}

    footer{text-align:center;padding:24px 16px 8px;color:#55758c;font-size:12px;line-height:1.9;margin-top:12px}
    @media (prefers-color-scheme: dark){footer{color:var(--muted)}}

    @media (max-width:900px){
      .page{width:calc(100% - 20px);padding-top:14px}
      .hero{border-radius:20px;padding:10px 14px;gap:10px}
      .brand{min-width:auto;flex-shrink:0}.brand strong{font-size:18px}
      .scan{font-size:12px;flex-shrink:0}
      .overview{grid-template-columns:repeat(4,1fr);gap:8px}
      .ov-card{padding:14px 8px}
      .ov-card b{font-size:22px}
      .server-head{padding:14px 16px;gap:10px}
      .server-stats{width:250px;gap:6px}
      .server-name{font-size:14.5px}
    }

    @media (max-width:600px){
      .page{width:calc(100% - 14px);padding:10px 0 16px}
      .hero{border-radius:16px;padding:8px 10px;gap:6px;position:sticky;top:6px}
      .brand{flex-shrink:0}
      .brand strong{font-size:15px}
      .brand small{display:none}
      .logo{width:34px;height:34px;border-radius:10px;font-size:16px}
      .scan{margin-top:0;font-size:11.5px;flex-shrink:0}
      .scan .refresh{flex:0 0 auto;padding:7px 12px;font-size:12px}
      .overview{grid-template-columns:repeat(2,1fr);gap:8px;margin-top:14px}
      .ov-card{padding:12px 8px;border-radius:14px}
      .ov-card b{font-size:20px}
      .ov-card span{font-size:11px}
      .server-list{margin-top:14px;gap:10px}
      .server-head{padding:12px 14px;gap:8px;flex-wrap:nowrap}
      .server-status-dot{width:10px;height:10px}
      .server-name{font-size:13.5px;gap:5px}
      .server-name .region{font-size:10px;padding:1px 6px}
      .server-detail{font-size:11px;gap:6px;margin-top:2px}
      .server-stats{width:210px;gap:4px}
      .server-stats .stat-item span{font-size:9.5px}
      .server-stats .stat-item b{font-size:15px;height:18px;line-height:18px}
      .stat-item.latency b{font-size:12px;height:18px;line-height:18px}
      .server-group.open .server-body{padding:0 14px 14px}
      .room-list{gap:8px}
      .room-item{padding:14px;border-radius:14px}
      .room-host{font-size:14.5px}
      .room-game{font-size:11px;padding:3px 10px}
      .room-meta{font-size:12px;gap:6px}
      .room-players{gap:4px}
      .room-players .player{padding:2px 8px;font-size:10.5px}
      .filters{padding:10px 0 2px}
      .filter-tab{padding:7px 14px;font-size:12px}
    }

    @media (max-width:380px){
      .brand small{display:none}
      .brand strong{font-size:14px}
      .logo{width:30px;height:30px;font-size:14px}
      .scan{font-size:10.5px;gap:6px}
      .scan .refresh{padding:6px 10px;font-size:11px}
      .server-detail .addr-text{display:none}
      .server-stats{grid-template-columns:repeat(3,1fr);width:150px;}
      .server-stats .stat-item.idle{display:none}
    }

    @media (prefers-reduced-motion:reduce){
      *,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important}
    }
  </style>
</head>
<body>
<div class="page">
  <section class="hero glass">
    <a class="brand" href="/"><span class="logo">🎮</span><span><strong>Direct LDN</strong><small>独立 LAN-Play 监控</small></span></a>
    <div class="scan">
      <i class="dot"></i><span>实时扫描</span>
      <button id="refreshBtn" class="refresh">
        <span class="spinner"></span>
        <span class="refresh-text"><span>刷新</span></span>
      </button>
    </div>
  </section>

  <div class="overview" id="overview">
    <div class="ov-card servers"><span>在线服务器</span><b id="ovServers">—</b></div>
    <div class="ov-card online"><span>总在线</span><b id="ovOnline">—</b></div>
    <div class="ov-card idle"><span>空闲</span><b id="ovIdle">—</b></div>
    <div class="ov-card rooms"><span>总房间</span><b id="ovRooms">—</b></div>
  </div>

  <div class="filters" id="filters"></div>

  <div class="server-list" id="serverList">
    <div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>
  </div>

</div>

<script>
(() => {
  'use strict';
  const state = { servers:[], rooms:[], game:'all', expanded:new Set(), loading:false, firstLoad:true, firstExpand:true };
  const $ = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  async function getJSON(url){
    const r = await fetch(url, { headers:{ Accept:'application/json' }, cache:'no-store' });
    const d = await r.json().catch(() => ({}));
    if(!r.ok || d.ok === false) throw new Error(d.error || `请求失败 (${r.status})`);
    return d;
  }

  const statusDot = s => s==='online' ? 'online' : s==='checking' ? 'checking' : 'offline';

  function copyAddr(text, el){
    const done = () => {
      el.classList.add('addr-copied');
      const original = el.textContent;
      el.textContent = '✅ 已复制 ' + text;
      setTimeout(() => {
        el.classList.remove('addr-copied');
        el.textContent = original;
      }, 1500);
    };
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
    } else {
      fallbackCopy(text, done);
    }
  }
  function fallbackCopy(text, cb){
    const ta = document.createElement('textarea');
    ta.value = text; ta.style.position='fixed'; ta.style.left='-9999px';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } catch(e){}
    document.body.removeChild(ta);
    cb && cb();
  }

  function latencyHTML(s){
    if(s.status !== 'online' || s.error || s.latency_ms == null || s.latency_ms < 0){
      return '<b class="latency-badge error">-</b>';
    }
    const lat = s.latency_ms;
    if(lat <= 300){
      return `<b class="latency-badge fast">${lat}ms</b>`;
    } else {
      return `<b class="latency-badge slow">${lat}ms</b>`;
    }
  }

  function roomCard(room){
    const players = Array.isArray(room.players) ? room.players : [];
    const count = `${room.node_count||players.length}${room.node_count_max?' / '+room.node_count_max:''} 人`;
    const gameVal = String(room.game || '');
    const iconUrl = room.game_icon || 'https://tinfoil.media/ti/FFFFFFFFFFFFFFFF/48/48';
    return `<div class="room-item" data-game="${gameVal}">
      <div class="room-top">
        <div class="room-host">
          <span>${esc(room.host||'未知房间')}</span>
          <img src="${esc(iconUrl)}" alt="${esc(room.game)}" title="${esc(room.game)}" class="room-host-icon" loading="lazy">
        </div>
        <span class="room-game">${esc(room.game)}</span>
      </div>
      <div class="room-meta">
        <span class="green">● 正在联机</span>
        <span>|</span>
        <span>${esc(count)}</span>
        <span>|</span>
        <span>🖥️ ${esc(room.server_name)}</span>
      </div>
      <div class="room-players">${players.map(p=>`<span class="player">${esc(p)}</span>`).join('')}</div>
    </div>`;
  }

  function applyFilter(autoExpand){
    if(autoExpand === undefined) autoExpand = false;
    const g = state.game;
    const isAll = (g === 'all');
    const isAllServers = (g === 'all_servers');

    const filteredRooms = isAllServers ? state.rooms : (isAll ? state.rooms : state.rooms.filter(r => r.game === g));
    const onlineCount = state.servers.filter(s=>s.status==='online').length;
    const totalOnline = state.servers.filter(s=>s.status==='online').reduce((a,s)=>a+(s.online||0),0);
    $('ovServers').textContent = `${onlineCount}/${state.servers.length}`;
    $('ovOnline').textContent = totalOnline;
    $('ovIdle').textContent = state.servers.filter(s=>s.status==='online').reduce((a,s)=>a+(s.idle||0),0);
    $('ovRooms').textContent = filteredRooms.length;

    const allRooms = document.querySelectorAll('.room-item');
    allRooms.forEach(el => {
      el.style.display = (isAll || isAllServers || el.dataset.game === g) ? '' : 'none';
    });

    state.servers.forEach(s => {
      const group = document.querySelector(`.server-group[data-id="${s.id}"]`);
      if(!group) return;
      const items = group.querySelectorAll('.room-item');
      let visible = 0;
      items.forEach(el => { if(el.style.display !== 'none') visible++; });

      const isOnline = s.status === 'online' && !s.error;

      if(isAllServers){
        group.style.display = '';
        if(autoExpand && !group.classList.contains('open')){
          group.classList.add('open');
          state.expanded.add(s.id);
        }
        group.querySelectorAll('.no-rooms, .no-rooms-empty, .no-rooms-match').forEach(el => el.remove());
        if(items.length === 0 && isOnline){
          let emptyMsg = group.querySelector('.no-rooms-empty');
          if(!emptyMsg){
            emptyMsg = document.createElement('div');
            emptyMsg.className = 'no-rooms-empty no-rooms';
            emptyMsg.textContent = '📭 该服务器暂无公开房间';
            const body = group.querySelector('.server-body > .body-inner');
            if(body) body.appendChild(emptyMsg);
          }
          emptyMsg.style.display = '';
        }
      } else if(isAll){
        const hasAnyRooms = items.length > 0;
        group.style.display = (hasAnyRooms && isOnline) ? '' : 'none';
        if(autoExpand && hasAnyRooms && !group.classList.contains('open')){
          group.classList.add('open');
          state.expanded.add(s.id);
        }
        group.querySelectorAll('.no-rooms, .no-rooms-empty, .no-rooms-match').forEach(el => el.remove());
      } else {
        if(visible > 0 && isOnline){
          group.style.display = '';
          if(autoExpand && !group.classList.contains('open')){
            group.classList.add('open');
            state.expanded.add(s.id);
          }
          group.querySelectorAll('.no-rooms, .no-rooms-empty, .no-rooms-match').forEach(el => el.remove());
        } else {
          group.style.display = 'none';
        }
        group.querySelectorAll('.no-rooms, .no-rooms-empty').forEach(el => el.style.display = 'none');
      }
    });

    const visibleGroups = document.querySelectorAll('.server-group:not([style*="display: none"])');
    let globalMsg = document.getElementById('no-server-match');
    if(!isAll && !isAllServers && visibleGroups.length === 0){
      if(!globalMsg){
        globalMsg = document.createElement('div');
        globalMsg.id = 'no-server-match';
        globalMsg.className = 'no-rooms';
        globalMsg.style.cssText = 'text-align:center;padding:24px;font-size:14px;';
        globalMsg.textContent = `🔍 没有服务器有游戏「${g}」的房间`;
        $('serverList').appendChild(globalMsg);
      }
      globalMsg.textContent = `🔍 没有服务器有游戏「${g}」的房间`;
      globalMsg.style.display = '';
    } else if(globalMsg){
      globalMsg.style.display = 'none';
    }
  }

  function renderServers(){
    const list = $('serverList');
    const roomsByServer = {};
    state.rooms.forEach(r => { (roomsByServer[r.server_id] = roomsByServer[r.server_id] || []).push(r); });

    const onlineCount = state.servers.filter(s => s.status==='online').length;
    const totalOnline = state.servers.filter(s=>s.status==='online').reduce((a,s)=>a+(s.online||0),0);
    const totalIdle = state.servers.filter(s=>s.status==='online').reduce((a,s)=>a+(s.idle||0),0);
    $('ovServers').textContent = `${onlineCount}/${state.servers.length}`;
    $('ovOnline').textContent = totalOnline;
    $('ovIdle').textContent = totalIdle;
    $('ovRooms').textContent = state.rooms.length;

    if(!state.servers.length){
      if(state.firstLoad){ list.innerHTML = '<div class="skeleton"></div><div class="skeleton"></div>'; }
      return;
    }

    const existing = state._domCache || (state._domCache = new Map());
    if(existing.size === 0){
      list.querySelectorAll('.server-group').forEach(el => { existing.set(el.dataset.id, el); });
    }

    const currentIds = new Set(state.servers.map(s => s.id));
    for (const [id, el] of existing.entries()) {
      if (!currentIds.has(id)) {
        el.remove();
        existing.delete(id);
      }
    }

    const order = [];

    state.servers.forEach((s) => {
      const dot = statusDot(s.status);
      const rooms = roomsByServer[s.id] || [];
      const regionTxt = s.region ? `<span class="region">${esc(s.region)}</span>` : '';
      const errMsg = s.error ? `<div class="server-error">⚠️ ${esc(s.error)}</div>` : '';
      const roomsHtml = rooms.length
        ? `<div class="room-list">${rooms.map(r=>roomCard(r)).join('')}</div>`
        : '';

      let group = existing.get(s.id);
      if(group){
        const dotEl = group.querySelector('.server-status-dot');
        if(dotEl && dotEl.className !== 'server-status-dot '+dot) dotEl.className = 'server-status-dot ' + dot;

        const nameEl = group.querySelector('.server-name');
        const nameHtml = `${esc(s.name)} ${regionTxt}`;
        if(nameEl && nameEl.innerHTML !== nameHtml) nameEl.innerHTML = nameHtml;

        const detailEl = group.querySelector('.server-detail');
        const detailHtml = `<span class="addr-text" title="点击复制地址">${esc(s.address)}</span>`;
        if(detailEl && detailEl.innerHTML !== detailHtml) detailEl.innerHTML = detailHtml;
        const addrEl = group.querySelector('.addr-text');
        if(addrEl && !addrEl._copyBound){ addrEl._copyBound=true; addrEl.addEventListener('click', (e)=>{ e.stopPropagation(); copyAddr(s.address, addrEl); }); }

        const statBs = group.querySelectorAll('.stat-item b');
        if(statBs.length>=3){
          const vals = [String(s.online||0), String(s.idle||0), String(s.room_count||0)];
          statBs[0].textContent = vals[0];
          statBs[1].textContent = vals[1];
          statBs[2].textContent = vals[2];
        }

        const latencyEl = group.querySelector('.stat-item.latency');
        if(latencyEl){
          const badge = latencyEl.querySelector('.latency-badge');
          const newBadge = latencyHTML(s);
          if(!badge || badge.outerHTML !== newBadge){
            latencyEl.innerHTML = `<span>延迟</span>${newBadge}`;
          }
        }

        const shouldOpen = state.expanded.has(s.id);
        const isOpen = group.classList.contains('open');
        if(shouldOpen !== isOpen) group.classList.toggle('open', shouldOpen);

        const body = group.querySelector('.server-body > .body-inner');
        if(body){
          const newBody = errMsg + roomsHtml;
          if(body.innerHTML !== newBody) body.innerHTML = newBody;
        }

        const oldMsg = group.querySelector('.no-rooms-match');
        if(oldMsg) oldMsg.remove();
      } else {
        const isOpen = state.expanded.has(s.id) ? 'open' : '';
        const div = document.createElement('div');
        div.className = `server-group ${isOpen}`;
        div.dataset.id = s.id;
        div.innerHTML = `
          <div class="server-head">
            <div class="server-status-dot ${dot}"></div>
            <div class="server-info">
              <div class="server-name">${esc(s.name)} ${regionTxt}</div>
              <div class="server-detail">
                <span class="addr-text" title="点击复制地址">${esc(s.address)}</span>
              </div>
            </div>
            <div class="server-stats">
              <div class="stat-item online"><span>在线</span><b>${s.online||0}</b></div>
              <div class="stat-item idle"><span>空闲</span><b>${s.idle||0}</b></div>
              <div class="stat-item rooms"><span>房间</span><b>${s.room_count||0}</b></div>
              <div class="stat-item latency">
                <span>延迟</span>
                ${latencyHTML(s)}
              </div>
            </div>
          </div>
          <div class="server-body"><div class="body-inner">
            ${errMsg}
            ${roomsHtml}
          </div></div>`;
        existing.set(s.id, div);
        div.querySelector('.server-head').addEventListener('click', (e) => {
          if(e.target.closest('.addr-text')) return;
          const id = div.dataset.id;
          if(state.expanded.has(id)){ state.expanded.delete(id); div.classList.remove('open'); }
          else { state.expanded.add(id); div.classList.add('open'); }
        });
        const addrEl = div.querySelector('.addr-text');
        if(addrEl){ addrEl.addEventListener('click', (e) => { e.stopPropagation(); copyAddr(s.address, addrEl); }); }
      }
      order.push(existing.get(s.id));
    });

    if(state.firstLoad || list.children.length === 0){
      list.innerHTML = '';
      const frag = document.createDocumentFragment();
      order.forEach(el => frag.appendChild(el));
      list.appendChild(frag);
      state.firstLoad = false;
    } else {
      const current = Array.from(list.children);
      let changed = current.length !== order.length;
      if(!changed){ for(let i=0;i<current.length;i++){ if(current[i]!==order[i]){ changed=true; break; } } }
      if(changed){
        const frag = document.createDocumentFragment();
        order.forEach(el => frag.appendChild(el));
        list.appendChild(frag);
      }
    }
  }

  function renderFilters(){
    const games = [...new Set(state.rooms.map(r => r.game).filter(Boolean))];
    const tabs = ['all_servers', 'all', ...games.slice(0,10)];
    const container = $('filters');
    const existing = container.children;

    while(existing.length < tabs.length){
      const btn = document.createElement('button');
      btn.className = 'filter-tab';
      btn.addEventListener('click', () => {
        container.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.game = btn.dataset.game;

        if(state.game === 'all_servers'){
          state.servers.forEach(s => {
            const group = document.querySelector(`.server-group[data-id="${s.id}"]`);
            if(!group) return;
            const hasRooms = (s.room_count || 0) > 0;
            if(hasRooms){
              if(!group.classList.contains('open')){
                group.classList.add('open');
                state.expanded.add(s.id);
              }
            } else {
              group.classList.remove('open');
              state.expanded.delete(s.id);
            }
          });
          applyFilter(false);
        } else {
          applyFilter(true);
        }
      });
      container.appendChild(btn);
    }
    while(existing.length > tabs.length){ existing[existing.length-1].remove(); }

    tabs.forEach((g, i) => {
      const btn = existing[i];
      let label;
      if(g === 'all'){
        label = `总房间 (${state.rooms.length})`;
      } else if(g === 'all_servers'){
        label = `全部 (${state.servers.length})`;
      } else {
        label = esc(g);
      }
      btn.dataset.game = g;
      btn.textContent = label;
      const active = (g === 'all' && state.game === 'all')
                  || (g === 'all_servers' && state.game === 'all_servers')
                  || (g !== 'all' && g !== 'all_servers' && state.game === g);
      btn.classList.toggle('active', active);
    });
  }

  function render(data){
    state.servers = Array.isArray(data.servers) ? data.servers : [];
    state.rooms = Array.isArray(data.rooms) ? data.rooms : [];

    if(state.firstExpand){
      state.game = 'all_servers';
      state.firstExpand = false;
    }

    if(state.game === 'all_servers'){
      state.servers.forEach(s => {
        const hasRooms = (s.room_count || 0) > 0;
        if (hasRooms) {
          state.expanded.add(s.id);
        } else {
          state.expanded.delete(s.id);
        }
      });
    }

    requestAnimationFrame(() => {
      renderFilters();
      renderServers();
      applyFilter(false);
    });
  }

  async function load(force=false){
    if(state.loading) return;
    state.loading = true;
    const btn = $('refreshBtn');
    btn.classList.add('loading');
    try{
      const url = '/api/snapshot?refresh=' + (force?'1':'0') + '&_=' + Date.now();
      const data = await getJSON(url);
      await new Promise(res => requestAnimationFrame(res));
      render(data);
      if(btn){ btn.classList.remove('loading'); btn.classList.add('success'); btn.querySelector('.refresh-text').innerHTML='<span>✓ 已刷新</span>'; setTimeout(()=>{btn.classList.remove('success');}, 1200); }
    }catch(e){
      btn.classList.remove('loading');
    }finally{
      state.loading = false;
      scheduleRefresh();
    }
  }

  let refreshTimer = null;
  function scheduleRefresh(){
    if(refreshTimer) clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => { load(false); }, 10000);
  }

  $('refreshBtn').addEventListener('click', ()=>{
    if(refreshTimer) clearTimeout(refreshTimer);
    load(true);
  });

  document.addEventListener('keydown', e=>{
    if(e.target.tagName==='INPUT'||e.target.tagName==='SELECT') return;
    if(e.key==='r'||e.key==='R'){
      if(refreshTimer) clearTimeout(refreshTimer);
      load(true);
    }
  });

  let touchStartY=0;
  document.addEventListener('touchstart',e=>{touchStartY=e.changedTouches[0].screenY},{passive:true});
  document.addEventListener('touchend',e=>{
    const dy = touchStartY - e.changedTouches[0].screenY;
    if(dy < -80 && window.scrollY <= 0){
      if(refreshTimer) clearTimeout(refreshTimer);
      load(true);
    }
  },{passive:true});

  state.firstLoad = true;
  state.firstExpand = true;
  load();
})();
</script>
</body></html>"""

# ══════════════════════════════════════════════════════════════════════════════
# HTTP 请求处理器
# ══════════════════════════════════════════════════════════════════════════════

class MonitorHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {format % args}")

    def _send_response(self, body: bytes, headers: dict[str, str], status: int = 200) -> None:
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict[str, Any], cache_hit: bool = False, status: int = 200) -> None:
        body, headers, status = make_json_response(data, cache_hit, status)
        self._send_response(body, headers, status)

    def _send_text(self, text: str, content_type: str = "text/plain; charset=utf-8", status: int = 200) -> None:
        body = text.encode("utf-8")
        self._send_response(body, {"Content-Type": content_type}, status)

    def _send_html(self, html: str, status: int = 200) -> None:
        self._send_text(html, "text/html; charset=utf-8", status)

    def _parse_query(self) -> dict[str, str]:
        parsed = urllib.parse.urlparse(self.path)
        self.path = parsed.path
        return parse_query(parsed.query)

    def do_GET(self) -> None:
        query = self._parse_query()
        try:
            if self.path == "/":
                self._send_html(PAGE_HTML)
            elif self.path == "/api/health":
                self._send_json({
                    "ok": True, "service": APP_NAME, "time": utc_now(),
                    "server_count": len(SERVERS),
                    "source": "direct LAN-Play server queries",
                    "cache_ttl": CACHE_TTL,
                })
            elif self.path == "/api/servers":
                servers, hit = scan_all(wants_refresh(query))
                public = [{k: v for k, v in s.items() if k != "rooms"} for s in servers]
                self._send_json({"ok": True, "items": public, "checked_at": utc_now()}, hit)
            elif self.path == "/api/dashboard":
                server_id = query.get("server", SERVERS[0]["id"]).strip()
                if server_id not in SERVERS_BY_ID:
                    raise ValueError("server 不在本地服务器配置中")
                result, hit = scan_server(SERVERS_BY_ID[server_id], wants_refresh(query))
                self._send_json({"ok": True, **result}, hit)
            elif self.path == "/api/rooms":
                page = bounded_int(query, "page", 1, 1, 10000)
                page_size = bounded_int(query, "page_size", 50, 1, 100)
                server_filter = query.get("server", "").strip()
                if server_filter and server_filter not in SERVERS_BY_ID:
                    raise ValueError("server 不在本地服务器配置中")
                servers, hit = scan_all(wants_refresh(query))
                rooms = [r for s in servers if not server_filter or s["id"] == server_filter for r in s["rooms"]]
                total = len(rooms)
                total_pages = max(1, (total + page_size - 1) // page_size)
                page = min(page, total_pages)
                start = (page - 1) * page_size
                self._send_json({
                    "ok": True, "items": rooms[start:start + page_size],
                    "page": page, "pageSize": page_size, "total": total,
                    "totalPages": total_pages, "checked_at": utc_now(),
                }, hit)
            elif self.path == "/api/snapshot":
                server_id = query.get("server", "").strip()
                if server_id and server_id not in SERVERS_BY_ID:
                    raise ValueError("server 不在本地服务器配置中")
                servers, hit = scan_all(wants_refresh(query))
                if not server_id:
                    server_id = servers[0]["id"] if servers else ""
                selected = next((s for s in servers if s["id"] == server_id), None)
                rooms = [r for s in servers for r in s["rooms"]]
                self._send_json({
                    "ok": True, "checked_at": utc_now(), "selected": selected,
                    "servers": servers, "rooms": rooms,
                    "online_servers": sum(1 for s in servers if s["status"] == "online"),
                    "total_online": sum(s["online"] for s in servers if s["status"] == "online"),
                }, hit)
            else:
                self._send_json({"ok": False, "error": "页面或接口不存在"}, status=404)
        except ValueError as e:
            self._send_json({"ok": False, "error": str(e)}, status=400)
        except Exception as e:
            self._send_json({"ok": False, "error": str(e)}, status=500)

    def do_POST(self) -> None:
        self._send_json({"ok": False, "error": "仅支持 GET 请求"}, status=405)

# ══════════════════════════════════════════════════════════════════════════════
# 启动入口 (支持 Kivy Android 内嵌 WebView 启动)
# ══════════════════════════════════════════════════════════════════════════════

def start_server():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    
    print(f"[启动] {APP_NAME}")
    print(f"[监听] http://{host}:{port}")
    
    server = HTTPServer((host, port), MonitorHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.serve_forever()
    except Exception:
        server.server_close()

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass
    from android.runnable import run_on_ui_thread

    WebView = autoclass('android.webkit.WebView')
    WebViewClient = autoclass('android.webkit.WebViewClient')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')

    class BrowserWidget(Widget):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # 延时 0.5 秒确保 Activity 完全准备就绪，避免闪退
            Clock.schedule_once(self.create_webview, 0.5)

        @run_on_ui_thread
        def create_webview(self, *args):
            try:
                activity = PythonActivity.mActivity
                webview = WebView(activity)
                settings = webview.getSettings()
                settings.setJavaScriptEnabled(True)
                settings.setDomStorageEnabled(True)
                settings.setLoadWithOverviewMode(True)
                settings.setUseWideViewPort(True)
                settings.setDatabaseEnabled(True)
                
                wvc = WebViewClient()
                webview.setWebViewClient(wvc)
                
                # 加载本地后端服务页面
                webview.loadUrl('http://127.0.0.1:5000/')
                activity.setContentView(webview)
            except Exception as e:
                print(f"[UI错误] 初始化 WebView 失败: {e}")

    class LanPlayMonitorApp(App):
        def build(self):
            t = threading.Thread(target=start_server, daemon=True)
            t.start()
            return BrowserWidget()
else:
    class LanPlayMonitorApp(App):
        def build(self):
            t = threading.Thread(target=start_server, daemon=True)
            t.start()
            print("请在浏览器打开 http://127.0.0.1:5000/")
            return Widget()

if __name__ == "__main__":
    try:
        LanPlayMonitorApp().run()
    except KeyboardInterrupt:
        print("\n[停止] 正在关闭...")
        for scanner in ACTIVE_SCANNERS.values():
            scanner.close()
        print("[停止] 已关闭")
