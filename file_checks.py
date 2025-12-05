import os
import re
import vt 
from dotenv import load_dotenv
import hashlib

load_dotenv()
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")
vt_client = vt.Client(VIRUSTOTAL_API_KEY)

async def get_file_risk_score(filename, mime_type):
    """
    Возвращает оценку риска файла:
    0 - безопасно
    1 - подозрительно (архив)
    2 - опасно (исполняемый файл или скрипт)
    """
    
    # Проверяем исполняемый в linux (elf) файл
    if mime_type == 'application/x-executable' or mime_type == 'application/x-elf':
        return 2

    filename = filename.lower().strip()
    
    # Списки расширений
    high_risk_ext = {
        '.exe', '.scr', '.bat', '.cmd', '.vbs', '.py', '.ps1', '.deb',
        '.lnk', '.com', '.msi', '.apk', '.jar', '.cpl', '.sh'
    }
    
    medium_risk_ext = {
        '.docm', '.xlsm', '.pptm', '.zip', '.rar', '.7z', '.iso'
    }

    # Проверка на двойное расширение 
    double_ext_pattern = r"\.(docx?|pdf|txt|jpg|png|xlsx?)\.[a-z0-9]{2,4}$"
    
    if re.search(double_ext_pattern, filename):
        return 2 

    # Проверка конца файла
    for ext in high_risk_ext:
        if filename.endswith(ext):
            return 2
            
    for ext in medium_risk_ext:
        if filename.endswith(ext):
            return 1
            
    return 0


async def virusTotal_scan(message):
    """
    Сканирует файл с помощью сервиса VirusTotal
    """
    try:
        file_size_bytes = message.document.size
        file_size_mb = file_size_bytes / (1024 * 1024) # Переводим в МБ
        if file_size_mb < 32: # API VirusTotal больше не позволяет
            filepath = await message.download_media()
        else:
            print("Невозможно проверить файл(слишком большой размер)")
            filepath = None
            return 1
        # Вычисляем sha256 файла для анализа сигнатуры
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        file_hash = sha256_hash.hexdigest()
        print(f"Проверяю хэш: {file_hash}")

        try:
            file_obj = await vt_client.get_object_async(f"/files/{file_hash}")
            stats = file_obj.last_analysis_stats
        except vt.error.APIError as e:
            # Если ошибка 404 (NotFoundError), значит файл еще не загружали
            if e.code == "NotFoundError":
                print("Хеш не найден, начинаю загрузку на VirusTotal...")
                with open(filepath, "rb") as f:
                    analysis = await vt_client.scan_file_async(f, wait_for_completion=True)
                stats = analysis.stats
            else:
                raise e

        print(f"{stats['malicious']} антивирусов посчитало файл {filepath} вредоносным")
        
        if stats['malicious'] >= 5:
            return 2
        
        return 1

    except Exception as e:
        print(f"[ОШИБКА VIRUSTOTAL] {e}")
        return 1

    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)