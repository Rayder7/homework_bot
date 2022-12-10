import sys
import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

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

    if response.status_code != 200:
        assert logger.debug("Отсутствует переменная(-ные) окружения")

    if response is not None:
        return response.json()


def check_response(response):
    """проверяет ответ API на соответствие документации."""
    try:
        homework = response['homeworks']
    except KeyError:
        logger.error('В ответе нет ключа')
        raise KeyError('В ответе нет ключа')

    if type(response) is not dict:
        logger.error('структура данных не соответствует ожиданиям')
        raise TypeError('Не словарь')
    if type(response['homeworks']) is not list:
        logger.error('данные приходят не в виде списка.')
        raise TypeError('Не список')
    return homework[0]


def parse_status(homework):
    """извлекает из информации о конкретной.
    домашней работе статус этой работы
    """
    try:
        homework_name = homework['homework_name']
    except KeyError as e:
        logger.error(f'Нет имени домашней работы {e}')
    try:
        homework_status = homework['status']
    except KeyError as e:
        logger.error(f'Нет статуса {e}')
    if homework_status not in HOMEWORK_VERDICTS:
        assert logger.error(
            'Пустой или незнакомый статус домашней работы')
    verdict = HOMEWORK_VERDICTS[homework_status]
    logger.info('Изменился статус проверки работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical("Отсутствует переменная(-ные) окружения")
        sys.exit("Отсутствует переменная(-ные) окружения")
    TMP_STATUS = 'reviewing'
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if TMP_STATUS != homework['status']:
                message = parse_status(homework)
                send_message(bot, message)
                TMP_STATUS = homework['status']
            logger.debug('Изменений нет? ждем 10 минут')
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = str(f'Сбой в работе программы {error}')
            logger.critical(message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
