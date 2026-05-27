import re
from datetime import datetime
from groq import Groq
from core.protector import ShieldProtector
from core.browser import SafeBrowser
import config


class ZAIAgent:

    def __init__(self, groq_api_key=None, model=None):
        self.groq = Groq(api_key=groq_api_key or config.GROQ_API_KEY)
        self.model = model or config.MODEL_NAME
        self.protector = ShieldProtector()
        self.browser = SafeBrowser(self.protector)
        self.conversation_history = []
        self.max_history = 20
        self.commands_executed = 0
        self.created_at = datetime.now().isoformat()

    def _build_system_prompt(self) -> str:
        return f"""أنت {config.AGENT_NAME} - مساعد ذكي قوي ومتطور.

شخصيتك:
- مساعد ذكي سريع ودقيق
- تتكلم بالعربية بطلاقة ووضوح
- تقدم إجابات مفصلة ومنظمة
- صريح وواقعي

قدراتك:
- بحث في الإنترنت (اكتب: ابحث عن [موضوع])
- بحث في يوتيوب (اكتب: يوتيوب [موضوع])
- بحث في غيت هوب (اكتب: غيت هوب [موضوع])
- آخر الأخبار (اكتب: أخبار [موضوع])
- تصفح المواقع بأمان (اكتب: افتح [رابط])
- حماية من الروابط المشبوهة (أرسل رابط وسأفحصه)
- إحصائيات (اكتب: إحصائيات)
- مسح الذاكرة (اكتب: مسح الذاكرة)

قواعد:
- لا تختلق معلومات - إذا لم تعرف قل "لا أعلم"
- كن مهنياً وواضحاً
- التاريخ: {datetime.now().strftime('%Y-%m-%d')}
- اكتب مساعد لعرض كل الأوامر"""

    def process_message(self, user_message: str) -> str:
        self.commands_executed += 1
        user_message = user_message.strip()

        if not user_message:
            return ""

        cmd_result = self._check_commands(user_message)
        if cmd_result:
            return cmd_result

        if 'http' in user_message or '://' in user_message:
            link_result = self._handle_links(user_message)
            if link_result:
                return link_result

        self._add_to_history('user', user_message)

        try:
            response = self.groq.chat.completions.create(
                model=self.model,
                messages=self._get_messages(),
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
            )

            reply = response.choices[0].message.content
            self._add_to_history('assistant', reply)
            return reply

        except Exception as e:
            error_msg = f"خطأ في الاتصال بالنموذج: {str(e)}"
            self._add_to_history('assistant', error_msg)
            return error_msg

    def _check_commands(self, message: str) -> str:
        msg = message.lower().strip()

        if msg in ['مساعد', 'مساعدة', 'help', '/help']:
            return (
                "الأوامر المتاحة:\n\n"
                "- ابحث عن [موضوع] : بحث في الإنترنت\n"
                "- يوتيوب [موضوع] : بحث في يوتيوب\n"
                "- غيت هوب [موضوع] : بحث في غيت هوب\n"
                "- أخبار [موضوع] : آخر الأخبار\n"
                "- افتح [رابط] : تصفح صفحة ويب\n"
                "- إحصائيات : أداء الـ Agent\n"
                "- مسح الذاكرة : محادثة جديدة\n\n"
                "أو تحدث معي بشكل طبيعي!"
            )

        elif msg in ['مسح الذاكرة', 'clear']:
            self.conversation_history = []
            return "تم مسح الذاكرة. محادثة جديدة!"

        elif msg in ['إحصائيات', 'stats']:
            s = self.protector.get_stats()
            return (
                f"إحصائيات {config.AGENT_NAME}:\n\n"
                f"- وقت الإنشاء: {self.created_at}\n"
                f"- أوامر منفذة: {self.commands_executed}\n"
                f"- روابط فحصت: {s['total']}\n"
                f"- روابط حظرت: {s['blocked']}\n"
                f"- روابط مسموحة: {s['allowed']}\n"
                f"- النموذج: {self.model}"
            )

        elif msg.startswith('بحث عن') or msg.startswith('ابحث عن'):
            query = message.replace('بحث عن', '').replace('ابحث عن', '').strip()
            if query:
                return self.browser.search(query)

        elif msg.startswith('يوتيوب'):
            query = message.replace('يوتيوب', '').strip()
            if query:
                return self.browser.search_youtube(query)

        elif msg.startswith('غيت هوب') or msg.startswith('github'):
            query = message.replace('غيت هوب', '').replace('github', '').strip()
            if query:
                return self.browser.search_github(query)

        elif msg.startswith('أخبار') or msg.startswith('news'):
            topic = message.replace('أخبار', '').replace('news', '').strip()
            return self.browser.get_latest_news(topic or "technology")

        elif msg.startswith('افتح') or msg.startswith('open'):
            url = message.replace('افتح', '').replace('open', '').strip()
            if url:
                return self.browser.get_webpage_content(url)

        return None

    def _handle_links(self, message: str) -> str:
        urls = re.findall(r'https?://[^\s]+', message)
        if urls:
            url = urls[0]
            safety = self.protector.is_safe_url(url)
            if safety['safe']:
                return f"الرابط آمن ({safety['reason']})\n\n{self.browser.get_webpage_content(url)}"
            else:
                return f"تحذير: {safety['reason']}\nلا أنصحك بفتح هذا الرابط!"
        return None

    def _add_to_history(self, role: str, content: str):
        self.conversation_history.append({
            'role': role,
            'content': content
        })
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

    def _get_messages(self) -> list:
        messages = [{'role': 'system', 'content': self._build_system_prompt()}]
        for msg in self.conversation_history:
            messages.append({'role': msg['role'], 'content': msg['content']})
        return messages
