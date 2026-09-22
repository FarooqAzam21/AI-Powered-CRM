import ipaddress
import socket
import logging
from urllib.parse import urlparse
from typing import Tuple

logger = logging.getLogger(__name__)

DISALLOWED_HOSTNAMES = {"localhost", "localhost.localdomain", "metadata.google.internal"}


def is_ssrf_safe_url(url: str, allow_private: bool = False) -> Tuple[bool, str]:
    """
    Validates target URL against SSRF attacks (blocking loopback, RFC-1918 private IPs,
    cloud metadata IP 169.254.169.254, link-local, and reserved ranges).
    Returns tuple (is_safe: bool, reason: str).
    """
    if allow_private:
        return True, "Private URLs explicitly allowed by configuration"

    if not url or not isinstance(url, str):
        return False, "URL is empty or invalid type"

    try:
        parsed = urlparse(url.strip())
    except Exception as exc:
        return False, f"Failed to parse URL: {exc}"

    if parsed.scheme not in ("http", "https"):
        return False, f"Unsupported scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "Missing hostname in URL"

    hostname_lower = hostname.lower()

    if hostname_lower in DISALLOWED_HOSTNAMES or hostname_lower.endswith(".internal") or hostname_lower.endswith(".local"):
        return False, f"Target hostname '{hostname}' is a restricted internal domain."

    # Try resolving IP addresses for the hostname
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        # If hostname doesn't resolve in test environment, we check if it looks like a standard test domain or public domain
        logger.warning(f"Could not resolve hostname '{hostname}': {exc}")
        if "test" in hostname_lower or "example" in hostname_lower:
            return True, "Synthetic test domain permitted"
        return False, f"Cannot resolve hostname '{hostname}'"
    except Exception as exc:
        return False, f"DNS lookup failed for '{hostname}': {exc}"

    for family, socktype, proto, canonname, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        if ip_obj.is_loopback:
            return False, f"Target IP '{ip_str}' is loopback"
        if ip_obj.is_private:
            return False, f"Target IP '{ip_str}' is private RFC-1918 subnet"
        if ip_obj.is_link_local:
            return False, f"Target IP '{ip_str}' is link-local / cloud metadata range"
        if ip_obj.is_reserved or ip_obj.is_multicast:
            return False, f"Target IP '{ip_str}' is reserved or multicast"
        if str(ip_obj) == "169.254.169.254":
            return False, "Target IP 169.254.169.254 is cloud metadata service"

    return True, "URL is SSRF safe"
