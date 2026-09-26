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
        self.contacts = {}
        self.pinching = False
        self.pinch_pair = None

    def pinch_event(self, phase):
        pair = tuple(sorted(self.contacts)[:2])
        if phase != 'end' and len(pair) == 2 and pair != self.pinch_pair:
            phase = 'start'
        self.pinch_pair = pair
        self.send('onPinch', {'phase': phase, 'points': tuple(self.contacts[k] for k in pair)})

    def add_contact(self, args):
        identity = args.get('TouchId')
        if identity is None or identity < 0 or 'TouchPosX' not in args or 'TouchPosY' not in args:
            return False
        self.contacts[identity] = (args['TouchPosX'], args['TouchPosY'])
        return True

    def send(self, name, args):
        callback = self.props.get(name)
        if callable(callback):
            callback(args)

    def down(self, args):
        if self.props.get('enabled') is False:
            return
        if self.pressed and self.touch and callable(self.props.get('onPinch')):
            identity = args.get('TouchId')
            if identity in self.contacts:
                point = (args.get('TouchPosX'), args.get('TouchPosY'))
                previous = self.contacts[identity]
                if (point[0] is not None and point[1] is not None and
                        abs(point[0] - previous[0]) <= 4 and
                        abs(point[1] - previous[1]) <= 4):
                    self.global_press = False
                    return  # Duplicate global/local down for the same finger.
                # Android reuses TouchId after a lost up. A new down at a new
                # position starts a fresh gesture, never a move from old origin.
                self.cancel({})
            else:
                hit = self.props.get('screenHit')
                if callable(hit) and not hit((args.get('TouchPosX', -1), args.get('TouchPosY', -1))):
                    return
                if self.add_contact(args):
                    if len(self.contacts) >= 2:
                        if not self.pinching:
                            self.pinching = True
                            self.send('onCancel', args)  # A pinch can never become an edit.
                        self.pinch_event('move')
                    return
        if self.pressed and self.global_press:
            self.global_press = False
            return
        if self.pressed:
            if self.touch and args.get('TouchId') != self.args.get('TouchId'):
                return
            self.cancel(args)
        identity = args.get('TouchId')
        touch = (args.get('pointerKind') == 'touch' or self.touch_mode() or
                 (callable(self.props.get('onPinch')) and identity is not None and identity >= 0))
        self.touch = touch
        self.origin = self.previous = None if touch else self.motion.GetMousePosition()
        args = dict(args, pointerKind='touch' if touch else 'mouse')
        self.args = dict(args)
        if touch and callable(self.props.get('onPinch')):
            self.add_contact(args)
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
        self.contacts.clear()
        self.pinching = False
        self.pinch_pair = None

    def up(self, args):
        if not self.pressed:
            return
        if self.pinching:
            identity = args.get('TouchId')
            if identity is None:
                self.cancel(args)  # Ambiguous capture loss must not leave a pinch stuck.
            elif identity in self.contacts:
                del self.contacts[identity]
                if self.contacts:
                    self.pinch_event('move' if len(self.contacts) >= 2 else 'pause')
                else:
                    self.stop()
                    self.pinch_event('end')
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
            if self.pinching and args.get('TouchId') is not None:
                self.up(args)
                return
            if self.touch and args.get('TouchId') not in (None, self.args.get('TouchId')):
                return
            pinching = self.pinching
            self.stop()
            if pinching:
                self.pinch_event('end')
            self.send('onCancel', args)

    def move(self, args):
        if self.pressed:
            identity = args.get('TouchId')
            # Android reports every held finger here, but its button down/up
            # callbacks can describe only the first finger. Admit a second
            # contact from its first local move, while retaining hit testing.
            if (self.touch and callable(self.props.get('onPinch')) and
                    identity is not None and identity >= 0 and
                    identity not in self.contacts):
                self.down(args)
            if self.pinching:
                if identity in self.contacts:
                    self.add_contact(args)
                    if len(self.contacts) >= 2:
                        self.pinch_event('move')
                return
            if self.origin is None:
                if args.get('TouchId') not in (None, self.args.get('TouchId')):
                    return
                self.args.update(args)
                if identity in self.contacts:
                    self.add_contact(args)
            self.send('onMove', args)

    def touch_finished(self):
        """The multi_touch button is released after the final native finger."""
        if self.pinching:
            self.cancel({})

    def enter(self, args):
        self.hovered = True
        self.send('onEnter', args)

    def move_out(self, args):
        if self.touch:
            if args.get('TouchEvent') == 7:
                self.cancel({})
            elif (args.get('TouchEvent') == 6 and not self.pinching and
                  args.get('TouchId') in (None, self.args.get('TouchId') if self.args else None) and
                  args.get('TouchPosX') == 0 and args.get('TouchPosY') == 0):
                # Android sends this after release even if the local up was
                # dropped. A real viewport exit retains its nonzero position.
                self.cancel(args)
            return
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
        if self.touch and self.pressed and self.props.get('onPinch') and point is not None:
            if callable(hit_test) and hit_test(point):
                self.down(dict(args, TouchPosX=point[0], TouchPosY=point[1]))
            return
        if point is None or self.pressed or not self.props.get('globalCapture'):
            return
        if not (hit_test(point) if callable(hit_test) else self.hovered):
            return
        event = dict(args, TouchPosX=point[0], TouchPosY=point[1])
        self.down(event)
        self.global_press = self.pressed

    def native_touch(self, args):
        """Route explicit contact events (also used by debug replay)."""
        if self.props.get('enabled') is False or (not self.touch_mode() and
                not callable(self.props.get('onPinch'))):
            return
        phase = args.get('TouchEvent', args.get('ButtonState', -1))
        identity = args.get('TouchId')
        if phase == 7:
            self.cancel({})
        elif phase in (0, 3):
            if identity is not None:
                (self.up if phase == 0 else self.cancel)(args)
        elif identity is not None and identity >= 0:
            if 'TouchPosX' not in args or 'TouchPosY' not in args:
                return
            if phase == 1 and identity not in self.contacts:
                self.screen_down(args, (args['TouchPosX'], args['TouchPosY']))
            if phase != 1 and identity in self.contacts:
                self.move(args)


def release_pointers(host, args):
    """Local and global up may arrive in either order; finish each press once."""
    for tracker in tuple(getattr(host, '_projection_pointers', ())):
        if tracker.pinching or (not tracker.touch and tracker.origin is not None) or args.get('TouchId') is None or tracker.args.get('TouchId') in (None, args['TouchId']):
            tracker.up(args)
