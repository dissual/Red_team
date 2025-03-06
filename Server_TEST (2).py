from fastapi import FastAPI, HTTPException, Depends
from asyncpg import Connection, Pool
import asyncio

# Настройка приложения FastAPI
app = FastAPI()

# Глобальная переменная для подключения к базе данных
db_pool: Pool = None

# Подключение к базе данных при старте приложения
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
        max_size=10  # Пул соединений
    )
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                UserID SERIAL PRIMARY KEY,
                Username VARCHAR(20) NOT NULL,
                FirstName VARCHAR(20) NOT NULL,
                LastName VARCHAR(20) NOT NULL,
                PhoneNumber VARCHAR(15) UNIQUE,
                Email VARCHAR(50) UNIQUE NOT NULL,
                Favorites VARCHAR(100)
            )
        """)

# Закрытие соединения с базой данных при завершении приложения
@app.on_event("shutdown")
async def shutdown():
    await db_pool.close()

# Маршрут для добавления нового пользователя
@app.post("/users/")
async def add_user(username: str, first_name: str, last_name: str, phone_number: str, email: str, favorites: str):
    async with db_pool.acquire() as conn:
        try:
            await conn.execute("""
                INSERT INTO Users (Username, FirstName, LastName, PhoneNumber, Email, Favorites)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, username, first_name, last_name, phone_number, email, favorites)
            return {"message": "Пользователь успешно добавлен"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка: {e}")

# Маршрут для просмотра всех пользователей
@app.get("/users/")
async def get_users():
    async with db_pool.acquire() as conn:
        users = await conn.fetch("SELECT * FROM Users")
        return [dict(user) for user in users]

# Маршрут для обновления пользователя
@app.put("/users/{user_id}")
async def update_user(user_id: int, favorites: str):
    async with db_pool.acquire() as conn:
        try:
            result = await conn.execute("""
                UPDATE Users
                SET Favorites = $1
                WHERE UserID = $2
            """, favorites, user_id)
            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="Пользователь не найден")
            return {"message": "Пользователь успешно обновлен"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка: {e}")

# Маршрут для удаления пользователя
@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    async with db_pool.acquire() as conn:
        try:
            result = await conn.execute("""
                DELETE FROM Users
                WHERE UserID = $1
            """, user_id)
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Пользователь не найден")
            return {"message": "Пользователь успешно удален"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка: {e}")
