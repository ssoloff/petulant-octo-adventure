#!/usr/bin/env python3

import functools
import itertools
import operator

class Mediator:
    def __init__(self):
        self._publishers_by_topic = {}
        self._subscribers_by_topic = {}

    def _notify_subscriber(self, subscriber, topic):
        subscriber(topic)

    def get_published_data(self, *topics):
        return itertools.chain.from_iterable([
            [publisher(topic) for publisher in self._publishers_by_topic.get(topic, [])]
            for topic in topics
        ])

    def notify_subscribers(self, *topics):
        for topic in topics:
            for subscriber in self._subscribers_by_topic.get(topic, []):
                self._notify_subscriber(subscriber, topic)

    def publish(self, publisher, *topics):
        for topic in topics:
            publishers = self._publishers_by_topic.setdefault(topic, [])
            publishers.append(publisher)
            self.notify_subscribers(topic)

    def subscribe(self, subscriber, *topics):
        for topic in topics:
            subscribers = self._subscribers_by_topic.setdefault(topic, [])
            subscribers.append(subscriber)
            self._notify_subscriber(subscriber, topic)

class Value:
    def __init__(self, mediator, name):
        self._mediator = mediator
        self._name = name
        self._published_topics = []
        self.publish(name)

    def _notify_subscribers(self):
        self._mediator.notify_subscribers(*self._published_topics)

    def get_name(self):
        return self._name

    def publish(self, *topics):
        self._published_topics += topics
        self._mediator.publish(lambda topic: self, *topics)

class FixedValue(Value):
    def __init__(self, mediator, name, value=0):
        super().__init__(mediator, name)
        self._value = value

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = value
        self._notify_subscribers()

class DynamicValue(Value):
    def __init__(self, mediator, name):
        super().__init__(mediator, name)
        self._subscribed_topics = []

    def get_value(self):
        return functools.reduce(
            operator.add,
            [
                value.get_value()
                for value in self._mediator.get_published_data(*self._subscribed_topics)
            ],
            0
        )

    def subscribe(self, *topics):
        self._subscribed_topics += topics
        self._mediator.subscribe(lambda topic: self._notify_subscribers(), *topics)

if __name__ == '__main__':
    def print_value(message, value):
        print('[{}] {} = {}'.format(message, value.get_name(), value.get_value()))

    mediator = Mediator()
    observer = lambda topic: [print_value('notification', value) for value in mediator.get_published_data(topic)]

    # Case 1: composite value subscribes to component values
    astr_base = FixedValue(mediator, 'astr_base', 14)
    astr_adj = FixedValue(mediator, 'astr_adj', 2)
    astr = DynamicValue(mediator, 'astr')
    print_value('initial', astr)

    mediator.subscribe(observer, astr.get_name())

    astr.subscribe(astr_base.get_name())
    astr.subscribe(astr_adj.get_name())

    astr_adj.set_value(-1)
    astr_base.set_value(10)

    print_value('final', astr)

    # Case 2: component values publish to composite value
    aint_base = FixedValue(mediator, 'aint_base', 12)
    aint_adj = FixedValue(mediator, 'aint_adj', 1)
    aint = DynamicValue(mediator, 'aint')
    print_value('initial', aint)

    mediator.subscribe(observer, aint.get_name())

    aint.subscribe('aint_contrib')
    aint_base.publish('aint_contrib')
    aint_adj.publish('aint_contrib')

    aint_adj.set_value(-1)
    aint_base.set_value(10)

    print_value('final', aint)
