class Field:
  def __init__(self, default=0):
    self.default = default
  
  def create(self, entity, name):
    return _Field(name, self)


class Watch:
  def __init__(self, source, f):
    self.source = source
    self.f = f

  def create(self, entity, name):
    return _Watch(name, self, entity)


class EntityBase(type):
  def __new__(cls, name, bases, attrs, **kwargs):
    meta = {}
    print(f'EntityBase.__new__(cls={cls.__name__}, name={name})')
    for k, v in attrs.items():
      if isinstance(v, Field) or isinstance(v, Watch):
        print(f'+ {k}: {v}(type(v)')
        meta[k] = v 
    new_cls = super().__new__(cls, name, bases, attrs, **kwargs)
    setattr(new_cls, '_meta', meta)
    return new_cls


class Entity(metaclass=EntityBase):
  @classmethod
  def create(cls, **kwargs):
    obj = cls.__call__(**kwargs)
    return obj
  
  def __init__(self, **kwargs):
    super().__init__()
    self.__fields_dict__ = {}  # stores mapping 'prototype -> instance'
    for field_name, prototype in self._meta.items():
      field_instance = prototype.create(self, field_name)
      self.__fields_dict__[prototype] = field_instance
      setattr(self, field_name, field_instance)
    for name, value in kwargs.items():
      self.get_field(name).value = value
  
  def get_field(self, index):
    if index in self._meta:
      return self.__fields_dict__[self._meta[index]]
    else:
      return self.__fields_dict__[index]


class _Updatable:
  def __init__(self):
    self._listeners = []
  
  def attach_listener(self, listener):
    self._listeners.append(listener)
  
  def _updated(self):
    for listener in self._listeners:
      listener.update()


class _Field(_Updatable):
  def __init__(self, name, prototype):
    super().__init__()
    self._name = name
    self._prototype = prototype
    self._value = prototype.default

  @property
  def value(self):
    return self._value
  
  @value.setter
  def value(self, new_value):
    if self._value != new_value:
      self._value = new_value
      self._updated()
  
  def __str__(self):
    return f"{self._name} (={self.value})"
  
  @property
  def prototype(self):
    return self._prototype

  @property
  def name(self):
    return self._name


class _Watch(_Updatable):
  def __init__(self, name, prototype, entity):
    super().__init__()
    self._name = name
    self._prototype = prototype
    self._entity = entity
    self._value = None
    self.update()
    real_source = entity.get_field(self.prototype.source)
    real_source.attach_listener(self)
  
  def update(self):
    real_source = self.entity.get_field(self.prototype.source)
    new_value = self.prototype.f(real_source.value)
    if new_value != self._value:
      self._value = new_value
      self._updated()
  
  @property
  def value(self):
    return self._value

  def __str__(self):
    return f"{self.value}"
  
  @property
  def prototype(self):
    return self._prototype
  
  @property
  def entity(self):
    return self._entity
  
  @property
  def name(self):
    return self._name


if __name__ == '__main__':
  import math

  class Packet(Entity):
    name = Field()
    bitsize = Field()
    bytesize = Watch(source=bitsize, f=lambda x: int(math.ceil(x/8)))
    wordsize = Watch(source=bytesize, f=lambda x: int(math.ceil(x/2)))
  
  def print_packet(p):
    print(f"{p.name}: bits:{p.bitsize}, bytes:{p.bytesize}, words:{p.wordsize}")
  
  p1 = Packet.create(name="Pkt#1", bitsize=8)
  p2 = Packet.create(name="Pkt#2", bitsize=17)
  print_packet(p1)
  print_packet(p2)
  assert p1.bitsize.value == 8
  assert p2.bitsize.value == 17
  print('--- set p1 bitsize = 48 ---')
  p1.bitsize.value = 48
  print_packet(p1)