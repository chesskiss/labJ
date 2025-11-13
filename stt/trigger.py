# stt/trigger.py

class TriggerEvaluator:
    """
    Evaluates transcribed text for control triggers.
    This version uses keyword matching, but can be upgraded later to use LLMs or NLP engines.
    """

    def __init__(self):
        self.stop_transcription_keywords = {"stop writing", "pause", "mute"}
        self.start_transcription_keywords = {"start writing", "resume", "unmute"}
        self.stop_listening_keywords = {"stop listening", "terminate", "shutdown"}

    def evaluate(self, text):
        """
        Check the text for any control triggers.

        Returns:
            str or None: Action keyword like "pause_transcription", "resume_transcription", "stop_listening" or None
        """
        lowered = text.lower()

        if any(kw in lowered for kw in self.stop_listening_keywords):
            return "stop_listening"
        elif any(kw in lowered for kw in self.start_transcription_keywords):
            return "resume_transcription"
        elif any(kw in lowered for kw in self.stop_transcription_keywords):
            return "pause_transcription"
        else:
            return None
