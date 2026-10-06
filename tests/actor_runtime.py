"""Test SDK components retain the entity they were created for."""


class BoundComponent:
    def __init__(self, runtime, field, entity):
        self.runtime, self.field, self.entity = runtime, field, entity

    def __getattr__(self, name):
        def invoke(*args, **kwargs):
            setattr(self.runtime, self.field, self.entity)
            return getattr(self.runtime, name)(*args, **kwargs)
        return invoke
