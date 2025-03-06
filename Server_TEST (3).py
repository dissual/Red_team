import socket
import select

# Настройки сервера
HOST = '127.0.0.1'  # IP-адрес сервера
PORT = 8080         # Порт сервера
MAX_CLIENTS = 50    # Максимальное количество клиентов

# Создаем сокет сервера
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(MAX_CLIENTS)

print(f"HTTP-сервер запущен на {HOST}:{PORT}. Ожидание подключений...")

# Список сокетов для мониторинга
sockets_list = [server_socket]
clients = {}

def handle_client(client_socket):
    # Читаем HTTP-заголовок
    request = client_socket.recv(1024).decode('utf-8')
    print(f"Получен запрос:\n{request}")

 
        # Формируем HTTP-ответ с текстом "hallo world"
    response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            "\r\n"
            "<html><body><h1>Работает</h1></body></html>"
        )
  

    # Отправляем ответ клиенту
    client_socket.send(response.encode('utf-8'))
    client_socket.close()

while True:
    # Мониторим сокеты с помощью select
    read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

    for notified_socket in read_sockets:
        # Если новое подключение
        if notified_socket == server_socket:
            client_socket, client_address = server_socket.accept()
            print(f"Новое подключение от {client_address}")

            # Добавляем клиента в список
            sockets_list.append(client_socket)
            clients[client_socket] = client_address

            if len(sockets_list) > MAX_CLIENTS:
                print("Достигнуто максимальное количество клиентов.")
                client_socket.close()
                sockets_list.remove(client_socket)
                del clients[client_socket]
        else:
            # Обрабатываем запрос клиента
            handle_client(notified_socket)
            sockets_list.remove(notified_socket)
            del clients[notified_socket]

    # Обрабатываем исключения
    for notified_socket in exception_sockets:
        sockets_list.remove(notified_socket)
        del clients[notified_socket]