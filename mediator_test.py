#!/usr/bin/env python3

import functools
import itertools
import operator
import re

class _Topic:
    def __init__(self, mediator):
        self._mediator = mediator

    def _get_published_data_for_topic(self, topic):
        return [publisher(topic) for publisher in self._mediator._get_publishers_for_topic(topic)]

    def _notify_subscribers_for_topic(self, subscribers, topic):
        assert _Topic.is_single_topic(topic)
        for subscriber in subscribers:
            subscriber(topic)

    @staticmethod
    def is_multi_topic(*topics):
        return all(map(lambda topic: isinstance(topic, _MultiTopic), topics))

    @staticmethod
    def is_single_topic(*topics):
        return all(map(lambda topic: isinstance(topic, _SingleTopic), topics))

class _SingleTopic(_Topic):
    def __init__(self, mediator, name):
        super().__init__(mediator)
        self._name = name

    def __eq__(self, other):
        return self._name == other._name

    def __hash__(self):
        return hash(self._name)

    def __repr__(self):
        return 'SingleTopic[{}]'.format(self._name)

    def get_published_data(self):
        return self._get_published_data_for_topic(self)

    def matches(self, topic):
        return self._name == topic._name

    def notify_subscribers(self, *subscribers):
        self._notify_subscribers_for_topic(subscribers, self)

class _MultiTopic(_Topic):
    def __init__(self, mediator, name_pattern):
        super().__init__(mediator)
        self._name_pattern = name_pattern

    def __eq__(self, other):
        return self._name_pattern == other._name_pattern

    def __hash__(self):
        return hash(self._name_pattern)

    def __repr__(self):
        return 'MultiTopic[{}]'.format(self._name_pattern)

    def get_published_data(self):
        return itertools.chain.from_iterable(
            self._get_published_data_for_topic(publisher_topic)
            for publisher_topic in self._mediator._get_all_publisher_topics()
            if self._name_pattern.fullmatch(publisher_topic._name)
        )

    def matches(self, topic):
        return self._name_pattern.fullmatch(topic._name)

    def notify_subscribers(self, *subscribers):
        for publisher_topic in self._mediator._get_all_publisher_topics():
            if self._name_pattern.fullmatch(publisher_topic._name):
                self._notify_subscribers_for_topic(subscribers, publisher_topic)

class _Value:
    def __init__(self, mediator, name):
        self._mediator = mediator
        self._published_topics = []
        self._topic = mediator.new_single_topic(name)

    def _notify_subscribers(self):
        self._mediator.notify_subscribers(*self._published_topics)

    def get_topic(self):
        return self._topic

    def publish(self, *topics):
        assert _Topic.is_single_topic(*topics)
        self._published_topics += topics
        self._mediator.publish(lambda topic: self, *topics)

class _StaticValue(_Value):
    def __init__(self, mediator, name, value):
        super().__init__(mediator, name)
        self._value = value

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = value
        self._notify_subscribers()

class _DynamicValue(_Value):
    def __init__(self, mediator, name):
        super().__init__(mediator, name)
        self._subscribed_topics = []

    def _get_subscribed_values(self):
        return self._mediator.get_published_data(*self._subscribed_topics)

    def get_value(self):
        return functools.reduce(
            operator.add,
            [value.get_value() for value in self._get_subscribed_values()],
            0
        )

    def subscribe(self, *topics):
        self._subscribed_topics += topics
        self._mediator.subscribe(lambda topic: self._notify_subscribers(), *topics)

class Mediator:
    def __init__(self):
        self._observers = []
        self._publishers_by_topic = {}
        self._subscribers_by_topic = {}

    def _add_publisher(self, publisher, topic):
        assert _Topic.is_single_topic(topic)
        publishers = self._get_publishers_for_topic(topic, create_if_absent=True)
        publishers.append(publisher)
        self._notify_observers_that_publisher_added(publisher, topic)

    def _add_subscriber(self, subscriber, topic):
        subscribers = self._get_subscribers_for_topic(topic, create_if_absent=True)
        subscribers.append(subscriber)
        self._notify_observers_that_subscriber_added(subscriber, topic)

    def _get_all_publisher_topics(self):
        return self._publishers_by_topic.keys()

    def _get_all_subscriber_topics(self):
        return self._subscribers_by_topic.keys()

    def _get_publishers_for_topic(self, topic, create_if_absent=False):
        assert _Topic.is_single_topic(topic)
        if create_if_absent:
            return self._publishers_by_topic.setdefault(topic, [])
        else:
            return self._publishers_by_topic.get(topic, [])

    def _get_subscribers_for_topic(self, topic, create_if_absent=False):
        if create_if_absent:
            return self._subscribers_by_topic.setdefault(topic, [])
        else:
            return self._subscribers_by_topic.get(topic, [])

    def _notify_observers(self, action):
        for observer in self._observers:
            action(observer)

    def _notify_observers_that_publisher_added(self, publisher, topic):
        self._notify_observers(lambda observer: observer.publisher_added(publisher, topic))

    def _notify_observers_that_subscriber_added(self, subscriber, topic):
        self._notify_observers(lambda observer: observer.subscriber_added(subscriber, topic))

    def _notify_observers_that_topic_published(self, topic):
        self._notify_observers(lambda observer: observer.topic_published(topic))

    def _notify_subscribers(self, topic):
        assert _Topic.is_single_topic(topic)
        self._notify_observers_that_topic_published(topic)
        for subscriber_topic in self._get_all_subscriber_topics():
            if subscriber_topic.matches(topic):
                topic.notify_subscribers(*self._get_subscribers_for_topic(subscriber_topic))

    def add_observer(self, observer):
        self._observers.append(observer)

    def get_published_data(self, *topics):
        return itertools.chain.from_iterable([
            topic.get_published_data() for topic in topics
        ])

    def new_dynamic_value(self, name):
        value = _DynamicValue(self, name)
        value.publish(value.get_topic())
        return value

    def new_multi_topic(self, name_pattern):
        return _MultiTopic(self, name_pattern)

    def new_single_topic(self, name):
        return _SingleTopic(self, name)

    def new_static_value(self, name, value=0):
        value = _StaticValue(self, name, value)
        value.publish(value.get_topic())
        return value

    def notify_subscribers(self, *topics):
        for topic in topics:
            self._notify_subscribers(topic)

    def publish(self, publisher, *topics):
        for topic in topics:
            self._add_publisher(publisher, topic)
            self._notify_subscribers(topic)

    def subscribe(self, subscriber, *topics):
        for topic in topics:
            self._add_subscriber(subscriber, topic)
            topic.notify_subscribers(subscriber)

if __name__ == '__main__':
    class Observer:
        def publisher_added(self, publisher, topic):
            print('[observer] added publisher "{}" for topic "{}"'.format(publisher, topic))

        def subscriber_added(self, subscriber, topic):
            print('[observer] added subscriber "{}" for topic "{}"'.format(subscriber, topic))

        def topic_published(self, topic):
            print('[observer] topic "{}" published'.format(topic))

    def print_value(message, value):
        print('[{}] {} = {}'.format(message, value.get_topic(), value.get_value()))

    mediator = Mediator()
    mediator.subscribe(
        lambda topic: [
            print_value('notification', value)
            for value in mediator.get_published_data(topic)
        ],
        mediator.new_multi_topic(re.compile('astr|aint|adex'))
    )

    # uncomment the following line to enable verbose Mediator logging
    #mediator.add_observer(Observer())

    # Case 1: composite value subscribes to component values
    astr_base = mediator.new_static_value('astr_base', 14)
    astr_adj = mediator.new_static_value('astr_adj', 2)
    astr = mediator.new_dynamic_value('astr')
    print_value('initial', astr)

    astr.subscribe(astr_base.get_topic())
    astr.subscribe(astr_adj.get_topic())

    astr_adj.set_value(-1)
    astr_base.set_value(10)

    print_value('final', astr)

    # Case 2: component values publish to composite value
    aint_base = mediator.new_static_value('aint_base', 12)
    aint_adj = mediator.new_static_value('aint_adj', 1)
    aint = mediator.new_dynamic_value('aint')
    print_value('initial', aint)

    aint_contrib_topic = mediator.new_single_topic('aint_contrib')
    aint.subscribe(aint_contrib_topic)
    aint_base.publish(aint_contrib_topic)
    aint_adj.publish(aint_contrib_topic)

    aint_adj.set_value(-3)
    aint_base.set_value(8)

    print_value('final', aint)

    # Case 3: composite value subscribes to pattern; component values publish to topics that match pattern
    adex_base = mediator.new_static_value('adex_base', 13)
    adex_adj = mediator.new_static_value('adex_adj', 3)
    adex = mediator.new_dynamic_value('adex')
    print_value('initial', adex)

    adex.subscribe(mediator.new_multi_topic(re.compile('adex_.+')))

    adex_adj.set_value(-2)
    adex_base.set_value(9)

    print_value('final', adex)
