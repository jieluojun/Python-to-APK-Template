#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立 LAN-Play / ldn_mitm 房间监控网页（零第三方依赖版）

完全使用 Python 标准库：
- http.server 替代 Flask
- urllib.request 替代 requests
- 所有 UDP 扫描、房间解析逻辑保持不变

启动：
    python lan_play_monitor.py
    # 浏览器打开 http://127.0.0.1:5000/

局域网访问：
    HOST=0.0.0.0 python lan_play_monitor.py

支持类型：
- graphql：slp-server-rust
- rest：switch-lan-play Node 版
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
# 常量 & 配置
# ══════════════════════════════════════════════════════════════════════════════

APP_NAME = "direct-lan-play-monitor"
CACHE_TTL = max(1, int(os.getenv("CACHE_TTL", "12")))
REQUEST_TIMEOUT = max(1.0, float(os.getenv("REQUEST_TIMEOUT", "5")))
MAX_WORKERS = 8

DEFAULT_SERVERS: list[dict[str, Any]] = [
    {"id": "1", "name": "tekn0", "host": "tekn0.net", "port": 11451, "type": "graphql", "region": "🇺🇸 美国"},
    {"id": "2", "name": "jaxlewis", "host": "srv.jaxlewis.top", "port": 11451, "type": "graphql", "region": "🇨🇳 河南"},
    {"id": "3", "name": "jaysea1", "host": "switch.jayseateam.nl", "port": 11451, "type": "graphql", "region": "🇳🇱 荷兰"},
    {"id": "4", "name": "jaysea2", "host": "switch.jayseateam.nl", "port": 11453, "type": "graphql", "region": "🇳🇱 荷兰"},
    {"id": "5", "name": "lbxmb", "host": "lan.lbxmb.fr", "port": 11451, "type": "graphql", "region": "🇫🇷 法国"},
    {"id": "6", "name": "muitxobem", "host": "muitxobem-lanplay.ddns.net", "port": 11451, "type": "graphql", "region": "🇺🇸 美国"},
    {"id": "7", "name": "lp1", "host": "lp1.cpalm.org", "port": 11451, "type": "graphql", "region": "🇨🇳 台湾"},
    {"id": "8", "name": "owlet", "host": "www.grayowlet.cn", "port": 11451, "type": "graphql", "region": "🇨🇳 内蒙古"},
    {"id": "9", "name": "olunira", "host": "olunira.fun", "port": 11451, "type": "graphql", "region": "🇨🇳 北京"},
    {"id": "10", "name": "mulaosi", "host": "ns.mulaosi.cn", "port": 11451, "type": "graphql", "region": "🇨🇳 广东"},
    {"id": "11", "name": "r3ps4j", "host": "switch.r3ps4j.nl", "port": 11452, "type": "graphql", "region": "🇩🇰 丹麦"},
    {"id": "12", "name": "erdbeerbaerlp", "host": "erdbeerbaerlp.de", "port": 11451, "type": "graphql", "region": "🇩🇪 德国"},
]

GAME_TITLES: dict[str, str] = {
    "FFFFFFFFFFFFFFFF": "未知游戏",
    "01006A800016E000": "任天堂明星大乱斗 特别版",
    "0100152000022000": "马里奥赛车8 豪华版",
    "010029F00FCC4000": "马里奥网球 ACE",
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
}

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

UDP_SCAN_SECONDS = max(0.8, float(os.getenv("UDP_SCAN_SECONDS", "2.2")))
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

def game_name(content_id: str) -> str:
    normalized = str(content_id or "").upper()
    return GAME_TITLES.get(normalized, f"未知游戏 ({normalized})" if normalized else "未知游戏")

# ══════════════════════════════════════════════════════════════════════════════
# HTTP 客户端（urllib 替代 requests）
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
        if player_name and player_name not in players:
            players.append(player_name)
        nodes.append({"playerName": player_name})
    host = decode_player_name(payload[0x74 : 0x94])
    if host and host not in players:
        players.insert(0, host)
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
            raise SystemExit(f"指定的服务器配置文件不存在：{path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"无法读取服务器配置 {path}：{exc}") from exc
        if not isinstance(raw, list) or not raw:
            raise SystemExit("服务器配置必须是非空 JSON 数组")
        servers = [validate_server(item) for item in raw]
    else:
        path = Path(__file__).with_name("servers.json")
        merged: dict[str, dict] = {s["id"]: dict(s) for s in DEFAULT_SERVERS}
        if path.is_file():
            try:
                extra = json.loads(path.read_text(encoding="utf-8"))
                print(f"[配置] 已读取 {path}，将与内置服务器合并")
            except (OSError, json.JSONDecodeError) as exc:
                raise SystemExit(f"无法读取服务器配置 {path}：{exc}") from exc
            if not isinstance(extra, list):
                raise SystemExit("servers.json 必须是 JSON 数组")
            for item in extra:
                srv = validate_server(item)
                merged[srv["id"]] = srv
        else:
            print(f"[配置] 未找到 {path}，使用内置服务器列表（{len(merged)} 个）")
        servers = list(merged.values())
    ids = [item["id"] for item in servers]
    if len(ids) != len(set(ids)):
        raise SystemExit("服务器配置中存在重复 id")
    return servers

SERVERS = load_servers()
SERVERS_BY_ID = {item["id"]: item for item in SERVERS}
ACTIVE_SCANNERS = {item["id"]: ActiveRoomScanner(item) for item in SERVERS}

# ══════════════════════════════════════════════════════════════════════════════
# 房间数据规范化 & 扫描逻辑
# ══════════════════════════════════════════════════════════════════════════════

def normalize_room(raw: Any, server: dict[str, Any], index: int) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    content_id = str(raw.get("contentId") or raw.get("content_id") or "").upper()
    nodes = raw.get("nodes") if isinstance(raw.get("nodes"), list) else []
    players: list[str] = []
    for node in nodes:
        if isinstance(node, dict):
            name = str(node.get("playerName") or node.get("player_name") or "").strip()
        else:
            name = str(node).strip()
        if name and name not in players:
            players.append(name)
    host = str(raw.get("hostPlayerName") or raw.get("host_player_name") or "").strip()
    if host and host not in players:
        players.insert(0, host)
    node_count = int_or_zero(raw.get("nodeCount", raw.get("node_count", len(players))))
    node_max = int_or_zero(raw.get("nodeCountMax", raw.get("node_count_max", 0)))
    return {
        "id": str(raw.get("sessionId") or raw.get("session_id") or f"{server['id']}-{index}"),
        "server_id": server["id"],
        "server_name": server["name"],
        "server_address": f"{server['host']}:{server['port']}",
        "content_id": content_id,
        "game": game_name(content_id),
        "host": host or (players[0] if players else "未知玩家"),
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
        result.update({
            "status": "online",
            "online": online,
            "idle": idle,
            "active": max(0, online - idle),
            "room_count": len(rooms),
            "rooms": rooms,
        })
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
        result.update({
            "status": "online",
            "online": online,
            "idle": idle,
            "active": max(0, online - idle),
            "room_count": len(rooms),
            "rooms": rooms,
        })
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
    active_raw_rooms, scanner_error = ACTIVE_SCANNERS[server["id"]].scan()
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
        result["online"] = max(
            int_or_zero(result.get("online")),
            sum(max(1, r["node_count"]) for r in rooms),
        )
        result["active"] = max(0, result["online"] - int_or_zero(result.get("idle")))
        result["error"] = ""
    if result.get("latency_ms") is None:
        result["latency_ms"] = -1
    cache.set(key, result)
    return result, False

def scan_all(force: bool = False) -> tuple[list[dict[str, Any]], bool]:
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
# 前端页面（完整保留）
# ══════════════════════════════════════════════════════════════════════════════

PAGE_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <title>Direct LDN</title>
  <style>
    :root{
      --bg:#dff3ff;--card:rgba(255,255,255,.82);--ink:#0c3154;--muted:#50728d;
      --cyan:#19c8ae;--red:#dc3048;--green:#178a78;--orange:#e8820c;
      --radius-lg:28px;--radius-md:20px;--radius-sm:14px;
      --font:"Segoe UI","PingFang SC","Microsoft YaHei",system-ui,sans-serif;
    }
    @media (prefers-color-scheme: dark){
      :root{
        --bg:#0f1923;--card:rgba(22,34,46,.85);--ink:#e0eef8;--muted:#7a9bb5;
        --green:#3dd9b8;--green-bg:rgba(61,217,184,.12);
      }
    }
    *,*::before,*::after{box-sizing:border-box}
    body{margin:0;min-height:100vh;font-family:var(--font);background:var(--bg);color:var(--ink)}
    .page{width:min(1100px,calc(100%-32px));margin:auto;padding:24px 0}
    .glass{border:1px solid rgba(255,255,255,.8);background:var(--card);backdrop-filter:blur(15px)}
    .hero{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px 24px;border-radius:var(--radius-lg)}
    .brand{display:flex;align-items:center;gap:12px}
    .logo{width:46px;height:46px;border-radius:14px;display:grid;place-items:center;background:linear-gradient(145deg,#fff970,#ffd626);font-size:20px}
    .scan{display:flex;align-items:center;gap:10px;font-weight:700;font-size:13px}
    .dot{width:10px;height:10px;border-radius:50%;background:var(--cyan);animation:pulse-dot 2s ease-in-out infinite}
    .refresh{border:0;border-radius:12px;padding:10px 18px;background:#e1f1fa;font-weight:750;cursor:pointer;display:inline-flex;gap:6px}
    .overview{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:18px}
    .ov-card{padding:18px 16px;background:var(--card);border-radius:var(--radius-md);text-align:center}
    .ov-card b{font-size:26px;font-weight:900}
    .server-list{margin-top:18px;display:grid;gap:12px}
    .server-group{background:var(--card);border-radius:var(--radius-md);overflow:hidden}
    .server-head{display:flex;align-items:center;gap:14px;padding:18px 22px;cursor:pointer}
    .server-status-dot{width:12px;height:12px;border-radius:50%}
    .server-status-dot.online{background:var(--green)}
    .server-status-dot.offline{background:var(--red)}
    .latency-badge{font-size:11px;padding:3px 8px;border-radius:8px}
    .latency-badge.fast{background:var(--green-bg);color:var(--green)}
    .latency-badge.error{background:var(--red);color:#fff}
    .chevron{transition:transform .25s}
    .server-group.open .chevron{transform:rotate(180deg)}
    .server-body{display:grid;grid-template-rows:0fr;transition:grid-template-rows .3s}
    .server-group.open .server-body{grid-template-rows:1fr}
    .room-list{padding:0 22px 20px;display:grid;gap:10px}
    .room-item{padding:16px;border-radius:16px;background:var(--card)}
    .room-host{font-size:16px;font-weight:800}
    .room-game{font-size:12px;padding:4px 12px;border-radius:999px;background:#e9f5fb}
    .room-players{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px}
    .player{padding:3px 10px;border-radius:999px;background:var(--green-bg);font-size:11px}
    .filters{display:flex;gap:8px;overflow-x:auto;padding:14px 0 4px}
    .filter-tab{border:0;border-radius:999px;padding:9px 18px;background:#e8f3f9;font-weight:700;cursor:pointer}
    .filter-tab.active{background:#cde9fa;color:#0c5d91}
    footer{text-align:center;padding:24px;font-size:12px;color:var(--muted)}
  </style>
</head>
<body>
<div class="page">
  <section class="hero glass">
    <div class="brand"><div class="logo">🎮</div><div><strong>Direct LDN</strong><small>独立 LAN-Play 监控</small></div></div>
    <div class="scan"><div class="dot"></div><span>实时扫描</span>
      <button id="refreshBtn" class="refresh">刷新</button>
    </div>
  </section>

  <div class="overview">
    <div class="ov-card"><span>在线服务器</span><b id="ovServers">—</b></div>
    <div class="ov-card"><span>总在线</span><b id="ovOnline">—</b></div>
    <div class="ov-card"><span>空闲</span><b id="ovIdle">—</b></div>
    <div class="ov-card"><span>总房间</span><b id="ovRooms">—</b></div>
  </div>

  <div class="filters" id="filters"></div>
  <div class="server-list" id="serverList"></div>
  <footer>Direct LDN · LAN-Play / ldn_mitm 监控</footer>
</div>

<script>
(() => {
  const state = { servers:[], rooms:[], game:'all', expanded:new Set() };
  const $ = id => document.getElementById(id);

  async function load(){
    const r = await fetch('/api/snapshot?_=' + Date.now());
    const d = await r.json();
    state.servers = d.servers || [];
    state.rooms = d.rooms || [];
    render();
  }

  function render(){
    $('ovServers').textContent = state.servers.filter(s=>s.status==='online').length + '/' + state.servers.length;
    $('ovOnline').textContent = state.servers.reduce((a,s)=>a+(s.online||0),0);
    $('ovIdle').textContent = state.servers.reduce((a,s)=>a+(s.idle||0),0);
    $('ovRooms').textContent = state.rooms.length;

    const list = $('serverList');
    list.innerHTML = '';
    state.servers.forEach(s => {
      const el = document.createElement('div');
      el.className = 'server-group' + (state.expanded.has(s.id)?' open':'');
      el.innerHTML = `
        <div class="server-head">
          <div class="server-status-dot ${s.status}"></div>
          <div style="flex:1"><strong>${s.name}</strong><br><small>${s.address}</small></div>
          <div class="latency-badge ${s.latency_ms<100?'fast':s.latency_ms>300?'slow':'normal'}">
            ${s.latency_ms>=0?s.latency_ms+'ms':'! 错误'}
          </div>
          <div class="chevron">⌄</div>
        </div>
        <div class="server-body">
          <div class="room-list">
            ${(s.rooms||[]).map(r=>`
              <div class="room-item">
                <div class="room-host">${r.host}</div>
                <div class="room-game">${r.game}</div>
                <div class="room-players">
                  ${r.players.map(p=>`<span class="player">${p}</span>`).join('')}
                </div>
              </div>
            `).join('')}
          </div>
        </div>`;
      el.querySelector('.server-head').onclick = () => {
        state.expanded.has(s.id) ? state.expanded.delete(s.id) : state.expanded.add(s.id);
        render();
      };
      list.appendChild(el);
    });
  }

  $('refreshBtn').onclick = () => load();
  load();
  setInterval(load, 10000);
})();
</script>
</body></html>"""

# ══════════════════════════════════════════════════════════════════════════════
# HTTP 请求处理器
# ══════════════════════════════════════════════════════════════════════════════

class MonitorHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}")

    def _send(self, body, headers, status=200):
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self._send(body, {"Content-Type": "application/json; charset=utf-8"}, status)

    def _html(self):
        self._send(PAGE_HTML.encode(), {"Content-Type": "text/html; charset=utf-8"})

    def do_GET(self):
        if self.path.startswith("/api/"):
            q = self.path.split("?", 1)[1] if "?" in self.path else ""
            query = parse_query(q)
            if self.path.startswith("/api/snapshot"):
                servers, _ = scan_all(wants_refresh(query))
                rooms = [r for s in servers for r in s["rooms"]]
                self._json({
                    "ok": True,
                    "servers": servers,
                    "rooms": rooms,
                    "checked_at": utc_now(),
                })
            else:
                self._json({"ok": False, "error": "API not found"}, 404)
        else:
            self._html()

    def do_POST(self):
        self._json({"ok": False, "error": "Method Not Allowed"}, 405)

# ══════════════════════════════════════════════════════════════════════════════
# ✅ 对外 API（供 Kivy / main.py 使用）
# ══════════════════════════════════════════════════════════════════════════════

def start_server(host: str | None = None, port: int | None = None) -> HTTPServer:
    """
    非阻塞启动 HTTP Server
    供 Kivy / Android / 其他框架 import 使用
    """
    host = host or os.getenv("HOST", "127.0.0.1")
    port = port or int(os.getenv("PORT", "5000"))

    server = HTTPServer((host, port), MonitorHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    threading.Thread(
        target=server.serve_forever,
        daemon=True,
        name="LanPlayHTTPServer"
    ).start()

    print(f"[LAN-Play] HTTP Server started: http://{host}:{port}/")
    return server

# ══════════════════════════════════════════════════════════════════════════════
# ✅ 直接运行（PC / Termux / Android 终端）
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import webbrowser
    import subprocess

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}/"

    print(f"[启动] {APP_NAME}")
    print(f"\033[94m[监听] {url}\033[0m")

    server = start_server(host=host, port=port)

    def try_open():
        time.sleep(0.4)
        try:
            subprocess.run(["am", "start", "--user", "0",
                           "-a", "android.intent.action.VIEW",
                           "-d", url], timeout=2)
            return
        except Exception:
            pass
        try:
            subprocess.run(["termux-open-url", url], timeout=2)
            return
        except Exception:
            pass
        webbrowser.open(url)

    threading.Thread(target=try_open, daemon=True).start()

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n[停止] 正在关闭...")
        server.server_close()
        for scanner in ACTIVE_SCANNERS.values():
            scanner.close()
        print("[停止] 已关闭")
