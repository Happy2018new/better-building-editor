"""Frame-budgeted editor item snapshots; visibility never modifies saved NBT."""
from .item_sprite_plan import iter_render_steps
from .liquid_preview import LiquidPreview
from .model import Document


class ItemPreview(LiquidPreview):
    def __init__(self, session, profile):
        LiquidPreview.__init__(self, session, None, {}, profile.max_groups)
        self.profile = profile

    def _start(self, signature):
        source = self.session.editor.document
        snapshot = Document(source.size, biome=source.biome)
        snapshot.blocks = source.blocks.copy()
        hidden, layer = frozenset(signature[2]), signature[3]
        def visible(pos):
            return pos[1] not in hidden and (layer is None or pos[1] == layer)
        self.document = snapshot
        self.iterator = iter_render_steps(snapshot, self.profile, visible)
        self.preparing = {}
