"""Book preview plans share the established native control lifetime."""
from .portal_preview import PortalPreview
from .book_render_plan import iter_render_steps
from .model import Document


class BookPreview(PortalPreview):
    def _start(self,signature):
        source=self.session.editor.document
        snapshot=Document(source.size,biome=source.biome)
        snapshot.blocks=source.blocks.copy()
        hidden,layer=frozenset(signature[2]),signature[3]
        def visible(position):
            return position[1] not in hidden and (layer is None or position[1]==layer)
        self.document=snapshot
        self.iterator=iter_render_steps(snapshot,self.profile,visible=visible)
        self.preparing={}
