"""The live probe must observe water rather than a different liquid subclass."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from probe_liquid_workspace import WATER_OWNER_SELECT


class LiquidProjection:
    pass


class ProductLiquidProjection(LiquidProjection):
    pass


class CauldronProjection(LiquidProjection):
    pass


class ItemProjection(LiquidProjection):
    pass


class Companions:
    def __init__(self, *owners):
        self.companions = owners


def selected(owner):
    namespace = {'owner': owner, 'LiquidProjection': LiquidProjection,
                 'ProductLiquidProjection': ProductLiquidProjection}
    exec(WATER_OWNER_SELECT, namespace)
    return namespace['liquid']


class WaterProbeOwnerTest(unittest.TestCase):
    def test_single_water_owner(self):
        owner = LiquidProjection()
        self.assertIs(selected(owner), owner)

    def test_multisurface_owner_ignores_liquid_subclasses_in_any_order(self):
        cauldron, item = CauldronProjection(), ItemProjection()
        for owner in (LiquidProjection(), ProductLiquidProjection()):
            for others in ((cauldron, item, owner), (item, owner, cauldron), (owner, cauldron, item)):
                with self.subTest(order=others):
                    self.assertIs(selected(Companions(*others)), owner)

    def test_single_product_water_owner(self):
        owner = ProductLiquidProjection()
        self.assertIs(selected(owner), owner)

    def test_missing_water_has_no_selected_owner(self):
        for owner in (None, CauldronProjection(), ItemProjection(),
                      Companions(CauldronProjection(), ItemProjection())):
            with self.subTest(owner=owner):
                self.assertIsNone(selected(owner))


if __name__ == '__main__':
    unittest.main()
