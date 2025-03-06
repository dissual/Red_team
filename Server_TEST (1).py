from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import requests
import base64
import io
import json
import pandas as pd
from typing import Optional

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

app = FastAPI()

# Путь к базе данных SQLite
DATABASE = 'Users.db'

# Загрузка базы данных из CSV
df = pd.read_csv("plants_watering.csv", names=[
    "scientific_name", "common_name", "family", "watering_frequency",
    "notes", "toxicity", "repotting", "light_requirements", "health"
], header=None)

# Подключение к базе данных PostgreSQL
db_pool: asyncpg.Pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(
        database="postgres",
        user="postgres",
        password="1234",
        host="localhost",
        port="5432",
        min_size=1,
        max_size=10
    )
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT(20) NOT NULL,
                first_name TEXT(20) NOT NULL,
                last_name TEXT(20) NOT NULL,
                phone TEXT(15),
                email TEXT(50),
                favorites TEXT(100)
            )
        ''')
        await db.commit()

@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()

def image_to_base64(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

def get_description_from_external_source(scientific_name):
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

def extract_plant_description(plant_data):
    try:
        if not plant_data.get("suggestions"):
            return "Описание недоступно"
        first_suggestion = plant_data["suggestions"][0]
        plant_name = first_suggestion.get("plant_details", {}).get("scientific_name", "")
        return (
            first_suggestion.get("plant_details", {}).get("description")
            or get_description_from_external_source(plant_name)
            or "Описание отсутствует"
        )
    except Exception as e:
        print(f"Ошибка получения описания: {e}")
        return "Не удалось получить описание"

def get_plant_info(image_base64):
    api_key = "dJnePWJr2JzgMp8MYYqnl9nHDnZAdbNVwoySY89M6mfdqC6D0z"
    url = "https://api.plant.id/v2/identify"
    data = {
        "images": [image_base64],
        "modifiers": ["crops_fast"],
        "plant_language": "ru",
        "upload_images": True
    }
    headers = {
        "Content-Type": "application/json",
        "Api-Key": api_key
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()

def get_watering_info(plant_data):
    if "suggestions" in plant_data and len(plant_data["suggestions"]) > 0:
        plant = plant_data["suggestions"][0]
        scientific_name = plant.get("plant_details", {}).get("scientific_name", "")
        genus = ""
        if scientific_name:
            parts = scientific_name.split()
            if len(parts) >= 1:
                genus = parts[0].capitalize()
        plant_name = plant.get("plant_name", "")
        common_name_from_api = ""
        if isinstance(plant_name, dict):
            common_name_from_api = plant_name.get("common", "")
        elif isinstance(plant_name, str):
            common_name_from_api = plant_name
        row = df[
            (df["scientific_name"] == scientific_name) |
            (df["common_name"] == common_name_from_api)
        ]
        if not row.empty:
            common_name = row.iloc[0]["common_name"]
            description = extract_plant_description(plant_data)
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
        else:
            row = df[df["scientific_name"].str.startswith(genus)]
            if not row.empty:
                common_name = row.iloc[0]["common_name"]
                description = extract_plant_description(plant_data)
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
            else:
                family = plant.get("plant_family", "")
                row = df[df["family"] == family]
                if not row.empty:
                    common_name = row.iloc[0]["common_name"]
                    description = extract_plant_description(plant_data)
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
    return None

@app.post("/upload-plant/")
async def upload_plant(file: UploadFile = File(...), user_id: Optional[int] = None):
    try:
        contents = await file.read()
        image_base64 = image_to_base64(contents)
        plant_response = get_plant_info(image_base64)

        if plant_response:
            watering_info = get_watering_info(plant_response)
            if watering_info:
                async with aiosqlite.connect(DATABASE) as db:
                    await db.execute('''
                        UPDATE users
                        SET favorites = favorites || ?
                        WHERE id = ?
                    ''', (f",{watering_info['name']}", user_id))
                    await db.commit()

                return JSONResponse(content={
                    "message": "Цветок успешно добавлен в избранное",
                    "plant_info": watering_info
                })
            else:
                return JSONResponse(content={"error": "Информация о растении не найдена"}, status_code=404)
        else:
            return JSONResponse(content={"error": "Ошибка запроса к API"}, status_code=500)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {e}")

# Запуск асинхронного цикла
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
