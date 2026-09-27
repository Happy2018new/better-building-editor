"""Assign a shared VS/PS interface; do not change shader arithmetic."""
import struct


def normalize_interfaces(vertex_path, fragment_path):
    modules = [Module(p.read_bytes()) for p in (vertex_path, fragment_path)]
    # OpVariable storage classes Input=1 / Output=3; builtins have no Location.
    outputs = modules[0].located_variables(3)
    inputs = modules[1].located_variables(1)
    missing = set(inputs) - set(outputs)
    if missing:
        raise ValueError('Fragment inputs missing in vertex stage: ' + repr(sorted(missing)))
    names = sorted(set(inputs) | set(outputs))
    locations = {name: index for index, name in enumerate(names)}
    for module, variables in zip(modules, (outputs, inputs)):
        for name, variable in variables.items():
            module.set_decoration(variable, 30, locations[name])  # Location
        # Preserve TEXTURE_n -> tN/sN. Uniforms live in descriptor set 1;
        # textures in set 0, so the intermediate Vulkan layout stays valid.
        for variable, name in module.names.items():
            if name.startswith('TEXTURE_') and name[8:].isdigit():
                module.set_decoration(variable, 33, int(name[8:]))  # Binding
    for path, module in zip((vertex_path, fragment_path), modules):
        path.write_bytes(module.to_bytes())
    return locations


class Module:
    def __init__(self, data):
        if len(data) % 4:
            raise ValueError('Invalid SPIR-V word length')
        self.words = list(struct.unpack('<%dI' % (len(data) // 4), data))
        if self.words[0] != 0x07230203:
            raise ValueError('Invalid SPIR-V magic')
        self.names, self.storage, self.decorations = {}, {}, {}
        offset = 5
        while offset < len(self.words):
            word = self.words[offset]
            length, opcode = word >> 16, word & 0xffff
            if not length or offset + length > len(self.words):
                raise ValueError('Invalid SPIR-V instruction')
            args = self.words[offset + 1:offset + length]
            if opcode == 5:  # OpName
                raw = struct.pack('<%dI' % (len(args) - 1), *args[1:])
                self.names[args[0]] = raw.split(b'\0', 1)[0].decode('utf8')
            elif opcode == 59:  # OpVariable
                self.storage[args[1]] = args[2]
            elif opcode == 71:  # OpDecorate
                self.decorations[(args[0], args[1])] = offset + 3
            offset += length

    def located_variables(self, storage):
        return {name: variable for variable, name in self.names.items()
                if self.storage.get(variable) == storage and (variable, 30) in self.decorations}

    def set_decoration(self, variable, decoration, value):
        offset = self.decorations.get((variable, decoration))
        if offset is not None:
            self.words[offset] = value

    def to_bytes(self):
        return struct.pack('<%dI' % len(self.words), *self.words)
