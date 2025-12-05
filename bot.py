import os 
from telethon import TelegramClient, events, utils
from telethon.tl.functions.contacts import BlockRequest
from dotenv import load_dotenv
import spacy
from vosk import KaldiRecognizer, Model
import asyncio
import json
import subprocess
from typosquat import check_typosquatting
from file_checks import *

# Инициализация
load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
client = TelegramClient('bot', API_ID , API_HASH)

nlp = spacy.load("nlp_model")
vosk_model = Model('vosk_model')
scammers = {}

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    try:
        # NLP и важные переменные 
        text = event.text
        doc = nlp(text)
        score = doc.cats['SCAM']
        file_status = "✅ ЧИСТО"
        sender = await event.get_sender()
        sender_id = event.sender_id
        name = utils.get_display_name(sender)

        # Проверяем на тайпосквоттинг
        is_typo, target_brand = check_typosquatting(text)

        if is_typo:
            await event.forward_to('me')
            await client.send_message('me', f"🚨 **ВНИМАНИЕ! ФИШИНГ!**\nСсылка маскируется под **{target_brand}**.\nНе переходите! {name} заблокирован")
            await client(BlockRequest(sender_id))
            print(f"{name} заблокирован за фейк ссылку")
            return

        if not text and not event.voice and not event.video_note and not event.document and not event.video:
            print(f"{name}: невозможно проверить текст сообщения(скорее всего фото/стикер/GIF)")
            return 
        
        # Обрабатываем файлы
        if event.document and not event.voice and not event.video_note and not event.video:
            mime_type = event.document.mime_type
            match_status = await get_file_risk_score(event.document.attributes[0].file_name, mime_type)
            if match_status == 0:
                file_status = "✅ ЧИСТО"
            elif match_status == 2 or match_status == 1:
                analysis = await virusTotal_scan(event)
                if analysis == 2:
                    file_status = "🛑 АТАКА"
                elif analysis == 1:
                    file_status = "⚠️ ПОДОЗРИТЕЛЬНО"
            file_status = 'Статус файла: ' + file_status
            print(file_status)
        
        # Обрабатываем голосовые и видео сообщения
        if event.voice or event.video_note:
            filepath = await event.download_media()
            text = await asyncio.to_thread(process_audio, filepath)
            doc = nlp(text)
            score = doc.cats['SCAM']

        if score > 0.7:
            status = "🛑 АТАКА"
        elif score > 0.3:  
            status = "⚠️ ПОДОЗРИТЕЛЬНО"
        else:
            status = "✅ ЧИСТО"
        
        print(f"{name}:{status} ({score:.2f}): {text}")

        # Пересылаем подозрительное сообщение и выдаем предупреждение
        if status != '✅ ЧИСТО' or '✅ ЧИСТО' not in file_status:
            await event.forward_to('me')
            await client.send_message('me', f"{status} {file_status if event.media else ''}")
            
            scammers[sender_id] = scammers.get(sender_id, 0) + 1
            current_warns = scammers[sender_id]
            print(f"{name} предупреждений: {current_warns}")
            if not event.is_channel:
                if current_warns == 3:
                    await client(BlockRequest(sender_id))
                    print(f"{name} заблокирован за 3 препреждения")
            else:
                await client.send_message('me', f"Канал {name} опасен, покиньте его")

    except Exception as e:
        print(f"[ОШИБКА] {e}")


def process_audio(filepath):
    """
    Обрабатывает голосовые и видео сообщения
    """
    print(f"Обработка файла: {filepath}")
    # Команда для ffmpeg
    command = ["ffmpeg", "-loglevel", "quiet", "-i", filepath,"-ar", "16000", "-ac", "1", "-f", "s16le", "-"]
    
    try:
        # Конвертируем в подходящий формат через ffmpeg
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        
        # Инициализация распознавателя
        rec = KaldiRecognizer(vosk_model, 16000)
        result_text = ""

        while True:
    
            # Читаем аудиопоток буферами по 4кб
            data = process.stdout.read(4000)
            
            if len(data) == 0:
                break
            
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                result_text += res.get("text", "") + " "

        res = json.loads(rec.FinalResult())
        result_text += res.get("text", "")
        final_text = result_text.strip()
        
        return final_text

    except Exception as e:
        print(f"[ОШИБКА]: {e}")
        return ""
        
    finally:
        # Уборка мусора
        if os.path.exists(filepath):
            os.remove(filepath)


# Запуск 
if __name__ == "__main__":
    try:
        client.start()
        print('Бот запущен')
        client.run_until_disconnected()
    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА ЗАПУСКА]: {e}")