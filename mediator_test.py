#!/usr/bin/env python3

import functools
import operator
import re

class Mediator:
    def __init__(self):
        self._publishers_by_topic = {}
        self._subscribers_by_topic = {}

    def _get_published_data(self, topic):
        assert isinstance(topic, str)
        return [publisher(topic) for publisher in self._publishers_by_topic.get(topic, [])]

    def _notify_subscriber(self, subscriber, topic):
        assert isinstance(topic, str)
        subscriber(topic)

    def _notify_subscribers_with_topic(self, topic):
        assert isinstance(topic, str)
        for subscriber in self._subscribers_by_topic.get(topic, []):
            self._notify_subscriber(subscriber, topic)

    def _notify_subscribers_with_topic_pattern(self, topic):
        assert isinstance(topic, str)
        for topic_pattern in self._subscribers_by_topic.keys():
            if not isinstance(topic_pattern, str):
                if topic_pattern.fullmatch(topic):
                    for subscriber in self._subscribers_by_topic[topic_pattern]:
                        self._notify_subscriber(subscriber, topic)

    def get_published_data(self, *topics):
        data = []
        for topic in topics:
            if isinstance(topic, str):
                data.extend(self._get_published_data(topic))
            else:
                for publisher_topic in self._publishers_by_topic.keys():
                    if topic.fullmatch(publisher_topic):
                        data.extend(self._get_published_data(publisher_topic))
        return data

    def notify_subscribers(self, *topics):
        for topic in topics:
            assert isinstance(topic, str)
            self._notify_subscribers_with_topic(topic)
            self._notify_subscribers_with_topic_pattern(topic)

    def publish(self, publisher, *topics):
        for topic in topics:
            assert isinstance(topic, str)
            publishers = self._publishers_by_topic.setdefault(topic, [])
            publishers.append(publisher)
            self.notify_subscribers(topic)

    def subscribe(self, subscriber, *topics):
        for topic in topics:
            subscribers = self._subscribers_by_topic.setdefault(topic, [])
            subscribers.append(subscriber)
            if isinstance(topic, str):
                self._notify_subscriber(subscriber, topic)
            else:
                for publisher_topic in self._publishers_by_topic.keys():
                    if topic.fullmatch(publisher_topic):
                        self._notify_subscriber(subscriber, publisher_topic)

class Value:
    def __init__(self, mediator, name):
        self._mediator = mediator
        self._name = name
        self._published_topics = []

    def _notify_subscribers(self):
        self._mediator.notify_subscribers(*self._published_topics)

    def get_name(self):
        return self._name

    def publish(self, *topics):
        self._published_topics += topics
        self._mediator.publish(lambda topic: self, *topics)

class StaticValue(Value):
    def __init__(self, mediator, name, value):
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

class ValueFactory:
    def __init__(self, mediator):
        self._mediator = mediator

    def new_dynamic(self, name):
        value = DynamicValue(self._mediator, name)
        value.publish(name)
        return value

    def new_static(self, name, value=0):
        value = StaticValue(self._mediator, name, value)
        value.publish(name)
        return value

if __name__ == '__main__':
    def print_value(message, value):
        print('[{}] {} = {}'.format(message, value.get_name(), value.get_value()))

    mediator = Mediator()
    mediator.subscribe(
        lambda topic: [
            print_value('notification', value)
            for value in mediator.get_published_data(topic)
        ],
        re.compile('astr|aint|adex')
    )

    value_factory = ValueFactory(mediator)

    # Case 1: composite value subscribes to component values
    astr_base = value_factory.new_static('astr_base', 14)
    astr_adj = value_factory.new_static('astr_adj', 2)
    astr = value_factory.new_dynamic('astr')
    print_value('initial', astr)

    astr.subscribe(astr_base.get_name())
    astr.subscribe(astr_adj.get_name())

    astr_adj.set_value(-1)
    astr_base.set_value(10)

    print_value('final', astr)

    # Case 2: component values publish to composite value
    aint_base = value_factory.new_static('aint_base', 12)
    aint_adj = value_factory.new_static('aint_adj', 1)
    aint = value_factory.new_dynamic('aint')
    print_value('initial', aint)

    aint.subscribe('aint_contrib')
    aint_base.publish('aint_contrib')
    aint_adj.publish('aint_contrib')

    aint_adj.set_value(-3)
    aint_base.set_value(8)

    print_value('final', aint)

    # Case 3: composite value subscribes to pattern; component values publish to topics that match pattern
    adex_base = value_factory.new_static('adex_base', 13)
    adex_adj = value_factory.new_static('adex_adj', 3)
    adex = value_factory.new_dynamic('adex')
    print_value('initial', adex)

    adex.subscribe(re.compile('adex_.+'))

    adex_adj.set_value(-2)
    adex_base.set_value(9)

    print_value('final', adex)
