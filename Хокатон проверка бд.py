import asyncio
import asyncpg

# Подключение к базе данных
async def connect_to_db():
    try:
        conn = await asyncpg.connect(
            database="postgres",  # Имя вашей базы данных
            user="postgres",          # Имя пользователя
            password="1234",      # Пароль
            host="localhost",              # Хост (обычно localhost)
            port="5432"                   # Порт (по умолчанию 5432)
        )
        return conn
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return None

# Создание таблицы Users
async def create_table(conn):
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                UserID SERIAL PRIMARY KEY,
                Username VARCHAR(20) NOT NULL,
                FirstName VARCHAR(20) NOT NULL,
                LastName VARCHAR(20) NOT NULL,
                PhoneNumber VARCHAR(15) UNIQUE,
                Email VARCHAR(50) UNIQUE NOT NULL,
                Favorites VARCHAR(100)
            );
        """)
        print("Таблица Users создана или уже существует.")
    except Exception as e:
        print(f"Ошибка при создании таблицы: {e}")

# Добавление пользователя
async def add_user(conn):
    username = input("Введите ник пользователя: ")
    first_name = input("Введите имя: ")
    last_name = input("Введите фамилию: ")
    phone_number = input("Введите номер телефона: ")
    email = input("Введите email: ")
    favorites = input("Введите избранное: ")

    try:
        await conn.execute("""
            INSERT INTO Users (Username, FirstName, LastName, PhoneNumber, Email, Favorites)
            VALUES ($1, $2, $3, $4, $5, $6);
        """, username, first_name, last_name, phone_number, email, favorites)
        print("Пользователь успешно добавлен.")
    except Exception as e:
        print(f"Ошибка при добавлении пользователя: {e}")

# Просмотр всех пользователей
async def view_users(conn):
    try:
        users = await conn.fetch("SELECT * FROM Users;")
        if users:
            print("\nСписок пользователей:")
            for user in users:
                print(user)
        else:
            print("Пользователи не найдены.")
    except Exception as e:
        print(f"Ошибка при получении пользователей: {e}")

# Обновление пользователя
async def update_user(conn):
    user_id = input("Введите ID пользователя для обновления: ")
    favorites = input("Введите новое значение для избранного: ")

    try:
        await conn.execute("""
            UPDATE Users
            SET Favorites = $1
            WHERE UserID = $2;
        """, favorites, user_id)
        print("Пользователь успешно обновлен.")
    except Exception as e:
        print(f"Ошибка при обновлении пользователя: {e}")

# Удаление пользователя
async def delete_user(conn):
    user_id = input("Введите ID пользователя для удаления: ")

    try:
        await conn.execute("""
            DELETE FROM Users
            WHERE UserID = $1;
        """, user_id)
        print("Пользователь успешно удален.")
    except Exception as e:
        print(f"Ошибка при удалении пользователя: {e}")

# Основное меню
async def main():
    conn = await connect_to_db()
    if not conn:
        return

    await create_table(conn)

    while True:
        print("\nМеню:")
        print("1. Добавить пользователя")
        print("2. Просмотреть всех пользователей")
        print("3. Обновить пользователя")
        print("4. Удалить пользователя")
        print("5. Выйти")
        choice = input("Выберите действие: ")

        if choice == "1":
            await add_user(conn)
        elif choice == "2":
            await view_users(conn)
        elif choice == "3":
            await update_user(conn)
        elif choice == "4":
            await delete_user(conn)
        elif choice == "5":
            break
        else:
            print("Неверный выбор. Попробуйте снова.")

    await conn.close()
    print("Соединение с базой данных закрыто.")

# Запуск асинхронного приложения
if __name__ == "__main__":
    asyncio.run(main())