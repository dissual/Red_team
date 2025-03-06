import aiosqlite
import asyncio

# Путь к базе данных
DATABASE = 'Users.db'

# Функция для создания таблицы
async def create_table():
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

# Функция для добавления пользователя
async def add_user(username, first_name, last_name, phone, email, favorites):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('''
            INSERT INTO users (username, first_name, last_name, phone, email, favorites)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, first_name, last_name, phone, email, favorites))
        await db.commit()

# Функция для получения всех пользователей
async def get_all_users():
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute('SELECT * FROM users') as cursor:
            return await cursor.fetchall()

# Функция для поиска пользователя по имени
async def find_user_by_name(first_name):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute('SELECT * FROM users WHERE first_name = ?', (first_name,)) as cursor:
            return await cursor.fetchall()

# Функция для удаления пользователя по ID
async def delete_user_by_id(user_id):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('DELETE FROM users WHERE id = ?', (user_id,))
        await db.commit()

# Функция для обновления данных пользователя
async def update_user(user_id, username, first_name, last_name, phone, email, favorites):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('''
            UPDATE users
            SET username = ?, first_name = ?, last_name = ?, phone = ?, email = ?, favorites = ?
            WHERE id = ?
        ''', (username, first_name, last_name, phone, email, favorites, user_id))
        await db.commit()

# Основная функция для взаимодействия с пользователем через консоль
async def main():
    await create_table()

    while True:
        print("\n1. Добавить пользователя")
        print("2. Показать всех пользователей")
        print("3. Найти пользователя по имени")
        print("4. Удалить пользователя по ID")
        print("5. Обновить данные пользователя")
        print("6. Выйти")
        choice = input("Выберите действие: ")

        if choice == '1':
            username = input("Ник пользователя: ")
            first_name = input("Имя: ")
            last_name = input("Фамилия: ")
            phone = input("Телефон: ")
            email = input("Email: ")
            favorites = input("Избранное: ")
            await add_user(username, first_name, last_name, phone, email, favorites)
            print("Пользователь добавлен!")

        elif choice == '2':
            users = await get_all_users()
            for user in users:
                print(user)

        elif choice == '3':
            first_name = input("Введите имя для поиска: ")
            users = await find_user_by_name(first_name)
            for user in users:
                print(user)

        elif choice == '4':
            user_id = input("Введите ID пользователя для удаления: ")
            await delete_user_by_id(int(user_id))
            print("Пользователь удален!")

        elif choice == '5':
            user_id = input("Введите ID пользователя для обновления: ")
            username = input("Новый ник пользователя: ")
            first_name = input("Новое имя: ")
            last_name = input("Новая фамилия: ")
            phone = input("Новый телефон: ")
            email = input("Новый email: ")
            favorites = input("Новое избранное: ")
            await update_user(int(user_id), username, first_name, last_name, phone, email, favorites)
            print("Данные пользователя обновлены!")

        elif choice == '6':
            break

        else:
            print("Неверный выбор, попробуйте снова.")

# Запуск асинхронного цикла
if __name__ == '__main__':
    asyncio.run(main())