import spacy
import random
import pandas as pd 
from spacy.training.example import Example


# Настройки
CSV_FILE = "dataset.csv"
MODEL_NAME = "ru_core_news_lg"
OUTPUT_DIR = "nlp_model"


def load_data_from_csv(filename):
    """Читает CSV и превращает его в формат для spaCy"""
    df = pd.read_csv(filename)
    
    formatted_data = []
    
    # Проходим по каждой строчке файла
    for index, row in df.iterrows():
        text = row['text']
        label = row['label']
        
        # Если в label стоит 1 - это атака.
        if label == 1 or label == "scam" or label == "spam":
            cats = {"SCAM": 1, "HAM": 0}
        else:
            cats = {"SCAM": 0, "HAM": 1}
            
        # Добавляем в общий список
        formatted_data.append((str(text), {"cats": cats}))
        
    return formatted_data


# Загружаем и готовим данные
print(f"Читаю файл {CSV_FILE}...")
try:
    TRAIN_DATA = load_data_from_csv(CSV_FILE)
    print(f"Загружено {len(TRAIN_DATA)} примеров.")
except FileNotFoundError:
    print(f"[ОШИБКА]: Файл {CSV_FILE} не найден рядом со скриптом!")
    exit()

# Загружаем spaCy
nlp = spacy.load(MODEL_NAME)

# Настройка пайплайна 
if "textcat" not in nlp.pipe_names:
    textcat = nlp.add_pipe("textcat", last=True)
else:
    textcat = nlp.get_pipe("textcat")

textcat.add_label("SCAM")
textcat.add_label("HAM")

# Обучение
other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "textcat"]
with nlp.disable_pipes(*other_pipes):
    optimizer = nlp.begin_training()
    
    print("Начинаю обучение...")
    for i in range(7): # эпохи
        random.shuffle(TRAIN_DATA)
        losses = {}
        
        for batch in spacy.util.minibatch(TRAIN_DATA, size=8):
            texts, annotations = zip(*batch)
            
            examples = []
            for text, annot in zip(texts, annotations):
                doc = nlp.make_doc(text)
                examples.append(Example.from_dict(doc, annot))
            
            nlp.update(examples, drop=0.2, losses=losses, sgd=optimizer)
            
        print(f"Эпоха {i+1}, Потери (Loss): {losses['textcat']:.4f}")

# Сохранение
nlp.to_disk(OUTPUT_DIR)
print(f"Готово! Модель сохранена в папку '{OUTPUT_DIR}'")