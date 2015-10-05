#!/usr/bin/env python3

import functools
import itertools
import operator

class Mediator:
    def __init__(self):
        self._publishers_by_topic = {}
        self._subscribers_by_topic = {}

    def _notify_subscriber(self, topic, subscriber):
        subscriber(topic)

    def get_published_data(self, *topics):
        return itertools.chain.from_iterable([
            [publisher(topic) for publisher in self._publishers_by_topic.get(topic, [])]
            for topic in topics
        ])

    def notify_subscribers(self, topic):
        for subscriber in self._subscribers_by_topic.get(topic, []):
            self._notify_subscriber(topic, subscriber)

    def publish(self, topic, publisher):
        publishers = self._publishers_by_topic.setdefault(topic, [])
        publishers.append(publisher)
        self.notify_subscribers(topic)

    def subscribe(self, topic, subscriber):
        subscribers = self._subscribers_by_topic.setdefault(topic, [])
        subscribers.append(subscriber)
        self._notify_subscriber(topic, subscriber)

class Value:
    def __init__(self, mediator, name, value=0):
        self._mediator = mediator
        self._name = name
        self._value = value
        mediator.publish(name, self)

    def __call__(self, name):
        assert name == self._name
        return self

    def _notify_subscribers(self):
        self._mediator.notify_subscribers(self._name)

    def get_name(self):
        return self._name

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = value
        self._notify_subscribers()

class ValueAggregator:
    def __init__(self, mediator, target_value):
        self._mediator = mediator
        self._source_value_names = []
        self._target_value = target_value

    def __call__(self, topic):
        new_target_value = functools.reduce(
            operator.add,
            [
                source_value.get_value()
                for source_value in self._mediator.get_published_data(*self._source_value_names)
            ],
            0
        )
        self._target_value.set_value(new_target_value)

    def add_source_value(self, value):
        self._source_value_names.append(value.get_name())
        self._mediator.subscribe(value.get_name(), self)

if __name__ == '__main__':
    mediator = Mediator()
    ability_base = Value(mediator, 'ability_base', 14)
    ability_adj = Value(mediator, 'ability_adj', 2)
    ability = Value(mediator, 'ability')
    print('[initial] {} = {}'.format(ability.get_name(), ability.get_value()))

    mediator.subscribe(ability.get_name(), lambda topic: [
        print('[notification] {} = {}'.format(value.get_name(), value.get_value()))
        for value in mediator.get_published_data(topic)
    ])

    ability_aggregator = ValueAggregator(mediator, ability)
    ability_aggregator.add_source_value(ability_base)
    ability_aggregator.add_source_value(ability_adj)

    ability_adj.set_value(-1)
    ability_base.set_value(10)

    print('[final] {} = {}'.format(ability.get_name(), ability.get_value()))
