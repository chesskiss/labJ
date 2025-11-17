import React, { useEffect } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

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
}

export const TiptapEditor: React.FC<Props> = ({ session }) => {
  const editor = useEditor({
    extensions: [StarterKit],
    content: blocksToHtml(session.blocks),
    autofocus: false,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      // TODO: send updated HTML or structured data to backend
      // e.g. POST /sessions/:id/content
      // console.log("updated content", html);
    },
  });

  useEffect(() => {
    if (editor) {
      editor.commands.setContent(blocksToHtml(session.blocks));
    }
  }, [session.id]);

  return (
    <div className="tiptap-wrapper">
      <EditorContent editor={editor} />
    </div>
  );
};

// minimal conversion: in real life you’ll store structured blocks
function blocksToHtml(blocks: NotebookBlock[]): string {
  return blocks
    .map((b) => {
      if (b.type === "paragraph") {
        return `<p>${escapeHtml(String(b.content.text || ""))}</p>`;
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
