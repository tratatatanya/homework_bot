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
    except Exception as error:
        logger.error('ошибка при отправке сообщения')
        raise SystemError(f'Ошибка {error} при отправке сообщения.')


def get_api_answer(current_timestamp):
    """Проверяем ответ API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        logger.error('Ошибка при получении ответа.')
        raise SystemError('Ошибка при получении ответа.')
    else:
        if response.status_code == HTTPStatus.OK:
            logger.info('Получен ответ')
            homework = response.json()
            if 'error' in homework:
                logger.error('ошибка в ответе')
                raise SystemError(f'Ошибка json, {homework["error"]}')
            elif 'code' in homework:
                logger.error('ошибка в ответе')
                raise SystemError(f'Ошибка json, {homework["code"]}')
            else:
                return homework
        else:
            logger.error('Сервис недоступен')
            raise SystemError('Сервис недоступен')


def check_response(response):
    """Проверяем полученный ответ."""
    if type(response) == dict:
        response['current_date']
        homeworks = response['homeworks']
        if type(homeworks) == list:
            return homeworks
        else:
            logger.error('В ответе не список')
            raise TypeError('В ответе не список')
    else:
        logger.error('В ответе не словарь')
        raise TypeError('В ответе не словарь')


def parse_status(homework):
    """Ищем подходящий статус."""
    try:
        homework_name = homework.get('homework_name')
    except KeyError:
        message = f'Ничего не найдено по ключу {"homework_name"}'
        logger.info(message)
    if homework_name is None:
        logger.error('Домашняя работа не найдена')
        raise KeyError('Домашняя работа не найдена')
    homework_status = homework.get('status')
    if homework_status is None:
        logger.error('Статус домашней работы не найден')
        raise KeyError('Статус домашней работы не найден')
    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        logger.error('Вердикт по домашней работе не найден')
        raise KeyError('Вердикт по домашней работе не найден')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем наличие всех необходимых переменных окружения."""
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Не хватает переменных окружения!'
        logger.critical(message)
        raise exceptions.MissingTokenException(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - 86400
    current_status = None
    last_message = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            try:
                homework_status = homeworks[0].get('status')
                message = parse_status(homeworks[0])
                if homework_status != current_status:
                    current_status = homework_status
                    logger.info(message)
                    send_message(bot, message)
            except IndexError:
                message = 'Нет проверенных домашек за последние сутки'
                logger.info(message)
                if last_message != message:
                    last_message = message
                    send_message(bot, message)
            else:
                message = 'Статус не изменился.'
                logger.debug(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
