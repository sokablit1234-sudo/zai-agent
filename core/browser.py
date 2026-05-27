import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from core.protector import ShieldProtector


class SafeBrowser:

    def __init__(self, protector: ShieldProtector):
        self.protector = protector
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.session.timeout = 15

    def search(self, query: str, num_results: int = 5) -> str:
        try:
            if self._is_dangerous_query(query):
                return "لا يمكنني البحث عن هذا الموضوع لأسباب أمنية."

            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            results = []

            for result in soup.find_all('div', class_='result')[:num_results]:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')

                    if not self.protector.is_safe_url(link)['safe']:
                        continue

                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    results.append(f"{title}\n{link}\n{snippet}\n")

            if not results:
                return self._fallback_search(query)

            return f"نتائج البحث عن \"{query}\":\n\n" + "\n".join(results)

        except requests.Timeout:
            return "انتهت مهلة البحث. حاول مرة أخرى."
        except Exception as e:
            return f"خطأ في البحث: {str(e)}"

    def _fallback_search(self, query: str) -> str:
        try:
            url = f"https://www.google.com/search?q={quote_plus(query)}&num=5"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')

            results = []
            for g in soup.find_all('div', class_='g')[:5]:
                title_elem = g.find('h3')
                link_elem = g.find('a')

                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    link = link_elem.get('href', '')

                    if '/url?q=' in link:
                        link = link.split('/url?q=')[1].split('&')[0]

                    if not self.protector.is_safe_url(link)['safe']:
                        continue

                    results.append(f"{title}\n{link}\n")

            if results:
                return f"نتائج البحث عن \"{query}\":\n\n" + "\n".join(results)
            return "لم يتم العثور على نتائج."
        except Exception:
            return "لم أتمكن من البحث حالياً. حاول لاحقاً."

    def get_webpage_content(self, url: str, max_chars: int = 3000) -> str:
        try:
            safety = self.protector.is_safe_url(url)
            if not safety['safe']:
                return f"تم حظر هذا الرابط: {safety['reason']}"

            url = self.protector.sanitize_url(url)
            response = self.session.get(url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator=' ', strip=True)

            if len(text) > max_chars:
                text = text[:max_chars] + "\n\n... (محتوى مختصر)"

            return f"محتوى الصفحة:\n\n{text}"

        except requests.Timeout:
            return "انتهت مهلة تحميل الصفحة."
        except Exception as e:
            return f"خطأ في تحميل الصفحة: {str(e)}"

    def search_youtube(self, query: str, num_results: int = 5) -> str:
        try:
            if self._is_dangerous_query(query):
                return "لا يمكنني البحث عن هذا الموضوع."

            url = f"https://html.duckduckgo.com/html/?q={quote_plus('youtube ' + query)}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            results = []

            for result in soup.find_all('div', class_='result')[:num_results]:
                title_elem = result.find('a', class_='result__a')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')
                    safety = self.protector.is_safe_url(link)
                    if safety['safe'] and 'youtube.com' in link:
                        results.append(f"{title}\n{link}\n")

            if results:
                return f"نتائج يوتيوب عن \"{query}\":\n\n" + "\n".join(results)
            return "لم يتم العثور على نتائج في يوتيوب."
        except Exception as e:
            return f"خطأ في البحث في يوتيوب: {str(e)}"

    def search_github(self, query: str, num_results: int = 5) -> str:
        try:
            url = f"https://github.com/search?q={quote_plus(query)}&type=repositories"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            seen = set()

            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith('/') and href.count('/') >= 2 and href not in seen:
                    if '/search?' not in href and len(href) < 80:
                        seen.add(href)
                        link = f"https://github.com{href}"
                        if self.protector.is_safe_url(link)['safe']:
                            results.append(f"{href[1:]}\n{link}\n")

            results = results[:num_results]

            if results:
                return f"نتائج غيت هوب عن \"{query}\":\n\n" + "\n".join(results)
            return "لم يتم العثور على نتائج في غيت هوب."
        except Exception as e:
            return f"خطأ في البحث في غيت هوب: {str(e)}"

    def get_latest_news(self, topic: str = "technology") -> str:
        return self.search(f"{topic} latest news today 2025", num_results=7)

    def _is_dangerous_query(self, query: str) -> bool:
        bad = [
            'how to hack', 'exploit download', 'malware download',
            'dark web', 'buy drugs', 'illegal', 'weapon', 'bomb making'
        ]
        query_lower = query.lower()
        return any(k in query_lower for k in bad)
