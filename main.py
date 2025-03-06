import requests
import pandas as pd
from PIL import Image
import json
import base64
import io
import wikipedia
from wikipedia.exceptions import PageError, DisambiguationError, WikipediaException
from IPython.display import display, Image as DisplayImage
import hashlib


class PlantIdentifier:
    """Класс для идентификации растений через Plant.id API и получения информации о них."""

    def __init__(self, api_key="dJnePWJr2JzgMp8MYYqnl9nHDnZAdbNVwoySY89M6mfdqC6D0z"):
        self.api_key = api_key
        self.url = "https://api.plant.id/v2/identify"
        self.df = None

    def load_database(self, csv_path="plants_watering.csv"):
        """Загружает базу данных растений из CSV-файла."""
        self.df = pd.read_csv(csv_path, names=[
            "scientific_name", "common_name", "family", "watering_frequency",
            "notes", "toxicity", "repotting", "light_requirements", "health"
        ], header=None)

    @staticmethod
    def image_to_base64(image_path):
        """Преобразует изображение в строку Base64."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def identify_plant(self, image_path):
        """Отправляет запрос к Plant.id API для идентификации растения."""
        image_base64 = self.image_to_base64(image_path)
        data = {
            "images": [image_base64],
            "modifiers": ["crops_fast"],
            "plant_language": "ru",
            "upload_images": True
        }
        headers = {
            "Content-Type": "application/json",
            "Api-Key": self.api_key
        }
        response = requests.post(self.url, json=data, headers=headers)
        return response.json(), image_base64


class PlantInfoExtractor:
    """Класс для извлечения информации о растении из данных API и базы данных."""

    @staticmethod
    def get_wikipedia_description(scientific_name):
        """Получает описание растения из Wikipedia."""
        try:
            wikipedia.set_lang("ru")
            page = wikipedia.page(scientific_name, auto_suggest=False)
            return page.summary[:2000] + "..."
        except PageError:
            return f"Описание для {scientific_name} не найдено в Wikipedia"
        except DisambiguationError as e:
            return f"Неоднозначный запрос: {e.options[0]}"
        except WikipediaException as e:
            return f"Ошибка Wikipedia: {str(e)}"
        except Exception as e:
            return f"Ошибка при запросе: {str(e)}"

    @staticmethod
    def extract_description(plant_data):
        """Извлекает описание из данных API или Wikipedia."""
        try:
            if not plant_data.get("suggestions"):
                return "Описание недоступно"
            first_suggestion = plant_data["suggestions"][0]
            plant_name = first_suggestion.get("plant_details", {}).get("scientific_name", "")
            return (
                    first_suggestion.get("plant_details", {}).get("description") or
                    PlantInfoExtractor.get_wikipedia_description(plant_name) or
                    "Описание отсутствует"
            )
        except Exception as e:
            print(f"Ошибка получения описания: {e}")
            return "Не удалось получить описание"

    def get_plant_info(self, plant_data, df):
        """Получает информацию о растении из данных API и базы данных."""
        if "suggestions" not in plant_data or not plant_data["suggestions"]:
            return None

        plant = plant_data["suggestions"][0]
        scientific_name = plant.get("plant_details", {}).get("scientific_name", "")
        genus = scientific_name.split()[0].capitalize() if scientific_name else ""

        plant_name = plant.get("plant_name", "")
        common_name_from_api = plant_name.get("common", "") if isinstance(plant_name, dict) else plant_name

        # Поиск по научному или общему названию
        row = df[
            (df["scientific_name"] == scientific_name) |
            (df["common_name"] == common_name_from_api)
            ]

        if not row.empty:
            return self._create_result(row, common_name_from_api, scientific_name, plant_data)

        # Поиск по роду
        row = df[df["scientific_name"].str.startswith(genus)]
        if not row.empty:
            return self._create_result(row, common_name_from_api, scientific_name, plant_data)

        # Поиск по семейству
        family = plant.get("plant_family", "")
        row = df[df["family"] == family]
        if not row.empty:
            return self._create_result(row, common_name_from_api, scientific_name, plant_data)

        return None

    def _create_result(self, row, common_name_from_api, scientific_name, plant_data):
        """Создает словарь с информацией о растении."""
        common_name = row.iloc[0]["common_name"]
        description = self.extract_description(plant_data)
        return {
            "name": common_name or common_name_from_api,
            "scientific_name": scientific_name,
            "watering": row.iloc[0]["watering_frequency"],
            "notes": row.iloc[0]["notes"],
            "toxicity": row.iloc[0]["toxicity"],
            "repotting": row.iloc[0]["repotting"],
            "light_requirements": row.iloc[0]["light_requirements"],
            "health": row.iloc[0]["health"],
            "description": description
        }


class PlantAnalyzer:
    """Класс для анализа растения и сохранения результатов."""

    @staticmethod
    def display_image(image_data, title=""):
        """Отображает изображение в IPython."""
        if isinstance(image_data, str):
            display(DisplayImage(filename=image_data, width=300))
        elif isinstance(image_data, bytes):
            display(DisplayImage(data=image_data, width=300))
        print(title)

    @staticmethod
    def save_result(result, output_path="plant_info.json"):
        """Сохраняет результат в JSON-файл."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

    def analyze(self, image_path):
        """Основной метод анализа растения."""
        identifier = PlantIdentifier()
        extractor = PlantInfoExtractor()

        # Загружаем базу данных
        identifier.load_database()

        # Идентифицируем растение
        plant_response, image_base64 = identifier.identify_plant(image_path)
        result = {}

        if plant_response:
            # Проверяем наличие предложений и вероятность
            if "suggestions" in plant_response and plant_response["suggestions"]:
                probability = plant_response["suggestions"][0].get("probability", 0)
                if probability < 0.1:  # Вероятность меньше 10%
                    result["message"] = "Это не цветок"
                else:
                    plant_info = extractor.get_plant_info(plant_response, identifier.df)
                    if plant_info:
                        result = plant_info
                        result["image_base64"] = image_base64  # Добавляем Base64 изображения
                    else:
                        result["error"] = "Информация о растении не найдена"
            else:
                result["message"] = "Это не цветок"
        else:
            result["error"] = "Ошибка запроса к API"

        # Сохраняем и выводим результат
        self.save_result(result)
        print(json.dumps(result, ensure_ascii=False, indent=4))
        return result


if __name__ == "__main__":
    analyzer = PlantAnalyzer() 
    image_path = "arts/Тесты/val/Фиалка Виттрока.jpg"
    analyzer.analyze(image_path)