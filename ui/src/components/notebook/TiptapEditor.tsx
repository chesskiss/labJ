import React, { useEffect } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Highlight from "@tiptap/extension-highlight";

interface NotebookBlock {
  id: string;
  type: "paragraph" | "chart" | "graph" | "table";
  content: any;
}

interface Session {
  id: string;
  title: string;
  blocks: NotebookBlock[];
}

interface Props {
  session: Session;
  searchTerm: string;
}

export const TiptapEditor: React.FC<Props> = ({ session, searchTerm }) => {
  const editor = useEditor({
    extensions: [StarterKit, Highlight],
    content: blocksToHtml(session.blocks, searchTerm),
    autofocus: false,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      // TODO: send updated HTML or structured data to backend
      // e.g. POST /sessions/:id/content
      // console.log("updated content", html);
    },
  });

  useEffect(() => {
    if (!editor) return;

    const html = blocksToHtml(session.blocks, searchTerm);
    if (html !== editor.getHTML()) {
      editor.commands.setContent(html);
    }
  }, [editor, session.id, session.blocks, searchTerm]);

  return (
    <div className="tiptap-wrapper">
      <EditorContent editor={editor} />
    </div>
  );
};

// minimal conversion: in real life you’ll store structured blocks
function blocksToHtml(blocks: NotebookBlock[], searchTerm: string): string {
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
