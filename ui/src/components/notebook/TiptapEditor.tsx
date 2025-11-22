import React, { useEffect } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Highlight from "@tiptap/extension-highlight";

interface NotebookBlock {
  id: string;
  type: "paragraph" | "chart" | "graph" | "table" | "log";
  content: any;
}

interface Session {
  id: string;
  title: string;
  blocks: NotebookBlock[];
}

interface Props {
  session: Session;
  html: string;
  isDirty: boolean;
  onChange: (html: string) => void;
}

export const TiptapEditor: React.FC<Props> = ({ session, html, isDirty, onChange }) => {
  const editor = useEditor({
    extensions: [StarterKit, Highlight],
    content: html,
    autofocus: false,
    onUpdate: ({ editor }) => {
      const nextHtml = editor.getHTML();
      const isFocused =
        typeof (editor as any).isFocused === "function"
          ? (editor as any).isFocused()
          : !!(editor as any).isFocused;

      if (isFocused) {
        onChange(nextHtml);
      }
    },
  });

  useEffect(() => {
    if (!editor) return;

    if (!isDirty && html !== editor.getHTML()) {
      editor.commands.setContent(html);
    }
  }, [editor, session.id, html, isDirty]);

  return (
    <div className="tiptap-wrapper">
      <EditorContent editor={editor} />
    </div>
  );
};

// minimal conversion: in real life you’ll store structured blocks
export function blocksToHtml(blocks: NotebookBlock[], searchTerm: string): string {
  return blocks
    .map((b) => {
      if (b.type === "paragraph") {
        return `<p>${highlightText(String(b.content.text || ""), searchTerm)}</p>`;
      }
      if (b.type === "chart") {
        return `<p>[Chart: ${escapeHtml(b.content.title || "Chart")}]</p>`;
      }
      return `<p>${escapeHtml(JSON.stringify(b.content))}</p>`;
    })
    .join("\n");
}

function escapeHtml(text: string): string {
  return text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function highlightText(text: string, term: string): string {
  const query = term.trim();
  if (!query) return escapeHtml(text);

  try {
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(escaped, "gi");
    let lastIndex = 0;
    let result = "";
    let match: RegExpExecArray | null;

    while ((match = re.exec(text)) !== null) {
      result += escapeHtml(text.slice(lastIndex, match.index));
      result += `<mark class="search-highlight">${escapeHtml(match[0])}</mark>`;
      lastIndex = match.index + match[0].length;
    }

    result += escapeHtml(text.slice(lastIndex));
    return result;
  } catch {
    return escapeHtml(text);
  }
}
