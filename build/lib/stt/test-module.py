from stt.stt import run_interactive


def on_segment(text: str):
    """Called each time a speech segment is transcribed."""
    print(f">> {text}")


full_text = run_interactive(on_transcription=on_segment)
