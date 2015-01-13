from collections import defaultdict

from mock import call

from nameko.dependencies import InjectionProvider, SharedExtension, Extension
from nameko.testing.utils import get_dependency


class CallCollectorMixin(object):

    calls = defaultdict(lambda: defaultdict(list))

    def start(self, *args, **kwargs):
        self.calls[type(self)]['start'].append(call(*args, **kwargs))
        super(CallCollectorMixin, self).start(*args, **kwargs)


def test_simple_sharing(container_factory):

    class SimpleSharedExtension(CallCollectorMixin, SharedExtension):
        pass

    class SimpleInjection(CallCollectorMixin, InjectionProvider):
        ext = SimpleSharedExtension()

    class Service(object):
        inj_1 = SimpleInjection()
        inj_2 = SimpleInjection()

    container = container_factory(Service, {})
    container.start()

    assert len(container.dependencies) == 3
    assert len(CallCollectorMixin.calls[SimpleInjection]['start']) == 2
    assert len(CallCollectorMixin.calls[SimpleSharedExtension]['start']) == 1


def test_custom_sharing_key(container_factory):

    class CustomSharedExtension(CallCollectorMixin, SharedExtension):
        def __init__(self, arg):
            self.arg = arg

        @property
        def sharing_key(self):
            return (type(self), self.arg)

    class SimpleInjection(CallCollectorMixin, InjectionProvider):
        ext_a = CustomSharedExtension("a")
        ext_b = CustomSharedExtension("b")

    class Service(object):
        inj_1 = SimpleInjection()
        inj_2 = SimpleInjection()

    container = container_factory(Service, {})
    container.start()

    assert len(container.dependencies) == 4
    assert len(CallCollectorMixin.calls[SimpleInjection]['start']) == 2
    assert len(CallCollectorMixin.calls[CustomSharedExtension]['start']) == 2

    inj_1 = get_dependency(container, SimpleInjection, name="inj_1")
    inj_2 = get_dependency(container, SimpleInjection, name="inj_2")

    assert inj_1.ext_a != inj_1.ext_b
    assert inj_1.ext_a is inj_2.ext_a
    assert inj_1.ext_b is inj_2.ext_b


def test_shared_intermediate(container_factory):

    class DedicatedExtension(CallCollectorMixin, Extension):
        pass

    class SharedIntermediate(CallCollectorMixin, SharedExtension):
        ext = DedicatedExtension()

    class SimpleInjection(CallCollectorMixin, InjectionProvider):
        ext = SharedIntermediate()

    class Service(object):
        inj_1 = SimpleInjection()
        inj_2 = SimpleInjection()

    container = container_factory(Service, {})
    container.start()

    assert len(container.dependencies) == 4
    assert len(CallCollectorMixin.calls[SimpleInjection]['start']) == 2
    assert len(CallCollectorMixin.calls[SharedIntermediate]['start']) == 1
    assert len(CallCollectorMixin.calls[DedicatedExtension]['start']) == 1


def test_shared_extension_uniqueness(container_factory):

    class SimpleSharedExtension(CallCollectorMixin, SharedExtension):
        pass

    class SimpleInjection(CallCollectorMixin, InjectionProvider):
        ext = SimpleSharedExtension()

    class Service(object):
        inj_1 = SimpleInjection()
        inj_2 = SimpleInjection()

    c1 = container_factory(Service, {})
    c2 = container_factory(Service, {})

    # extension declarations are identical between containers
    assert c1.service_cls.inj_1.ext == c2.service_cls.inj_1.ext

    # extension instances are different between containers
    shared_1 = get_dependency(c1, SimpleSharedExtension)
    shared_2 = get_dependency(c2, SimpleSharedExtension)
    assert shared_1 is not shared_2
