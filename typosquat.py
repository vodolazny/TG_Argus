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
    
    # Вытаскиваем все ссылки из текста регуляркой
    found_urls = re.findall(r'(?:https?://)?(?:www\.)?([\w-]+\.[\w.-]+)', text.lower())
    
    if not found_urls:
        return False, None

    for domain in found_urls:
        # Очищаем домен от мусора 
        clean_domain = domain.split('/')[0] 
        
        # Сравниваем найденный домен с каждым из нашего Белого списка
        for real_brand in PROTECTED_DOMAINS:
            
            # Если домен совпадает с оригиналом - это ОК 
            if clean_domain == real_brand:
                continue 
            
            dist = Levenshtein.distance(clean_domain, real_brand)
            
            # Если отличие всего в 1 или 2 символах...
            if dist > 0 and dist <= 2:
                print(f"⚠️ Найден клон: {clean_domain} (косит под {real_brand}, dist={dist})")
                return True, real_brand
            
            # если бренд входит в название домена, но это не сам бренд
            if real_brand.split('.')[0] in clean_domain and clean_domain != real_brand:
                 print(f"⚠️ Найден фишинг по вхождению: {clean_domain}")
                 return True, real_brand

    return False, None
