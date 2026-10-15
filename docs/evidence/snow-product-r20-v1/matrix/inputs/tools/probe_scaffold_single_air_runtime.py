"""Single-cell v2 control with native palette proof and independent air encoding.

Setter return False remains visible and is never described as successful. The
physical restoration is separately established by both native layer buckets.
"""
import probe_scaffold_single_air_control as base
from scaffold_native_palette_readback import HELPER

KIND = 'scaffold_single_air_native_palette_control'
METHOD = 'single near air/stone/dual-air; raw states and true two-layer palette; physical restore independent of setter bool; v2'


def _replace(code, before, after):
    if code.count(before) != 1:
        raise ValueError('Archived single-air template changed; review native palette control')
    return code.replace(before, after, 1)


def native_code():
    code = _replace(base.SERVER, repr(base.KIND), repr(KIND))
    code = _replace(code, repr(base.METHOD), repr(METHOD))
    helper = '\n'.join(' ' + line if line else '' for line in HELPER.splitlines())
    code = _replace(code, ' def read(at):', helper + '\n def read(at):')
    code = _replace(code, "'states':state.GetBlockStates(at,dimension),'liquid':info.GetLiquidBlock(at,dimension)}",
                    "'states':state.GetBlockStates(at,dimension),'liquid':info.GetLiquidBlock(at,dimension),'palette':palette_read(at)}")
    code = _replace(code, "assert dry_air(result['initial']),'Reserve is not dry air'",
                    "assert dry_air(result['initial']) and palette_air(result['initial']['palette']),'Reserve is not verified dual-layer air'")
    code = _replace(code, "assert returned is True and dry_air(result['explicit_air']['readback']),'Explicit air write failed'",
                    "assert type(returned) is bool and dry_air(result['explicit_air']['readback']) and palette_air(result['explicit_air']['readback']['palette']),'Explicit air physical readback failed'")
    code = _replace(code, "result['restored']=returned is True and dry_air(actual)",
                    "result['cleanup']['setter_success']=returned is True\n   result['cleanup']['physical_readback_verified']=dry_air(actual) and palette_air(actual['palette'])\n   result['restored']=type(returned) is bool and result['cleanup']['physical_readback_verified']")
    return code


def payload(player, foot, dimension, pos, air_encoding):
    config = {'runtime': base.RUNTIME, 'player': player, 'foot': tuple(foot), 'dimension': dimension,
              'pos': tuple(pos), 'air_encoding': air_encoding}
    return native_code().replace('__CONFIG__', repr(config))
