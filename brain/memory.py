from threading import Lock


class Memory:
    def __init__(self):
        self._lock = Lock()

        # Voice commands history
        self._commands = []

        # Person presence 
        self._person_present = False

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def add_command(self, payload):
        """
        Add a recognized command to history.

        Args:
            payload: dict with 'text' and 'command' keys
        """
        with self._lock:
            self._commands.append(payload)
            return list(self._commands)

    def get_commands(self):
        """Returns a copy of the full command history."""
        with self._lock:
            return list(self._commands)

    def clear_commands(self):
        """Clears command history."""
        with self._lock:
            self._commands.clear()

    # ------------------------------------------------------------------
    # Person presence
    # ------------------------------------------------------------------

    def set_person_present(self, present):
        """
        Update person presence state.

        Args:
            present: bool
        """
        with self._lock:
            self._person_present = present

    def get_person_present(self):
        """Returns current person presence state."""
        with self._lock:
            return self._person_present

    # ------------------------------------------------------------------
    # Full snapshot (for UI)
    # ------------------------------------------------------------------

    def snapshot(self):
        """Returns the full current state as a dict."""
        with self._lock:
            return {
                'commands':       list(self._commands),
                'count':          len(self._commands),
                'person_present': self._person_present,
            }
