import sys
import logging
import os
import json
import time

import requests
import telegram

from dotenv import load_dotenv
from http import HTTPStatus


load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=None)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger.addHandler(handler)
handler.setFormatter(formatter)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """проверяет доступность переменных окружения.
    которые необходимы для работы программы
    """
    return all([PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN])


def send_message(bot, message):
    """отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Успешная отправка сообщения')
    except Exception as error:
        logger.error(f'Ошибка отправки сообщения: {error}')


def get_api_answer(timestamp):
    """делает запрос к единственному эндпоинту API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS,
            params={'from_date': timestamp})
    except requests.RequestException as e:
        logger.critical(f'При обработке возникла не однозначная ситуация{e}')

    if response.status_code != HTTPStatus.OK:
        raise logger.debug("Отсутствует переменная(-ные) окружения")

    try:
        return response.json()
    except json.decoder.JSONDecodeError:
        logger.debug('не возвращает json')


def check_response(response):
    """проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logger.error('структура данных не соответствует ожиданиям')
        raise TypeError('Не словарь')
    homeworks = response.get('homeworks')
    if 'homeworks' not in response:
        logger.error('В ответе нет ключа')
        raise KeyError('В ответе нет ключа')
    if not isinstance(homeworks, list):
        logger.error('данные приходят не в виде списка.')
        raise TypeError('Не список')
    return homeworks


def parse_status(homework):
    """извлекает из информации о конкретной.
    домашней работе статус этой работы
    """
    homework_name = homework.get('homework_name')
    if not homework_name:
        logger.error('Нет имени домашней работы')
        raise KeyError('Нет имени домашней работы')
    homework_status = homework.get('status')
    if not homework_status:
        logger.error('Нет статуса работы')
        raise KeyError('Нет статуса работы')
    if homework_status not in HOMEWORK_VERDICTS:
        raise logger.error(
            'Пустой или незнакомый статус домашней работы')
    verdict = HOMEWORK_VERDICTS[homework_status]
    logger.info('Изменился статус проверки работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    DELTA_TIME: int = 600000
    if not check_tokens():
        logger.critical("Отсутствует переменная(-ные) окружения")
        sys.exit("Отсутствует переменная(-ные) окружения")
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    current_timestamp = timestamp - DELTA_TIME

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            homework = homeworks[0]
            if not homework:
                logger.debug('нет обнаружено работы')
            else:
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = response.get('current_date')

        except Exception as error:
            message = str(f'Сбой в работе программы {error}')
            send_message(bot, message)
            logger.debug(message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
