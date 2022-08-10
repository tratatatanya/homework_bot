import logging
import os
import requests
import telegram
import time
from dotenv import load_dotenv
from http import HTTPStatus

import exceptions


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    filename='error.log',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляем сообщение в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('отправлено сообщение в телеграм')
    except telegram.error.TelegramError:
        raise exceptions.MessageNotSendedException('Не отправлено')


def get_api_answer(current_timestamp):
    """Проверяем ответ API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException:
        raise requests.RequestException('Ошибка при получении ответа')
    if response.status_code != HTTPStatus.OK:
        raise exceptions.APIStatusCodeException(
            f'Ответ сервера {response.status_code}'
        )
    logger.info('Получен ответ')
    homework = response.json()
    if ('error' or 'code') in homework:
        raise exceptions.WrongAPIAnswerException('Ошибка json')
    return homework


def check_response(response):
    """Проверяем полученный ответ."""
    if not isinstance(response, dict):
        raise TypeError('В ответе не словарь')
    if response.get('current_date') is None:
        raise KeyError('В ответе нет current_date')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('В ответе не список')
    return homeworks


def parse_status(homework):
    """Ищем подходящий статус."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('Домашняя работа не найдена')
    homework_status = homework.get('status')
    if not homework_status:
        raise KeyError('Статус домашней работы не найден')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise exceptions.MissingVerdictException(
            'Вердикт по домашней работе не найден'
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем наличие всех необходимых переменных окружения."""
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Не хватает переменных окружения!')
        raise SystemExit('Бот не запустился.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    current_status = None
    last_message = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logger.info('Список проверенных домашек пуст.')
                continue
            homework_status = homeworks[0].get('status')
            message = parse_status(homeworks[0])
            if homework_status != current_status:
                current_status = homework_status
                logger.info(message)
                send_message(bot, message)
            logger.debug('Статус не изменился.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if last_message != message:
                send_message(bot, message)
                last_message = message
            logger.error(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
