#!/usr/bin/env python3

import functools
import operator

class Value:
    def __init__(self, name):
        self._name = name
        self._observers = []

    def _notify_observer(self, observer):
        observer(self)

    def _notify_observers(self):
        for observer in self._observers:
            self._notify_observer(observer)

    def add_observer(self, observer):
        self._observers.append(observer)
        self._notify_observer(observer)

    def get_name(self):
        return self._name

class FixedValue(Value):
    def __init__(self, name, value=0):
        super().__init__(name)
        self._value = value

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = value
        self._notify_observers()

class DynamicValue(Value):
    def __init__(self, name):
        super().__init__(name)
        self._providers = []

    def add_provider(self, provider):
        self._providers.append(provider)
        provider.add_observer(lambda value: self._notify_observers())

    def get_value(self):
        return functools.reduce(
            operator.add,
            [provider.get_value() for provider in self._providers],
            0
        )

if __name__ == '__main__':
    ability_base = FixedValue('ability_base', 14)
    ability_adj = FixedValue('ability_adj', 2)
    ability = DynamicValue('ability')
    print('[initial] {} = {}'.format(ability.get_name(), ability.get_value()))

    ability.add_observer(lambda value: print('[notification] {} = {}'.format(value.get_name(), value.get_value())))

    ability.add_provider(ability_base)
    ability.add_provider(ability_adj)

    ability_adj.set_value(-1)
    ability_base.set_value(10)

    print('[final] {} = {}'.format(ability.get_name(), ability.get_value()))
