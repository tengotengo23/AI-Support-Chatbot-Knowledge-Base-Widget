"""Visitor-facing texts (Georgian / English / Russian) and simple language detection."""

from __future__ import annotations

LANGUAGES = ("ka", "en", "ru")

STRINGS: dict[str, dict[str, str]] = {
    "ka": {
        "welcome": "გამარჯობა! 👋 რით შემიძლია დაგეხმაროთ?",
        "placeholder": "დაწერეთ შეკითხვა...",
        "send": "გაგზავნა",
        "talk_to_human": "ოპერატორთან დაკავშირება",
        "leave_contact": "კონტაქტის დატოვება",
        "handoff_started": "თქვენი შეკითხვა გადაეცა ოპერატორს. პასუხს აქვე მიიღებთ.",
        "handoff_unavailable": "ოპერატორი ამჟამად მიუწვდომელია. დაგვიტოვეთ კონტაქტი და დაგიკავშირდებით.",
        "handoff_back_to_bot": "ოპერატორმა საუბარი დაასრულა. კითხვების შემთხვევაში ისევ აქ ვარ.",
        "no_answer": "სამწუხაროდ, ამ კითხვაზე ზუსტი პასუხი არ მაქვს. გსურთ ოპერატორთან დაკავშირება ან კონტაქტის დატოვება?",
        "quota_exceeded": "ასისტენტი დროებით მიუწვდომელია. დაგვიტოვეთ კონტაქტი და დაგიკავშირდებით.",
        "greeting_reply": "გამარჯობა! რით შემიძლია დაგეხმაროთ?",
        "thanks_reply": "არაფრის! სხვა კითხვა თუ გაქვთ, მომწერეთ.",
        "name": "სახელი",
        "phone": "ტელეფონი",
        "email": "ელ-ფოსტა",
        "note": "შეტყობინება",
        "submit": "გაგზავნა",
        "lead_thanks": "მადლობა! მალე დაგიკავშირდებით.",
        "lead_invalid": "გთხოვთ, მიუთითოთ ტელეფონი ან ელ-ფოსტა.",
        "operator": "ოპერატორი",
        "error": "დაფიქსირდა შეცდომა. სცადეთ თავიდან.",
        "sources": "წყარო",
        "close": "დახურვა",
        "open_chat": "ჩატის გახსნა",
        "powered_by": "Powered by",
    },
    "en": {
        "welcome": "Hi! 👋 How can I help you today?",
        "placeholder": "Type your question...",
        "send": "Send",
        "talk_to_human": "Talk to a human",
        "leave_contact": "Leave your contact",
        "handoff_started": "Your question was sent to our team. You will get the reply right here.",
        "handoff_unavailable": "Our team is not available right now. Leave your contact and we will get back to you.",
        "handoff_back_to_bot": "The operator has closed the chat. I'm here if you have more questions.",
        "no_answer": "Sorry, I don't have an exact answer to that. Would you like to talk to a human or leave your contact?",
        "quota_exceeded": "The assistant is temporarily unavailable. Leave your contact and we will get back to you.",
        "greeting_reply": "Hi! How can I help you?",
        "thanks_reply": "You're welcome! Let me know if you have any other questions.",
        "name": "Name",
        "phone": "Phone",
        "email": "Email",
        "note": "Message",
        "submit": "Send",
        "lead_thanks": "Thank you! We will contact you soon.",
        "lead_invalid": "Please enter a phone number or an email.",
        "operator": "Operator",
        "error": "Something went wrong. Please try again.",
        "sources": "Source",
        "close": "Close",
        "open_chat": "Open chat",
        "powered_by": "Powered by",
    },
    "ru": {
        "welcome": "Здравствуйте! 👋 Чем могу помочь?",
        "placeholder": "Напишите вопрос...",
        "send": "Отправить",
        "talk_to_human": "Связаться с оператором",
        "leave_contact": "Оставить контакт",
        "handoff_started": "Ваш вопрос передан оператору. Ответ придёт сюда.",
        "handoff_unavailable": "Оператор сейчас недоступен. Оставьте контакт, и мы с вами свяжемся.",
        "handoff_back_to_bot": "Оператор завершил чат. Если появятся вопросы — я здесь.",
        "no_answer": "К сожалению, у меня нет точного ответа на этот вопрос. Хотите связаться с оператором или оставить контакт?",
        "quota_exceeded": "Ассистент временно недоступен. Оставьте контакт, и мы с вами свяжемся.",
        "greeting_reply": "Здравствуйте! Чем могу помочь?",
        "thanks_reply": "Пожалуйста! Если будут ещё вопросы — пишите.",
        "name": "Имя",
        "phone": "Телефон",
        "email": "Email",
        "note": "Сообщение",
        "submit": "Отправить",
        "lead_thanks": "Спасибо! Мы скоро с вами свяжемся.",
        "lead_invalid": "Пожалуйста, укажите телефон или email.",
        "operator": "Оператор",
        "error": "Произошла ошибка. Попробуйте ещё раз.",
        "sources": "Источник",
        "close": "Закрыть",
        "open_chat": "Открыть чат",
        "powered_by": "Powered by",
    },
}

GREETINGS = {
    "გამარჯობა", "გაგიმარჯოს", "სალამი", "hello", "hi", "hey", "привет", "здравствуйте",
    "добрый день", "good morning", "დილა მშვიდობისა",
}
THANKS = {"მადლობა", "გმადლობთ", "მადლობთ", "thanks", "thank you", "thx", "спасибо", "благодарю"}


def normalize_lang(lang: str | None, default: str = "ka") -> str:
    lang = (lang or "").lower()[:2]
    return lang if lang in LANGUAGES else default


def t(lang: str, key: str) -> str:
    return STRINGS.get(lang, STRINGS["en"]).get(key) or STRINGS["en"][key]


def detect_language(text: str, fallback: str = "ka") -> str:
    """Script-based detection: Georgian (Mkhedruli/Mtavruli), Cyrillic or Latin."""
    ka = ru = en = 0
    for ch in text:
        code = ord(ch)
        if 0x10A0 <= code <= 0x10FF or 0x1C90 <= code <= 0x1CBF or 0x2D00 <= code <= 0x2D2F:
            ka += 1
        elif 0x0400 <= code <= 0x04FF:
            ru += 1
        elif ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            en += 1
    best = max(ka, ru, en)
    if best == 0:
        return fallback
    if best == ka:
        return "ka"
    if best == ru:
        return "ru"
    return "en"


def small_talk_kind(text: str) -> str | None:
    cleaned = "".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).strip()
    if not cleaned or len(cleaned) > 40:
        return None
    if cleaned in GREETINGS:
        return "greeting"
    if cleaned in THANKS or any(cleaned.startswith(t_) for t_ in THANKS):
        return "thanks"
    return None
