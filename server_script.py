import socket
from datetime import datetime
import os
import asyncio
import requests

from config import host, port, max_col_of_clients, HDRS, APPID, URL_BASE


# Создание объекта сервера и запуск цикла ожидания подключения и запроса от клиента
async def creating_server_and_start():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(max_col_of_clients)
    server_socket.setblocking(False)

    print("Server is availble by this link: ", f"http://{host}:{port}/index.html")

    while True:
        client, address = await loop.sock_accept(server_socket)
        loop.create_task(getting_request(client, address))


# Асинхронная обработка запроса от клиента
async def getting_request(client, address):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print("Client with address: ", address, " has been connected.")

    try:
        # Асинхронно получаем данные от подключившегося клиента
        data_new = (await loop.sock_recv(client, 1024)).decode('utf8')
        data = data_new.split(' ')[1]
        print("His data: ", data, "")
        if data:
            # Асинхронно отправляем данные подключившемуся клиенту
            await sending_data(data, client, address, current_time)
            print("File ", data, " has been sent to client: ", address, ".\n")
    except Exception as e:
        print("Error: ", e)
    finally:
        client.close()


# Для отправки данных мы просто подыскиваем необходимый файл на сервере, кодируем его в байты и отправляем
async def sending_data(data, client, address, c_time):
    try:
        folders = {
            "sitepatterns": False,
            "photos": False,
            "music": False,
            "video": False
        }

        for folder in folders.keys():
            items = os.listdir(folder)
            if data in [f"/{item}" for item in items]:
                folders[folder] = True
                break

        # Шаримся по всем файлам и отправляем необходимый
        if folders["sitepatterns"]:
            with open(f'sitepatterns{data}', 'rb') as file:
                response = HDRS.encode('utf-8') + file.read()
            await loop.sock_sendall(client, response)
        elif folders["photos"]:
            with open(f'photos{data}', 'rb') as file:
                response = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: image/jpeg\r\n\r\n"
                ).encode('utf-8') + file.read()
            await loop.sock_sendall(client, response)
        elif folders["music"]:
            with open(f'music{data}', 'rb') as file:
                response = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: audio/mp3\r\n\r\n"
                ).encode('utf-8') + file.read()
            await loop.sock_sendall(client, response)
        elif folders["video"]:
            with open(f'video{data}', 'rb') as file:
                response = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: video/mp4\r\n\r\n"
                ).encode('utf-8') + file.read()
            await loop.sock_sendall(client, response)
        else:
            raise FileNotFoundError

        time_writing(c_time, address, data)

    except FileNotFoundError:
        print(data)
        if data == "/favicon.ico":
            with open('photoforsite/favicon.ico', 'rb') as file:
                response = HDRS.encode('utf-8') + file.read()
            await loop.sock_sendall(client, response)
        elif data.split('_')[0] in ['/weather', '/forecast']:
            response = HDRS.encode('utf-8') + weather(data).encode('utf-8')
            await loop.sock_sendall(client, response)
            time_writing(c_time, address, data)
        elif data == "/all":
            responseForAll = generate_all_response()
            await loop.sock_sendall(client, HDRS.encode('utf-8') + responseForAll.encode('utf-8'))
            time_writing(c_time, address, 'all')
        else:
            with open('errors/code.html', 'rb') as file:
                response = HDRS.encode('utf-8') + file.read()
            await loop.sock_sendall(client, response)
            time_writing(c_time, address, data)


def weather(data):
    type_of, location = data.split('_')
    if type_of == '/weather':
        info = current_weather(location)
        response = (
            f"<h2>Weather in {location}</h2>"
            f"<ul>"
            f"<li><strong>Country:</strong> {info['sys']['country']}</li>"
            f"<li><strong>Temperature:</strong> {info['main']['temp']} K</li>"
            f"<li><strong>Feels like:</strong> {info['main']['feels_like']} K</li>"
            f"<li><strong>Pressure:</strong> {info['main']['pressure']} mmr</li>"
            f"</ul>"
            f'<a href="all">Нажмите сюда, чтобы вернуться в хранилище файлов.</a>'
        )
    return response


# Функция выводит все файлы, которые есть на сервере
def generate_all_response():
    response = ""
    for folder in ["photos", "sitepatterns", "music", "video"]:
        items = os.listdir(folder)
        response += f"<br><br>{folder.capitalize()}:<br>"
        for item in items:
            response += f'<a style="padding-left: 30px;" href="{item}">{item}</a><br>'
    response += '<br><br>You can also request weather information using /weather_city. <br><br> <a href="index.html">Нажмите сюда, чтобы вернуться в хранилище файлов.</a>'
    return response


# Получаем данные о погоде по API
def current_weather(q, appid=APPID):
    return requests.get(URL_BASE + "weather", params={"q": q, "appid": appid}).json()


# Даннаая функция записывает в файл list.txt логи о подключающихся клиентах
def time_writing(time, address, data):
    with open('list.txt', 'a') as file:
        log = f"Time: {time} | Address: {address} | Data: {data}\n"
        file.write(log)


loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(creating_server_and_start())
except KeyboardInterrupt:
    pass
