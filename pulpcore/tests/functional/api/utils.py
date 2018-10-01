# coding=utf-8
"""Utilities for pulpcore API tests."""
import string
from random import choice


def gen_username(length=10, valid_characters=True):
    """Generate username given a certain length or punctuation to be used."""
    valid_punctuation = '@.+-_'
    if valid_characters:
        return ''.join(
            choice(string.ascii_letters + string.digits + valid_punctuation)
            for _ in range(length)
        )
    invalid_puntuation = ''.join(
        value for value in string.punctuation if value not in valid_punctuation
    )
    return ''.join(choice(invalid_puntuation) for _ in range(length))
