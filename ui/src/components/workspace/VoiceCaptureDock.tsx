interface VoiceCaptureDockProps {
  micState: "idle" | "listening" | "processing";
  onToggleMic: () => void;
}

export function VoiceCaptureDock({
  micState,
  onToggleMic,
}: VoiceCaptureDockProps) {
  const label =
    micState === "listening"
      ? "Stop recording"
      : micState === "processing"
        ? "Mic processing"
        : "Start recording";

  return (
    <section className="voiceDock" aria-label="Voice capture control">
      <button
        type="button"
        className={`floatingMic ${micState}`}
        onClick={onToggleMic}
        aria-label={label}
      >
        <svg className="micGlyph" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 3a3 3 0 0 0-3 3v5a3 3 0 1 0 6 0V6a3 3 0 0 0-3-3Zm5 8a1 1 0 1 0-2 0 3 3 0 0 1-6 0 1 1 0 1 0-2 0 5 5 0 0 0 4 4.9V18H9a1 1 0 1 0 0 2h6a1 1 0 1 0 0-2h-2v-2.1A5 5 0 0 0 17 11Z" />
        </svg>
      </button>
      <div className="voiceDockStatus" role="status" aria-live="polite">
        Mic: {micState}
      </div>
    </section>
  );
}
