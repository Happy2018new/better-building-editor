# -*- coding: utf-8 -*-
"""Native pointer capture with a screen-wide release fallback."""


class PointerTracker(object):
    def __init__(self, host, fiber, motion, touch_mode=None):
        self.host, self.props, self.motion = host, {}, motion
        self.slot = {'fiber': fiber, 'active': False, 'callback': self.tick}
        self.origin = self.previous = self.args = None
        self.pressed = False
        self.hovered = False
        self.global_press = False
        self.touch_mode = touch_mode or (lambda: False)
        self.touch = False

    def send(self, name, args):
        callback = self.props.get(name)
        if callable(callback):
            callback(args)

    def down(self, args):
        if self.props.get('enabled') is False:
            return
        if self.pressed and self.global_press:
            self.global_press = False
            return
        if self.pressed:
            if self.touch and args.get('TouchId') != self.args.get('TouchId'):
                return
            self.cancel(args)
        touch = args.get('pointerKind') == 'touch' or self.touch_mode()
        self.touch = touch
        self.origin = self.previous = None if touch else self.motion.GetMousePosition()
        args = dict(args, pointerKind='touch' if touch else 'mouse')
        self.args = dict(args)
        self.pressed = True
        if not hasattr(self.host, '_projection_pointers'):
            self.host._projection_pointers = set()
        self.host._projection_pointers.add(self)
        self.send('onDown', args)
        if self.origin is not None:
            self.slot['active'] = True
            self.host.pyreact_register_animation_frame(self.slot)

    def position_args(self):
        args = dict(self.args)
        if self.previous is not None and self.origin is not None:
            args['TouchPosX'] += self.previous[0] - self.origin[0]
            args['TouchPosY'] += self.previous[1] - self.origin[1]
        return args

    def tick(self, unused):
        if not self.pressed:
            return
        current = self.motion.GetMousePosition()
        if current is None:
            self.cancel(self.args)
        elif current != self.previous:
            self.previous = current
            self.send('onMove', self.position_args())

    def stop(self):
        self.pressed = False
        self.global_press = False
        self.slot['active'] = False
        self.host.pyreact_unregister_animation_frame(self.slot)
        if hasattr(self.host, '_projection_pointers'):
            self.host._projection_pointers.discard(self)
        self.args = None

    def up(self, args):
        if not self.pressed:
            return
        if (self.touch or self.origin is None) and args.get('TouchId') not in (None, self.args.get('TouchId')):
            return
        if self.slot['active']:
            self.tick(0.)
        if not self.pressed:
            return
        # Global release need not contain a control-local touch position.
        final = self.position_args()
        if self.origin is None:
            final.update(args)
        self.stop()
        self.send('onUp', final)

    def cancel(self, args):
        if self.pressed:
            self.stop()
            self.send('onCancel', args)

    def move(self, args):
        if self.pressed:
            if self.origin is None:
                if args.get('TouchId') not in (None, self.args.get('TouchId')):
                    return
                self.args.update(args)
            self.send('onMove', args)

    def enter(self, args):
        self.hovered = True
        self.send('onEnter', args)

    def move_out(self, args):
        # ModSDK also emits this on a normal touch-screen release. Only PC
        # needs cancellation here; touch retains its up/cancel callbacks.
        if not self.touch and self.origin is not None and not self.props.get('retainCapture'):
            self.cancel(args)

    def leave(self, args):
        self.hovered = False
        if not self.touch and self.origin is not None and not self.props.get('retainCapture'):
            self.cancel(args)
        self.send('onLeave', args)

    def screen_down(self, args, point):
        # The native menu mapping continues firing when a block mesh upload
        # drops a control-local down. Native hover still owns hit testing, so
        # navigation buttons and the inspector keep priority over the canvas.
        hit_test = self.props.get('screenHit')
        if self.touch_mode() or point is None or self.pressed or not self.props.get('globalCapture'):
            return
        if not (hit_test(point) if callable(hit_test) else self.hovered):
            return
        event = dict(args, TouchPosX=point[0], TouchPosY=point[1])
        self.down(event)
        self.global_press = self.pressed


def release_pointers(host, args):
    """Local and global up may arrive in either order; finish each press once."""
    for tracker in tuple(getattr(host, '_projection_pointers', ())):
        if (not tracker.touch and tracker.origin is not None) or args.get('TouchId') is None or tracker.args.get('TouchId') in (None, args['TouchId']):
            tracker.up(args)
