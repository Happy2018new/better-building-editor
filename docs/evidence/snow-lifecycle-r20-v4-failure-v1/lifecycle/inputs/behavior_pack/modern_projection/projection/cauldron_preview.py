"""Editor cauldron tops use the shared budgeted preview and native controls."""
from .cauldron_render_plan import iter_render_steps
from .liquid_preview import LiquidPreview
from .model import Document


class CauldronPreview(LiquidPreview):
    def __init__(self, session, profile):
        LiquidPreview.__init__(self, session, None, {}, profile.max_groups)
        self.profile = profile

    def _start(self, signature):
        source = self.session.editor.document
        snapshot = Document(source.size, biome=source.biome)
        snapshot.blocks = source.blocks.copy()
        hidden, layer = frozenset(signature[2]), signature[3]
        def visible(position):
            return position[1] not in hidden and (layer is None or position[1] == layer)
        self.document = snapshot
        self.iterator = iter_render_steps(snapshot, self.profile, visible=visible)
        self.preparing = {}
