import { useEffect, useRef, useState } from "react";

interface VoiceCaptureDockProps {
  isOpen: boolean;
  promptDraft: string;
  isSending: boolean;
  onToggleOpen: () => void;
  onPromptChange: (value: string) => void;
  onSendPrompt: () => void;
  onClose: () => void;
}

interface ThreadMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
}

type MicState = "idle" | "listening" | "processing";

function buildMockResponse(prompt: string): string {
  return `Mocked assistant: captured intent from "${prompt}". Backend integration is disabled in this phase.`;
}

export function VoiceCaptureDock({
  isOpen,
  promptDraft,
  isSending,
  onToggleOpen,
  onPromptChange,
  onSendPrompt,
  onClose,
}: VoiceCaptureDockProps) {
  const [thread, setThread] = useState<ThreadMessage[]>([
    {
      id: "assistant-init",
      role: "assistant",
      text: "Voice assistant ready. Use this panel to draft LLM prompts during your experiment.",
    },
  ]);

  const lastSubmittedPromptRef = useRef<string | null>(null);
  const prevSendingRef = useRef<boolean>(isSending);
  const threadScrollRef = useRef<HTMLDivElement | null>(null);

  const micState: MicState = isSending ? "processing" : isOpen ? "listening" : "idle";

  useEffect(() => {
    const previouslySending = prevSendingRef.current;
    if (previouslySending && !isSending && lastSubmittedPromptRef.current) {
      const previousPrompt = lastSubmittedPromptRef.current;
      setThread((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          text: buildMockResponse(previousPrompt),
        },
      ]);
      lastSubmittedPromptRef.current = null;
    }

    prevSendingRef.current = isSending;
  }, [isSending]);

  useEffect(() => {
    if (!threadScrollRef.current) {
      return;
    }
    threadScrollRef.current.scrollTop = threadScrollRef.current.scrollHeight;
  }, [thread, isOpen]);

  const handleSend = () => {
    const trimmed = promptDraft.trim();
    if (!trimmed.length || isSending) {
      return;
    }

    setThread((current) => [
      ...current,
      {
        id: `user-${Date.now()}`,
        role: "user",
        text: trimmed,
      },
    ]);

    lastSubmittedPromptRef.current = trimmed;
    onSendPrompt();
  };

  return (
    <section className="voiceDock" aria-label="Voice prompt control">
      <button
        type="button"
        className={`floatingMic ${micState}`}
        onClick={onToggleOpen}
        aria-label={isOpen ? "Hide voice prompt panel" : "Show voice prompt panel"}
      >
        <svg className="micGlyph" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 3a3 3 0 0 0-3 3v5a3 3 0 1 0 6 0V6a3 3 0 0 0-3-3Zm5 8a1 1 0 1 0-2 0 3 3 0 0 1-6 0 1 1 0 1 0-2 0 5 5 0 0 0 4 4.9V18H9a1 1 0 1 0 0 2h6a1 1 0 1 0 0-2h-2v-2.1A5 5 0 0 0 17 11Z" />
        </svg>
      </button>

      {isOpen && (
        <div className="voicePromptPanel">
          <div className="voicePanelHeader">
            <div>
              <h3 className="voicePanelTitle">Voice Prompt</h3>
              <p className="voicePanelState">State: {micState}</p>
            </div>
            <button type="button" className="voicePanelClose" onClick={onClose}>
              Close
            </button>
          </div>

          <div className="voiceThread" ref={threadScrollRef}>
            {thread.map((message) => (
              <div key={message.id} className={`voiceMessage ${message.role}`}>
                <span className="voiceMessageRole">{message.role === "user" ? "You" : "Assistant"}</span>
                <p>{message.text}</p>
              </div>
            ))}

            {isSending && (
              <div className="voiceMessage assistant thinking">
                <span className="voiceMessageRole">Assistant</span>
                <p>Thinking...</p>
              </div>
            )}
          </div>

          <div className="voiceComposer">
            <textarea
              className="voicePromptInput"
              rows={3}
              value={promptDraft}
              onChange={(event) => onPromptChange(event.target.value)}
              placeholder="Prompt the LLM (mock): summarize transcript, propose next lab step, or format notes."
            />
            <div className="voicePanelActions">
              <button
                type="button"
                className="primaryButton"
                onClick={handleSend}
                disabled={!promptDraft.trim().length || isSending}
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
