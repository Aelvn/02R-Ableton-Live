# -*- coding: utf-8 -*-
# KeyLabPads - point d'entree du Remote Script pour Ableton Live 12
from .KeyLabPads import KeyLabPads


def create_instance(c_instance):
    return KeyLabPads(c_instance)
