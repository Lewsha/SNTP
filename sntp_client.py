import socket
import struct
from datetime import datetime

# NTP_SERVER = "0.ru.pool.ntp.org"
NTP_SERVER = "127.0.0.1"

TIME1970 = 2208988800


def sntp_client():
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Хреначим сокет
    """48-байтный запрос клиента. Все байты занулены, кроме первого, в котором 3 поля пакета:
    LI (Leap Indicator) нам не нужен и занулен, поле VN (Version Number - номер версии) - содержит 3 и 
    самое важное - поле режим, в котором указана цифра 3, т.е. указано, что это пакет от клиента.
    В двоичном виде это 00 011 011 (пробелы поставлены для визуального разделения полей)"""
    data = '\x1b' + 47 * '\0'
    client.sendto(data.encode("utf-8"), (NTP_SERVER, 123))  # Отправляем наш запрос на 123 порт UDP сервера NTP
    data, address = client.recvfrom(1024)  # Получаем ответ
    if data:
        print('Response received from:', address)
    """Пояснение к методу unpuck. Первый параметр - fmt (формат строки). 
    В нашем конкретном случае испльзуется !, что означает "network (big-endian)", I означает тип языка C
    unsigned int, т.е. беззнаковое число, закодированное в 32 битах, а 12 означает количество таких чисел.
    Почему мы используем именно unsigned int, думаю, легко понять из формата пакета и временных меток."""
    unpack = struct.unpack("!12I", data)
    t = unpack[10] + unpack[11] / 2**32
    t -= TIME1970
    t = datetime.fromtimestamp(t)
    host_time = datetime.utcnow()
    print('\tHost time:\t', host_time)
    print("\tServer time: {}".format(t))


if __name__ == "__main__":
    sntp_client()
