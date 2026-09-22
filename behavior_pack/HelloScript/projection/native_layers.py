"""Batch camera-only UI layer writes without repeating input routing rebuilds."""


def apply_layers(updates):
    if not updates:
        return
    try:
        import gui
    except ImportError:
        gui = None
    original = getattr(gui, 'handle_input_mode_change', None)
    pending = []

    def defer(*args, **kwargs):
        call = (args, kwargs)
        if call not in pending:
            pending.append(call)

    # Netease 3.9's public SetLayer calls this Python helper even with both
    # refresh flags False. A 104-tile order change otherwise rebuilds the same
    # native input routes 105 times (~180 ms). Only coalesce the synchronous
    # batch; restore the engine helper before replay, including on exceptions.
    # Other engine versions retain the public API path if no helper exists.
    if callable(original):
        gui.handle_input_mode_change = defer
    try:
        for control, layer in updates:
            control.SetLayer(layer, False, False)
        control, layer = updates[-1]
        control.SetLayer(layer, False, True)
    finally:
        if callable(original):
            gui.handle_input_mode_change = original
            for args, kwargs in pending:
                original(*args, **kwargs)
