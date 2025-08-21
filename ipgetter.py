import re
from ipaddress import ip_network, ip_address
import re
from typing import Optional


SEP_RE = re.compile(r"[,\s;]+")

def _strip_comments_and_tokenize(text: str):
    tokens = []
    for raw_line in (text or "").splitlines():
        line = raw_line.split("#", 1)[0]  # обрезаем комментарий до конца строки
        for tok in SEP_RE.split(line.strip()):
            if tok:
                tokens.append(tok)
    return tokens

def get_ip_list(ip_string: str):
    """Parse IP inputs: supports single IPs and CIDR ranges in one string.
    - Accepts comma/space separated tokens.
    - Expands CIDRs to host addresses (excludes network/broadcast).
    - Deduplicates and returns a sorted list (IPv4-friendly sort).
    """
    tokens = re.split(r"[\s,;]+", (ip_string or "").strip())
    ips = set()
    for t in tokens:
        if not t:
            continue
        if "/" in t:
            net = ip_network(t, strict=False)
            ips.update(str(ip) for ip in net.hosts())
        else:
            ips.add(str(ip_address(t)))
    def _key(v):
        try:
            return tuple(int(x) for x in v.split("."))
        except ValueError:
            return v
    return sorted(ips, key=_key)

def parse_sources(ips_text: str, file_path: Optional[str]):

    all_text = ips_text or ""
    if file_path:
        with open(file_path, "r", encoding="utf-8") as f:
            all_text += "\n" + f.read()

    
    tokens = _strip_comments_and_tokenize(all_text)

    
    ip_list = get_ip_list(" ".join(tokens))

    summary = {"tokens_total": len(tokens), "targets_total": len(ip_list)}
    warnings = []
    return ip_list, summary, warnings
