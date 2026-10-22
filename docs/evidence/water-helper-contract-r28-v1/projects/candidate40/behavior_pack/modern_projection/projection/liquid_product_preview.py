"""Product water uses its own draw selection and shared preview lifecycle."""
from .liquid_preview import LiquidPreview
from .liquid_product_plan import iter_group_steps
from .liquid_render_plan import render_steps
from .model import Document


class ProductLiquidPreview(LiquidPreview):
    def _start(self, signature):
        source = self.session.editor.document
        snapshot = Document(source.size, biome=source.biome)
        snapshot.blocks = source.blocks.copy()
        hidden, layer = frozenset(signature[2]), signature[3]
        def visible(pos):
            return pos[1] not in hidden and (layer is None or pos[1] == layer)
        provider = self.provider_factory(snapshot)
        groups = iter_group_steps(snapshot, provider, visible=visible)
        self.document = snapshot
        self.iterator = render_steps(groups, self.models, 1., self.max_groups)
        self.preparing = {}
