# stt/context.py

"""
LLM-powered context processor for transcribed text.

This module processes raw Whisper transcriptions through an LLM to:
1. Understand user intent (command vs journal entry)
2. Extract tool calls via MCP-style function calling
3. Enhance journal text (grammar, filler removal, scientific structure)
4. Preserve raw transcription in metadata
"""

from typing import Dict, Any, List
from groq import Groq
import os
import json
from datetime import datetime


# System prompt for the LLM context layer
SYSTEM_PROMPT = """You are an intelligent lab journal assistant. Your job is to:

1. UNDERSTAND INTENT: Determine if the user is:
   - Giving a COMMAND (e.g., "open calculator", "pause writing", "new session")
   - Making a JOURNAL ENTRY (e.g., "write this down", "note that", "journal entry", or scientific observations)
   - BOTH (e.g., "Write down that I mixed 10mL... open calculator")
   - MEANINGLESS NOISE (single words, greetings like "okay", "hello", incomplete thoughts)

2. EXECUTE COMMANDS: Use the available tools to execute user commands:
   - create_calculator() - when user wants to perform calculations
   - create_note() - when user wants a sticky note
   - pause_transcription() - when user wants to stop writing
   - resume_transcription() - when user wants to resume writing
   - new_session() - when user wants to start a new session
   - stop_listening() - when user wants to shutdown

3. ENHANCE JOURNAL TEXT: For journal entries, clean and structure the text:
   - ONLY process as journal entry if user explicitly says to write/note/record something OR if it's a clear scientific observation
   - Fix grammar and spelling errors
   - Remove filler words (um, uh, like, you know, so, well, okay)
   - Structure as scientific observations when appropriate
   - Preserve technical terms and measurements EXACTLY as spoken
   - DO NOT change numbers or units
   - Use concise, professional lab notebook style

4. IGNORE NOISE: If the input is just:
   - Single words like "okay", "hello", "yes", "no"
   - Greetings or acknowledgments
   - Incomplete thoughts
   - Random filler
   RETURN: Empty text and no tool calls

5. JOURNAL ENTRY TRIGGERS: User must explicitly indicate they want to write something:
   - "Write down that..."
   - "Note that..."
   - "Journal entry..."
   - "Record this..."
   - OR it must be a clear scientific observation (e.g., "Added 5mL of buffer", "Temperature reached 37°C")

Examples:

Input: "Okay"
Output: ""
Tools: None

Input: "Hello"
Output: ""
Tools: None

Input: "New session"
Output: ""
Tools: new_session()

Input: "Write down that I added 5 milliliters of buffer to the sample"
Output: "Added 5mL of buffer to the sample."
Tools: None

Input: "Note that the reaction turned blue after adding the reagent"
Output: "Reaction turned blue after adding reagent."
Tools: None

Input: "Open calculator"
Output: ""
Tools: create_calculator()

Input: "Calculate 2 plus 2"
Output: ""
Tools: create_calculator(initial_expression="2+2")

Input: "I don't want to go"
Output: ""
Tools: None (casual speech, not a lab note or command)

CRITICAL RULES:
- NEVER modify numbers, measurements, or units
- NEVER add information that wasn't spoken
- BE CONCISE - lab notes should be brief and clear
- PRESERVE scientific terminology exactly
- IGNORE casual conversation, greetings, and incomplete thoughts
- ONLY write journal entries when explicitly requested OR when it's clearly a scientific observation
"""


class ContextProcessor:
    """
    LLM-powered context processor for transcribed text.

    Responsibilities:
    - Understand user intent (command vs journal entry)
    - Extract tool calls via MCP protocol
    - Enhance journal text (grammar, structure, filler removal)
    - Preserve raw transcription
    """

    def __init__(self, model: str = "llama-3.3-70b-versatile", enabled: bool = True):
        """
        Initialize the context processor.

        Args:
            model: Groq model to use for processing
            enabled: Whether context processing is enabled
        """
        self.model = model
        self.enabled = enabled

        if self.enabled:
            try:
                self.groq_client = Groq(api_key=os.getenv("LLM_API_KEY"))
                self.mcp_tools = self._initialize_mcp_tools()
                print(f"[ContextProcessor] Initialized with model: {model}")
            except Exception as e:
                print(f"[ContextProcessor] Failed to initialize: {e}")
                self.enabled = False
        else:
            print("[ContextProcessor] Disabled by configuration")

    def _initialize_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        Initialize MCP tool definitions following OpenAI function calling format.

        Returns:
            List of tool definitions
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_calculator",
                    "description": "Open a calculator subwindow for performing calculations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "initial_expression": {
                                "type": "string",
                                "description": "Optional initial expression to evaluate (e.g., '2+2', '5 ml to uL')",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_note",
                    "description": "Create a sticky note subwindow",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "initial_content": {
                                "type": "string",
                                "description": "Optional initial note content",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "pause_transcription",
                    "description": "Pause writing to the journal (still listens for commands)",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "resume_transcription",
                    "description": "Resume writing to the journal",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "new_session",
                    "description": "Start a new journal session",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Optional session title",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "stop_listening",
                    "description": "Completely shut down the voice assistant",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    def process(self, raw_text: str) -> Dict[str, Any]:
        """
        Process raw transcribed text with LLM.

        Args:
            raw_text: Raw transcription from Whisper

        Returns:
            {
                "enhanced_text": str,      # Cleaned, grammar-corrected text
                "raw_text": str,           # Original transcription
                "commands": List[Dict],    # Extracted MCP tool calls
                "intent": str,             # "command" | "journal" | "mixed" | "unknown"
                "metadata": Dict           # Processing metadata
            }
        """
        if not self.enabled:
            # If disabled, pass through without processing
            return {
                "enhanced_text": raw_text,
                "raw_text": raw_text,
                "commands": [],
                "intent": "journal",
                "metadata": {
                    "processed": False,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }

        try:
            # Build messages for LLM
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Transcribed text: {raw_text}"},
            ]

            # Call Groq with tool calling
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.mcp_tools,
                tool_choice="auto",  # Let LLM decide when to use tools
                temperature=0.3,  # Low temperature for consistent behavior
                max_tokens=500,
            )

            # Parse response
            message = response.choices[0].message

            # Extract tool calls (commands)
            commands = []
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    commands.append(
                        {"name": tool_call.function.name, "arguments": arguments}
                    )

            # Extract enhanced text from message content
            enhanced_text = message.content.strip() if message.content else ""

            # Determine intent
            if commands and not enhanced_text:
                intent = "command"
            elif enhanced_text and not commands:
                intent = "journal"
            elif commands and enhanced_text:
                intent = "mixed"
            else:
                intent = "unknown"

            return {
                "enhanced_text": enhanced_text,
                "raw_text": raw_text,
                "commands": commands,
                "intent": intent,
                "metadata": {
                    "model": self.model,
                    "processed": True,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }

        except Exception as e:
            print(f"[ContextProcessor] Error processing text: {e}")
            # Fallback to raw text on error
            return {
                "enhanced_text": raw_text,
                "raw_text": raw_text,
                "commands": [],
                "intent": "journal",
                "metadata": {
                    "processed": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }
