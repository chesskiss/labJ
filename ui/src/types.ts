
// High-level summary for the left sidebar
export interface SessionSummary {
    id: number;            // matches SQLite sessions.id
    title: string;         // sessions.title or derived
    description: string;   // optional, can be empty for now
    isFavorite: boolean;   // eventually can come from metadata
  }
  
  // Notebook block types – what the center editor renders
  export type BlockType = "paragraph" | "chart" | "graph" | "table";
  
  export interface BlockContent {
    text?: string;
    source?: string;        // "stt", "manual", etc.
    start_time?: string;    // ISO string from utterances.start_time
    end_time?: string;      // ISO string from utterances.end_time
    // later you can add more fields (tags, confidence, etc.)
  }
  
  export interface NotebookBlock {
    id: string;             // e.g. "utt-12"
    type: BlockType;
    content: BlockContent;
  }
  
  // Full session with blocks – for the notebook in the middle
  export interface NotebookSession {
    id: number;
    title: string;
    blocks: NotebookBlock[];
  }
  
  // Command response from /commands
  export interface CommandResponse {
    status: "ok" | "error";
    applied: {
      type: string;         // "NEW_SESSION" | "APPEND_NOTE" | "CREATE_DEFAULT_SESSION"
      session_id?: number;
      title?: string;
    };
  }
  