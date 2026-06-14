"""Определение пола по имени для обращения сеньор / сеньорита."""
from __future__ import annotations

import re

from personality import GENDER_FEMALE, GENDER_MALE

_MALE = {
    "alex", "alexander", "andrey", "anton", "artem", "artur", "bogdan", "boris",
    "david", "dmitry", "ivan", "john", "max", "michael", "nikolay", "oleg", "pavel",
    "sergey", "александр", "алексей", "анатолий", "андрей", "антон", "артем", "артур",
    "богдан", "борис", "вадим", "валентин", "валерий", "василий", "виктор", "виталий",
    "владимир", "владислав", "всеволод", "вячеслав", "геннадий", "георгий", "глеб",
    "григорий", "даниил", "данил", "данила", "денис", "дмитрий", "евгений", "егор",
    "иван", "игорь", "илья", "кирилл", "константин", "леонид", "максим", "марк",
    "матвей", "михаил", "никита", "николай", "олег", "павел", "петр", "роман",
    "руслан", "сергей", "станислав", "степан", "тимофей", "федор", "филипп", "эдуард",
    "юрий", "ярослав",
}

_FEMALE = {
    "anna", "daria", "ekaterina", "elena", "irina", "maria", "natalia", "olga", "victoria",
    "александра", "алена", "алина", "алиса", "алла", "анастасия", "ангелина", "анна",
    "антонина", "валентина", "валерия", "варвара", "вера", "вероника", "виктория",
    "галина", "дария", "дарья", "диана", "ева", "екатерина", "елена", "елизавета",
    "жанна", "зоя", "ирина", "карина", "кристина", "ксения", "лариса", "лидия",
    "любовь", "людмила", "маргарита", "марина", "мария", "надежда", "наталия",
    "наталья", "нина", "оксана", "ольга", "полина", "светлана", "софия", "софья",
    "тамара", "татьяна", "ульяна", "юлия", "яна",
}

_UNISEX = {
    "robin", "valya", "valia", "vasya", "vanya", "zhenya", "zhanna", "жан", "женя",
    "кима", "саша", "слава", "шура",
}

_MALE_A_ENDING = {"илья", "кузьма", "лука", "никита", "савва", "фома"}


def _normalize_first_name(name: str) -> str:
    token = re.split(r"[\s\-]+", name.strip(), maxsplit=1)[0]
    token = re.sub(r"[^\w\u0400-\u04FF]", "", token, flags=re.UNICODE)
    return token.lower().replace("ё", "е")


def detect_name_gender(name: str) -> str | None:
    """
    Возвращает GENDER_MALE, GENDER_FEMALE или None (унисекс / неизвестно — спросить).
    """
    first = _normalize_first_name(name)
    if not first:
        return None

    if first in _UNISEX:
        return None

    if first in _MALE or first in _MALE_A_ENDING:
        return GENDER_MALE

    if first in _FEMALE:
        return GENDER_FEMALE

    if first.endswith(("а", "я", "ия")) and first not in _MALE_A_ENDING:
        return GENDER_FEMALE

    if re.search(r"[бвгджзклмнпрстфхцчшщ]$", first):
        return GENDER_MALE

    return None
