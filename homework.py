import logging
import os
import time

import requests
from dotenv import load_dotenv
from telegram import Bot  # error

# from telegram.ext import CommandHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """проверяет доступность переменных окружения,
     которые необходимы для работы программы
     """
    list = ['PRACTICUM_TOKEN', 'TOKEN', 'ID']
    for x in list:
        if os.getenv(x) is None:
            return False
    return True


def send_message(bot, message):
    """отправляет сообщение в Telegram чат"""
    logging.DEBUG('Успешная отправка сообщения')
    try:
        return bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except TypeError as e:
        logging.ERROR(f'Ошибка сообщения {e}')


def get_api_answer(timestamp):
    """делает запрос к единственному эндпоинту API-сервиса"""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS,
            params={'from_date': 1667834674})
    except requests.RequestException as e:
        logging.CRITICAL(f'При обработке возникла не однозначная ситуация{e}')

    if response.status_code != 200:
        assert logging.DEBUG("Отсутствует переменная(-ные) окружения")

    if response is not None:
        return response.json()
    else:
        return 0


def check_response(response):
    """проверяет ответ API на соответствие документации"""
    try:
        response['homeworks'][0]
    except AssertionError as e:
        logging.ERROR(f'Нет нужной работы {e}')

    return response['homeworks'][0]


def parse_status(homework):
    """извлекает из информации о конкретной
    домашней работе статус этой работы
    """
    response = homework['status']
    if response not in HOMEWORK_VERDICTS:
        assert logging.DEBUG(
            'Пустой или незнакомый статус домашней работы')
    try:
        homework_name = homework['homework_name']
    except Exception as e:
        logging.DEBUG(f'Нет имени домашней работы {e}')
    verdict = HOMEWORK_VERDICTS[response]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        return logging.CRITICAL("Отсутствует переменная(-ные) окружения")
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            api = get_api_answer(timestamp)
            homework = check_response(api)
            message = parse_status(homework)
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            bot.close()


if __name__ == '__main__':
    main()
