# stt/trigger.py


class TriggerEvaluator:
    """
    Evaluates transcribed text for control triggers.
    This version uses keyword matching, but can be upgraded later to use LLMs or NLP engines.
    """

    def __init__(self):
        self.stop_transcription_keywords = {
            "stop writing",
            "pause",
            "mute",
            "stop transcribing",
            "stop transcription",
        }
        self.start_transcription_keywords = {
            "start writing",
            "resume",
            "unmute",
            "start transcribing",
            "resume transcribing",
        }
        self.stop_listening_keywords = {
            "stop listening",
            "terminate",
            "shutdown",
        }
        self.new_session_keywords = {
            "new session",
            "new notebook",
            "start new session",
            "begin new session",
            "create new session",
        }
        self.create_note_keywords = {
            "create note",
            "new note",
            "sticky note",
            "make a note",
            "open note",
        }
        self.create_calculator_keywords = {
            "calculator",
            "open calculator",
            "calc",
            "calculate",
        }

    def evaluate(self, text):
        """
        Check the text for any control triggers.

        Returns:
            str or None: Action keyword like "pause_transcription", "resume_transcription", "stop_listening", "create_note", "create_calculator" or None
        """
        lowered = text.lower()

        if any(kw in lowered for kw in self.stop_listening_keywords):
            return "stop_listening"
        elif any(kw in lowered for kw in self.new_session_keywords):
            return "new_session"
        elif any(kw in lowered for kw in self.create_note_keywords):
            return "create_note"
        elif any(kw in lowered for kw in self.create_calculator_keywords):
            return "create_calculator"
        elif any(kw in lowered for kw in self.start_transcription_keywords):
            return "resume_transcription"
        elif any(kw in lowered for kw in self.stop_transcription_keywords):
            return "pause_transcription"
        else:
            return None

    def contains_any_keyword(self, text: str) -> bool:
        """Return True if text contains any known trigger keyword."""
        lowered = text.lower()
        all_keywords = (
            self.stop_transcription_keywords
            | self.start_transcription_keywords
            | self.stop_listening_keywords
            | self.new_session_keywords
            | self.create_note_keywords
            | self.create_calculator_keywords
        )
        return any(kw in lowered for kw in all_keywords)
