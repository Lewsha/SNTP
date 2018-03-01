import socket
import struct
from datetime import datetime
import select


TIME1970 = 2208988800  # Колиество секунд с 01.01.1900 (начало отсчета в NTP) по 01.01.1970 (начало UNIX-времени)


class SNTPPacket:
    def __init__(self, data, timestamp, originate_timestamp):
        """Определяем поля. Те, которые можем заполнить сразу, заполняем сразу"""
        self.packet = None  # Это наш будущий пекет
        self.delay = self.read_delay()  # Это наша задержка, на которую мы врем
        self.data = data  # Здесь принятый пакет в байтах
        """В flags находятся 3 флага, которые вместе занимают байт
        Это: LI - флаг добавления/удаления секунды,
        VN - флаг версии протокола,
        mode - флаг режима (поскольку сервер, то и флаг выставляется в 4, т.е. сервер)
        Из всех этих флагов нас в запросе пользователя будет интересовать лишь VN (он копируется оттуда).
        Не забываем к времени прибавить, где нужно, TIME1970"""
        self.flags = None
        self.stratum = 0x02  # Слой (уровень) нашего сервера (1 - первичный сервер, 2 - вторичный)
        self.poll_interval = data[2]   # Интервал между сообщениями от сервера копируется из запроса клиента
        self.precision = -0x5   # Точность устанавливается как -ln от значащих бит сервера справа от запятой
        self.ROOT_DELAY = 0.0  # Время приема-передачи (RTT)
        self.ROOT_DISPERSION = 0x00  # Номинальная ошибка
        self.reference_identifier = 2130706433  # Идентификатор эталона
        self.reference_timestamp = timestamp + TIME1970  # Время, когда наше время было установлено или поправлено
        self.originate_timestamp = originate_timestamp  # Время запроса (когда клиент отправил запрос)
        self.receive_timestamp = timestamp + self.delay + TIME1970  # Время прихода запроса на сервер
        self.transmit_timestamp = 0  # Время отправки ответа
        self.timestamp = timestamp + TIME1970  # Время, когда пользователь прислал запрос

    def packaging(self):
        """Метод для формирования ответного пакета"""
        """Если нам пришел запрос версии 3, то и ответ будет версии 3, если 4, то 4"""
        if bytes(self.data[0]) == b'\x1b':
            self.flags = 0x1c
        else:
            self.flags = 0x24

        """Если клиент отправил серверу свое время, то мы сможем вычислить задержку"""
        if self.originate_timestamp != 0:
            self.ROOT_DELAY = (self.timestamp - self.originate_timestamp) * 2
        """Если не отправил, то мы время отправления установим сами искусственно
        (просто так, этого можно было и не делать)"""
        if self.originate_timestamp == 0:
            self.originate_timestamp = int(timestamp)
        """Определение времени отправки специально засунул поближе к упаковке"""
        self.transmit_timestamp = datetime.timestamp(datetime.utcnow()) + self.delay + TIME1970

        """Теперь у нас все данные определены, и мы можем их запаковать"""
        self.packet = struct.pack("!BBBbhh10I",
                                  self.flags, self.stratum, self.poll_interval, self.precision,
                                  self.to_integer(self.ROOT_DELAY),
                                  self.to_fractional(self.ROOT_DELAY, 16),
                                  self.ROOT_DISPERSION,
                                  self.reference_identifier,
                                  self.to_integer(self.reference_timestamp),
                                  self.to_fractional(self.reference_timestamp),
                                  self.to_integer(self.originate_timestamp),
                                  self.to_fractional(self.originate_timestamp),
                                  self.to_integer(self.receive_timestamp),
                                  self.to_fractional(self.receive_timestamp),
                                  self.to_integer(self.transmit_timestamp),
                                  self.to_fractional(self.receive_timestamp))
        return self.packet

    @staticmethod
    def to_integer(t_stamp):
        return int(t_stamp)

    @staticmethod
    def to_fractional(t_stamp, n=32):
        return int((t_stamp - int(t_stamp)) * 2**n)

    @staticmethod
    def read_delay():
        with open("configs.txt", encoding='utf-8', mode='r') as file:
            try:
                configs = file.read()
                configs = configs.split('\n')
                for string in configs:
                    if 'DELAY = ' in string:
                        delay = string.split()
                        delay = int(delay[2])
            except Exception as error:
                print(error.args)
                return 0
        return delay


if __name__ == "__main__":
    serv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    connections = [serv]
    serv.bind(("127.0.0.1", 123))
    serv.setblocking(0)
    value = True
    while value:
        read, write, error = select.select(connections, [], [])
        for sock in read:
            print(sock)
            if sock == serv:
                data, address = serv.recvfrom(1024)
                print("Connection from {} accepted.".format(address))
                timestamp = datetime.timestamp(datetime.utcnow())
                unpack_data = struct.unpack("!12I", data)
                originate_timestamp = unpack_data[10] + unpack_data[11] * 2**32
                packet = SNTPPacket(data, timestamp, originate_timestamp)
                reply = packet.packaging()
                serv.sendto(reply, address)

    serv.close()

