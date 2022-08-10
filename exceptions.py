class MessageNotSendedException(Exception):
    """Сообщение не отправлено."""


class WrongAPIAnswerException(Exception):
    """Некорректный ответ API."""


class WrongResponseException(Exception):
    """Ответ некорректного типа."""


class APIStatusCodeException(Exception):
    """Сервис недоступен."""
