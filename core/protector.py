import re
import requests
from urllib.parse import urlparse

DANGEROUS_EXTENSIONS = [
    '.exe', '.msi', '.bat', '.cmd', '.ps1', '.vbs', '.js',
    '.scr', '.pif', '.com', '.jar', '.apk', '.app'
]

SAFE_DOMAINS = [
    'google.com', 'youtube.com', 'github.com', 'wikipedia.org',
    'stackoverflow.com', 'reddit.com', 'twitter.com', 'x.com',
    'linkedin.com', 'medium.com', 'bbc.com', 'cnn.com',
    'reuters.com', 't.me', 'telegram.org', 'python.org',
    'pypi.org', 'developer.mozilla.org', 'aljazeera.net',
    'binance.com', 'coinmarketcap.com', 'tradingview.com',
    'groq.com', 'console.groq.com', 'openai.com',
    'anthropic.com', 'huggingface.co', 'discord.com',
    'instagram.com', 'facebook.com', 'whatsapp.com',
    'tiktok.com', 'microsoft.com', 'apple.com',
    'amazon.com', 'netflix.com', 'spotify.com', 'twitch.tv'
]


class ShieldProtector:

    def __init__(self):
        self.blocked_count = 0
        self.allowed_count = 0

    def is_safe_url(self, url: str) -> dict:
        try:
            parsed = urlparse(url)

            if not parsed.scheme or not parsed.netloc:
                return {'safe': False, 'reason': 'رابط غير صالح'}

            domain = parsed.netloc.lower()
            if self._is_suspicious_domain(domain):
                self.blocked_count += 1
                return {'safe': False, 'reason': f'النطاق {domain} مشبوه'}

            path = parsed.path.lower()
            if self._is_dangerous_file(path):
                self.blocked_count += 1
                return {'safe': False, 'reason': 'ملف تنفيذي خبيث'}

            if self._has_suspicious_params(url):
                return {'safe': False, 'reason': 'معلمات مشبوهة'}

            base_domain = '.'.join(domain.split('.')[-2:])
            if base_domain in SAFE_DOMAINS:
                self.allowed_count += 1
                return {'safe': True, 'reason': 'نطاق موثوق'}

            safety_check = self._quick_safety_check(domain)
            if not safety_check['safe']:
                self.blocked_count += 1
                return safety_check

            self.allowed_count += 1
            return {'safe': True, 'reason': 'اجتاز الفحص'}
        except Exception as e:
            return {'safe': False, 'reason': f'خطأ: {str(e)}'}

    def _is_suspicious_domain(self, domain: str) -> bool:
        suspicious = [
            r'g[o0]{2,}gle', r'faceb[o0]{2,}k', r'y[o0]{2,}tube',
            r'paypa[l1]', r'amaz[o0]n', r'[o0]utl[o0]{2}k'
        ]
        for p in suspicious:
            if re.search(p, domain, re.IGNORECASE):
                return True
        if sum(c.isdigit() for c in domain) > len(domain) * 0.4:
            return True
        return False

    def _is_dangerous_file(self, path: str) -> bool:
        for ext in DANGEROUS_EXTENSIONS:
            if path.endswith(ext) or ext + '?' in path:
                return True
        return False

    def _has_suspicious_params(self, url: str) -> bool:
        params = [
            'steal=', 'hack=', 'phish=', 'malware=', 'exploit=',
            'credential=', 'password='
        ]
        for p in params:
            if p in url.lower():
                return True
        return False

    def _quick_safety_check(self, domain: str) -> dict:
        ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        if re.match(ip_pattern, domain):
            return {'safe': False, 'reason': 'IP مباشر مشبوه'}
        if len(domain) < 4:
            return {'safe': False, 'reason': 'نطاق قصير مشبوه'}
        return {'safe': True, 'reason': 'اجتاز الفحص'}

    def sanitize_url(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            clean_params = []
            tracking = ['utm_', 'fbclid', 'gclid', 'ref', 'source']
            if parsed.query:
                for param in parsed.query.split('&'):
                    name = param.split('=')[0].lower()
                    if not any(name.startswith(t) for t in tracking):
                        clean_params.append(param)
            clean_query = '&'.join(clean_params) if clean_params else ''
            return parsed._replace(query=clean_query).geturl()
        except Exception:
            return url

    def get_stats(self) -> dict:
        return {
            'blocked': self.blocked_count,
            'allowed': self.allowed_count,
            'total': self.blocked_count + self.allowed_count
        }
