import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  type FormEvent,
} from "react";
import type { ToolbarAction, VoiceCaptureMode } from "../../types";

export interface JournalEditorHandle {
  focus: () => void;
  runToolbarAction: (action: ToolbarAction) => void;
  insertTranscript: (text: string, options: { asStep: boolean; mode: VoiceCaptureMode }) => void;
}

interface JournalEditorProps {
  entryId: string;
  initialContent: string;
  onContentChange: (html: string) => void;
  onBlur?: () => void;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export const JournalEditor = forwardRef<JournalEditorHandle, JournalEditorProps>(
  function JournalEditor({ entryId, initialContent, onContentChange, onBlur }, ref) {
    const editorRef = useRef<HTMLDivElement | null>(null);
    const lastEntryIdRef = useRef<string | null>(null);

    useEffect(() => {
      const editor = editorRef.current;
      if (!editor) {
        return;
      }

      const entryChanged = lastEntryIdRef.current !== entryId;
      lastEntryIdRef.current = entryId;

      if (entryChanged) {
        editor.innerHTML = initialContent;
        return;
      }

      // Do not rewrite while user is typing in this entry; it resets caret selection.
      if (document.activeElement === editor) {
        return;
      }

      if (editor.innerHTML !== initialContent) {
        editor.innerHTML = initialContent;
      }
    }, [entryId, initialContent]);

    const notifyContentChange = () => {
      if (!editorRef.current) {
        return;
      }
      onContentChange(editorRef.current.innerHTML);
    };

    const ensureFocus = () => {
      editorRef.current?.focus();
    };

    const getWorkingRange = (): Range | null => {
      if (!editorRef.current) {
        return null;
      }

      const selection = window.getSelection();
      if (selection && selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        if (editorRef.current.contains(range.commonAncestorContainer)) {
          return range;
        }
      }

      const fallbackRange = document.createRange();
      fallbackRange.selectNodeContents(editorRef.current);
      fallbackRange.collapse(false);
      return fallbackRange;
    };

    const insertHtmlAtCursor = (html: string) => {
      if (!editorRef.current) {
        return;
      }

      ensureFocus();
      const selection = window.getSelection();
      const range = getWorkingRange();

      if (!range) {
        return;
      }

      range.deleteContents();
      const template = document.createElement("template");
      template.innerHTML = html;
      const fragment = template.content;
      const lastNode = fragment.lastChild;

      range.insertNode(fragment);

      if (selection) {
        const nextRange = document.createRange();
        if (lastNode) {
          nextRange.setStartAfter(lastNode);
        } else {
          nextRange.selectNodeContents(editorRef.current);
          nextRange.collapse(false);
        }
        nextRange.collapse(true);
        selection.removeAllRanges();
        selection.addRange(nextRange);
      }

      notifyContentChange();
    };

    const runToolbarAction = (action: ToolbarAction) => {
      ensureFocus();

      switch (action) {
        case "bold":
          document.execCommand("bold");
          break;
        case "italic":
          document.execCommand("italic");
          break;
        case "bullet":
          document.execCommand("insertUnorderedList");
          break;
        case "heading":
          document.execCommand("formatBlock", false, "h2");
          break;
        case "checkbox":
          insertHtmlAtCursor("<p><span>[ ]</span> </p>");
          return;
        case "table":
          insertHtmlAtCursor(
            "<table class='editorTable'><tbody><tr><th>Column A</th><th>Column B</th></tr><tr><td>Value</td><td>Value</td></tr></tbody></table><p></p>"
          );
          return;
        case "attach":
          insertHtmlAtCursor("<p><span class='editorAttachment'>Attachment: assay_image.png</span></p>");
          return;
        default:
          break;
      }

      notifyContentChange();
    };

    const insertTranscript = (
      text: string,
      options: {
        asStep: boolean;
        mode: VoiceCaptureMode;
      }
    ) => {
      const cleaned = escapeHtml(text.trim());
      if (!cleaned.length) {
        return;
      }

      const now = new Date();
      const timestamp = now.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });

      if (options.asStep) {
        insertHtmlAtCursor(`<p><strong>Step:</strong> [ ] ${cleaned}</p>`);
        return;
      }

      if (options.mode === "note") {
        insertHtmlAtCursor(`<p><em>Note ${timestamp}</em>: ${cleaned}</p>`);
        return;
      }

      if (options.mode === "command") {
        insertHtmlAtCursor(`<p><strong>Command</strong>: ${cleaned}</p>`);
        return;
      }

      insertHtmlAtCursor(`<p>${cleaned}</p>`);
    };

    useImperativeHandle(
      ref,
      () => ({
        focus: ensureFocus,
        runToolbarAction,
        insertTranscript,
      }),
      []
    );

    const handleInput = (event: FormEvent<HTMLDivElement>) => {
      onContentChange((event.currentTarget as HTMLDivElement).innerHTML);
    };

    const handleBlur = () => {
      notifyContentChange();
      onBlur?.();
    };

    return (
      <div className="journalEditorWrap">
        <div className="editorHint">Voice transcript insert target</div>
        <div
          ref={editorRef}
          className="journalEditor"
          contentEditable
          suppressContentEditableWarning
          onInput={handleInput}
          onBlur={handleBlur}
          aria-label="Journal editor"
        />
      </div>
    );
  }
);
