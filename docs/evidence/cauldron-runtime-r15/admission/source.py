import mod.client.extraClientApi as api
import sys
system=api.GetSystem('NemcProjectionCleanDemo','Client')
_result={'runtime':api.GetMinecraftVersion(),'engine':api.GetEngineVersion(),'ui_initialized':bool(system and system.ui_initialized),'render_ticks':system.render_ticks if system else None,'top_ui':api.GetTopUI(),'foot':api.GetEngineCompFactory().CreatePos(api.GetLocalPlayerId()).GetFootPos(),'modern_projection_modules':[n for n in sys.modules if n=='modern_projection' or n.startswith('modern_projection.')]}
