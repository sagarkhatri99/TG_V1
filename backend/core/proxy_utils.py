import logging
import socks
from urllib.parse import urlparse
from typing import Optional, Dict, Any, Tuple, Union

# Define proxy types mapping to python-socks types (used by Telethon)
# Telethon uses these integer values
PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3

logger = logging.getLogger(__name__)

def parse_proxy_string(proxy_str: str, default_type: str = "socks5") -> Dict[str, Any]:
    """
    Parse a proxy string into its components (host, port, username, password).
    Supports:
    - host:port:username:password (Common IPRoyal format)
    - scheme://username:password@host:port
    - scheme://host:port
    - host:port
    
    Defaults to SOCKS5 as per user requirement.
    """
    if not proxy_str:
        return {}

    proxy_str = proxy_str.strip()
    
    # Force SOCKS5 if user requested "socks5 only" in their mind, 
    # but we'll try to follow the provided string if it explicitly has a scheme.
    # However, for default_type we'll use socks5.
    
    # 1. Check for host:port:username:password format
    parts = proxy_str.split(':')
    if len(parts) == 4:
        try:
            # Basic validation that port is numeric
            int(parts[1])
            return {
                "host": parts[0],
                "port": int(parts[1]),
                "username": parts[2],
                "password": parts[3],
                "proxy_type": "socks5" # Preferred
            }
        except ValueError:
            pass # Not the 4-part format we expected, try URL parsing

    # 2. Try parsing as a URL
    if "://" not in proxy_str:
        # Default to socks5
        test_str = f"socks5://{proxy_str}"
    else:
        test_str = proxy_str

    try:
        parsed = urlparse(test_str)
        scheme = parsed.scheme.lower() if parsed.scheme else "socks5"
        
        # Normalize proxy type - default to socks5 if not http/socks4
        if "socks5" in scheme or "socks" in scheme:
            p_type = "socks5"
        elif "socks4" in scheme:
            p_type = "socks4"
        elif "http" in scheme:
            p_type = "http"
        else:
            p_type = "socks5"

        return {
            "host": parsed.hostname,
            "port": parsed.port,
            "username": parsed.username,
            "password": parsed.password,
            "proxy_type": p_type
        }
    except Exception as e:
        logger.error(f"Failed to parse proxy string '{proxy_str}': {e}")
        return {}

def build_proxy_config(proxy_record: Any) -> Dict[str, Any]:
    """
    Takes a proxy record (either a Proxy model instance or a dictionary)
    and returns various formats needed for different libraries.
    
    Returns a dict with:
    - 'telethon': Tuple for Telethon (socks_type, host, port, rdns, user, pass)
    - 'requests': Dictionary for requests library proxies
    - 'url': Full scheme://user:pass@host:port string
    - 'details': Masked dictionary for logging
    """
    if hasattr(proxy_record, "__dict__") or not isinstance(proxy_record, dict):
        # It's likely a SQLAlchemy model or object
        proxy_url = getattr(proxy_record, 'proxy_url', None)
        proxy_type = getattr(proxy_record, 'proxy_type', 'socks5') or 'socks5'
        
        # Try to get attributes first (backward compatibility or if assigned manually)
        host = getattr(proxy_record, 'host', None)
        port = getattr(proxy_record, 'port', None)
        username = getattr(proxy_record, 'username', None)
        password = getattr(proxy_record, 'password', None)
        
        # If any essential component is missing, parse from proxy_url
        if not all([host, port]) and proxy_url:
            details = parse_proxy_string(proxy_url, proxy_type)
            host = details.get("host")
            port = details.get("port")
            username = username or details.get("username")
            password = password or details.get("password")
            proxy_type = details.get("proxy_type", proxy_type)
    else:
        # It's a dict
        host = proxy_record.get('host')
        port = proxy_record.get('port')
        username = proxy_record.get('username')
        password = proxy_record.get('password')
        proxy_type = proxy_record.get('proxy_type', 'socks5') or 'socks5'
        proxy_url = proxy_record.get('proxy_url')
        
        if not all([host, port]) and proxy_url:
            details = parse_proxy_string(proxy_url, proxy_type)
            host = details.get("host")
            port = details.get("port")
            username = username or details.get("username")
            password = password or details.get("password")
            proxy_type = details.get("proxy_type", proxy_type)

    proxy_type = proxy_type.lower()
    
    # Map to socks and Telethon types
    # Prefer SOCKS5
    if "socks5" in proxy_type or "socks" in proxy_type:
        s_type = socks.SOCKS5
        t_type = PROXY_TYPE_SOCKS5
        scheme = "socks5"
    elif "socks4" in proxy_type:
        s_type = socks.SOCKS4
        t_type = PROXY_TYPE_SOCKS4
        scheme = "socks4"
    else:
        s_type = socks.HTTP
        t_type = PROXY_TYPE_HTTP
        scheme = "http"

    # 1. Telethon Tuple Format (official dict form is also supported but user asked for tuple/clean standardized shape)
    telethon_config = {
        'proxy_type': t_type,
        'addr': host,
        'port': int(port) if port else 0,
        'rdns': True,
        'username': username,
        'password': password
    }

    # 2. Full URL
    if username and password:
        proxy_url = f"{scheme}://{username}:{password}@{host}:{port}"
    else:
        proxy_url = f"{scheme}://{host}:{port}"

    # 3. Requests Format
    # For SOCKS, requests/urllib3 uses 'socks5h' to ensure remote DNS
    req_scheme = f"{scheme}h" if "socks" in scheme else scheme
    if username and password:
        req_url = f"{req_scheme}://{username}:{password}@{host}:{port}"
    else:
        req_url = f"{req_scheme}://{host}:{port}"
        
    requests_config = {
        "http": req_url,
        "https": req_url
    }

    return {
        "telethon": telethon_config,
        "requests": requests_config,
        "url": proxy_url,
        "details": {
            "type": proxy_type,
            "addr": host,
            "port": port,
            "rdns": True,
            "username": username,
            "password_len": len(password) if password else 0
        }
    }


def verify_proxy_connectivity(proxy_record: Any, timeout: int = 5) -> Tuple[bool, str]:
    """
    Lightweight pre-flight check to verify if a proxy is reachable.
    Uses socket.connect for SOCKS/HTTP to verify the port is open.
    """
    import socket

    config = build_proxy_config(proxy_record)
    details = config.get("details", {})
    host = details.get("addr")
    port = details.get("port")
    p_type = details.get("type")

    if not host or not port:
        return False, "Invalid proxy configuration: missing host or port"

    try:
        # Standard socket check (TCP connect)
        # This only verifies the proxy server is listening, not that it authorizes us
        # or that it has internet connectivity. It's a "lightweight" check.
        with socket.create_connection((host, int(port)), timeout=timeout):
            pass
        return True, f"Proxy {host}:{port} ({p_type}) is reachable."
    except socket.timeout:
        return False, f"Proxy connection timeout after {timeout}s ({host}:{port})"
    except Exception as e:
        return False, f"Proxy connection failed: {str(e)} ({host}:{port})"
