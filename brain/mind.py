class Mind:
    def __init__(self, memory, socketio):
        """
        Initialize the Mind module.

        Args:
            memory:   Memory instance — shared state store
            socketio: SocketIO instance — for emitting UI updates
        """
        self.memory = memory
        self.socketio = socketio

        # Device state — extend this as you add more devices
        self.devices = {
            'lights': False,
            'fan':    False,
            'music':  None,  # 'playing', 'paused', or None
        }

        # Command dispatcher — maps command codes to handler methods
        self._handlers = {
            'LIGHTS_ON':    self._lights_on,
            'LIGHTS_OFF':   self._lights_off,
            'FAN_ON':       self._fan_on,
            'FAN_OFF':      self._fan_off,
            'MUSIC_ON':     self._music_on,
            'PAUSE_MUSIC':  self._music_pause,
            'MUSIC_OFF':    self._music_off,
            'SHUTDOWN':     self._shutdown,
        }

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def process(self, payload):
        """
        Process an incoming command payload from the RPi.

        Args:
            payload: dict with 'text' and 'command' keys
        """
        command = payload.get('command')
        handler = self._handlers.get(command)

        if handler:
            handler()
            print(f"[Mind] Executed: {command}")
        else:
            print(f"[Mind] Unknown command: {command}")

        # Store in memory and broadcast updated state to UI
        # (skip logging SHUTDOWN — it's transient)
        if command != 'SHUTDOWN':
            commands = self.memory.add_command(payload)
            self._emit_state(commands)

    # ------------------------------------------------------------------
    # Device state emission
    # ------------------------------------------------------------------

    def _emit_state(self, commands=None):
        """Broadcasts current device state and command history to the UI."""
        if commands is None:
            commands = self.memory.get_commands()

        self.socketio.emit('state', {
            'devices': self.devices,
            'commands': commands,
            'count': len(commands),
        })

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _lights_on(self):
        self.devices['lights'] = True

    def _lights_off(self):
        self.devices['lights'] = False

    def _fan_on(self):
        self.devices['fan'] = True

    def _fan_off(self):
        self.devices['fan'] = False

    def _music_on(self):
        self.devices['music'] = 'playing'

    def _music_pause(self):
        if self.devices['music'] == 'playing':
            self.devices['music'] = 'paused'
        else:
            print("[MIND] Cannot pause music: music is not playing.")

    def _music_off(self):
        self.devices['music'] = None

    def _shutdown(self):
        """Tell the RPi to shut down, then shut down the brain."""
        print("[Mind] Shutdown command received. Notifying RPi...")
        self.socketio.emit('shutdown')
        # brain/main.py will wait for 'shutdown_ack' from the RPi before exiting