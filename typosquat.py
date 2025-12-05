import Levenshtein
import re

# Бренды, которые часто подделывают (Белый список)

PROTECTED_DOMAINS = [
    "vk.com",
    "telegram.org",
    "t.me",
    "sberbank.ru",
    "gosuslugi.ru",
    "ozon.ru",
    "avito.ru",
    "wildberries.ru",
    "binance.com",
    "steamcommunity.com",
    "github.com"
]

def check_typosquatting(text):
    """
    Возвращает (True, оригинал), если найдена подделка.
    Возвращает (False, None), если все чисто.
    """
    
    # 1. Вытаскиваем все ссылки из текста регуляркой
    # Ищем все, что похоже на domain.zone
    found_urls = re.findall(r'(?:https?://)?(?:www\.)?([\w-]+\.[\w.-]+)', text.lower())
    
    if not found_urls:
        return False, None

    for domain in found_urls:
        # Очищаем домен от мусора (если вдруг попало что-то лишнее)
        clean_domain = domain.split('/')[0] 
        
        # Сравниваем найденный домен с каждым из нашего Белого списка
        for real_brand in PROTECTED_DOMAINS:
            
            # Если домен точь-в-точь совпадает с оригиналом - это ОК (мы не баним сбербанк)
            if clean_domain == real_brand:
                continue 
            
            # СЧИТАЕМ РАССТОЯНИЕ
            dist = Levenshtein.distance(clean_domain, real_brand)
            
            # --- ЛОГИКА ДЕТЕКЦИИ ---
            # Если отличие всего в 1 или 2 символах...
            # ИЛИ если домен содержит имя бренда (например sberbank-support.ru)
            if dist > 0 and dist <= 2:
                print(f"⚠️ Найден клон: {clean_domain} (косит под {real_brand}, dist={dist})")
                return True, real_brand
            
            # Доп. проверка: если бренд входит в название домена, но это не сам бренд
            # Пример: sberbank-bonus.ru (тут Levenshtein будет большим, но это все равно фишинг)
            if real_brand.split('.')[0] in clean_domain and clean_domain != real_brand:
                 print(f"⚠️ Найден фишинг по вхождению: {clean_domain}")
                 return True, real_brand

    return False, None