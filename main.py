"""
Main entry point for the voice-activated AI lab assistant.

This module orchestrates the flow of audio capture, speech-to-text transcription,
natural language processing, and visualization generation.
"""
import asyncio
import logging
from pathlib import Path


from audio.mic_stream import MicrophoneStream
from audio.audio_utils import AudioUtils
from stt.transcriber import Transcriber
from nlp.agent import LabAssistantAgent
from visualization.chart_generator import ChartGenerator
from ui.display import Display
from config import Config
import numpy as np

#TODO I want to encapsulate  more

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def is_stop_command(text: str) -> bool:
    """
    Check if the transcribed text contains a stop recording command.
    
    Args:
        text: Transcribed text to check
    
    Returns:
        True if text contains a stop command, False otherwise
    """
    if not text:
        return False
    
    text_lower = text.lower().strip()
    
    # Common stop recording phrases
    stop_phrases = [
        "stop recording",
        "stop listening",
        "stop the recording",
        "stop the microphone",
        "stop audio",
        "end recording",
        "quit recording",
        "exit recording",
        "that's all",
        "finished recording"
    ]
    
    # Check if any stop phrase is in the text
    for phrase in stop_phrases:
        if phrase in text_lower:
            return True
    
    return False


def main():
    """
    Main function that initializes and runs the lab assistant.
    
    The flow:
    1. Initialize audio stream
    2. Initialize transcriber
    3. Initialize NLP agent
    4. Initialize visualization components
    5. Start listening loop
    6. Process voice commands
    7. Generate charts/tables as needed
    8. Display results
    """
    logger.info("Starting Lab Assistant AI...")

    # Load configuration
    config = Config()

    # Initialize components
    mic_stream = MicrophoneStream(config.audio_config)
    transcriber = Transcriber(config.stt_config)
    agent = LabAssistantAgent(config.nlp_config)
    chart_generator = ChartGenerator(config.viz_config)
    display = Display(config.ui_config)

    # Start the main processing loop
    asyncio.run(run_assistant(mic_stream, transcriber, agent, chart_generator, display))

    logger.info("Lab Assistant AI stopped.")


async def run_assistant(mic_stream, transcriber, agent, chart_generator, display):
    """
    Main async loop for processing voice input and generating outputs.
    
    Args:
        mic_stream: Audio stream handler
        transcriber: Speech-to-text transcriber
        agent: NLP agent for intent extraction
        chart_generator: Chart/table generator
        display: Display handler for results
    
   The flow:
   1. Capture audio chunks from microphone
   2. Transcribe audio to text
   3. Parse intent and extract structured data
   4. Generate charts/tables based on commands
   5. Display or save results
   6. Handle errors gracefully
    """
    logger.info("Starting assistant processing loop...")
    
    try:
        # Get sample rate from mic_stream for transcription
        sample_rate = mic_stream.sample_rate
        logger.info(f"Using sample rate: {sample_rate} Hz")
        
        # Start audio stream
        if not mic_stream.is_streaming:
            mic_stream.start()
            logger.info("Audio stream started")
            logger.info("=" * 60)
            logger.info("MICROPHONE TEST MODE")
            logger.info("=" * 60)
            logger.info("The microphone is now active and listening.")
            logger.info("Make any noise (speak, clap, tap the mic) to test if it's working.")
            logger.info("You should see audio levels displayed below.")
            logger.info("=" * 60)
        
        # Process audio chunks
        chunk_count = 0
        audio_level_log_interval = 50  # Log audio levels every N chunks to avoid spam
        silence_threshold = 0.005  # RMS threshold below which audio is considered silence (lowered for sensitivity)
        max_rms_seen = 0.0  # Track maximum RMS level seen
        audio_detected_count = 0  # Count chunks with audio detected
        
        async for audio_chunk in mic_stream.stream_async():
            try:
                # Check if audio chunk is valid
                if audio_chunk is None or len(audio_chunk) == 0:
                    continue
                
                # Calculate audio levels to detect if microphone is receiving input
                # Flatten the audio chunk in case it's 2D
                if len(audio_chunk.shape) > 1:
                    audio_flat = audio_chunk.flatten()
                else:
                    audio_flat = audio_chunk
                
                # Calculate RMS (Root Mean Square) level
                rms_level = AudioUtils.calculate_rms(audio_flat)
                
                # Calculate peak level
                peak_level = np.max(np.abs(audio_flat))
                
                # Calculate dB level
                db_level = AudioUtils.calculate_db_level(audio_flat)
                
                # Detect if there's actual audio input (not just silence)
                has_audio = rms_level > silence_threshold
                
                # Track statistics
                if has_audio:
                    audio_detected_count += 1
                    max_rms_seen = max(max_rms_seen, rms_level)
                
                # Log audio levels periodically (every N chunks)
                chunk_count += 1
                if chunk_count % audio_level_log_interval == 0:
                    status = "🔊 AUDIO DETECTED" if has_audio else "🔇 Silent"
                    detection_rate = (audio_detected_count / chunk_count) * 100 if chunk_count > 0 else 0
                    
                    logger.info(
                        f"Audio levels - {status} | "
                        f"RMS: {rms_level:.6f} | "
                        f"Peak: {peak_level:.6f} | "
                        f"dB: {db_level:6.2f} | "
                        f"Max RMS seen: {max_rms_seen:.6f} | "
                        f"Detection rate: {detection_rate:.1f}% | "
                        f"Chunks processed: {chunk_count}"
                    )
                    
                    # Show audio level in display
                    if has_audio:
                        display.show_message(f"✅ Microphone working! Audio detected - RMS: {rms_level:.4f}, dB: {db_level:.1f}")
                    else:
                        display.show_message("🔇 Listening... (no audio detected - try speaking or making noise)")
                
                # Show continuous feedback for audio detection (real-time visualization)
                # Update every 5 chunks for smoother display
                if chunk_count % 5 == 0:
                    # Create a simple audio level bar
                    bar_length = 50
                    # Scale RMS for display (multiply by a factor to make it visible)
                    # For normalized audio (range -1 to 1), RMS of 0.1 is fairly loud
                    scaled_rms = min(rms_level * 20, 1.0)  # Scale up for visibility
                    bar_fill = int(scaled_rms * bar_length)
                    bar = "█" * bar_fill + "░" * (bar_length - bar_fill)
                    
                    # Color indicator based on audio level
                    if has_audio:
                        indicator = "🔊"
                        if rms_level > 0.1:
                            indicator = "🔊🔊"  # Very loud
                    else:
                        indicator = "🔇"
                    
                    # Print audio level with carriage return for updating in place
                    status_text = f"{indicator} Audio: [{bar}] RMS: {rms_level:.5f} Peak: {peak_level:.5f} dB: {db_level:7.2f}"
                    print(f"\r{status_text}", end="", flush=True)
                    
                    # Also print to log occasionally for debugging
                    if chunk_count % 200 == 0:
                        logger.debug(f"Real-time audio: RMS={rms_level:.6f}, Peak={peak_level:.6f}, dB={db_level:.2f}, HasAudio={has_audio}")
                
                # Transcribe audio to text
                # Note: We try transcription for all chunks, but it will return None if model isn't initialized
                text = await transcriber.transcribe(audio_chunk, sample_rate)
                
                # Debug: Log transcription attempts occasionally (only when audio is detected)
                if has_audio and chunk_count % 100 == 0:  # Log every 100 chunks when audio is present
                    logger.debug(f"Transcription attempt - RMS: {rms_level:.5f}, dB: {db_level:.2f}, Text result: {text}")
                
                if text and text.strip():
                    print()  # New line after audio level display
                    logger.info(f"✅ Transcribed: '{text}' (Audio level: RMS={rms_level:.5f}, dB={db_level:.2f})")
                    display.show_transcription(text)
                    
                    # Check for stop command - this must be checked before processing other intents
                    if is_stop_command(text):
                        logger.info("Stop recording command detected")
                        display.show_message("Stopping recording...")
                        break  # Exit the loop to stop recording
                    
                    # Parse intent from text
                    intent = await agent.parse_intent(text)
                    if intent:
                        logger.info(f"Parsed intent: {intent.type}")
                        
                        # Process intent and generate output
                        result = await process_intent(intent, chart_generator, display)
                        
                        # Display result
                        if result:
                            result_type = "chart" if hasattr(intent, 'chart_type') and intent.chart_type else "table"
                            await display.show(result, result_type=result_type)
                elif has_audio:
                    # We have audio but no transcription - this is useful for debugging
                    if chunk_count % 100 == 0:  # Only log occasionally
                        logger.warning(
                            f"⚠️  Audio detected but no transcription received - "
                            f"RMS: {rms_level:.5f}, dB: {db_level:.2f}, Peak: {peak_level:.5f}. "
                            f"STT model may not be initialized or audio may be too quiet."
                        )
                else:
                    # Very quiet or silent - this is normal
                    if chunk_count % 500 == 0:  # Log very occasionally
                        logger.debug(f"Silent chunk - RMS: {rms_level:.6f} (threshold: {silence_threshold})")
                        
            except Exception as e:
                logger.error(f"Error processing audio chunk: {e}", exc_info=True)
                continue
                
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Error in processing loop: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        print()  # New line after audio level display
        if mic_stream.is_streaming:
            mic_stream.stop()
        logger.info("=" * 60)
        logger.info("Recording stopped. Audio stream closed.")
        logger.info("=" * 60)


async def process_intent(intent, chart_generator, display):
    """
    Process the extracted intent and generate appropriate outputs.
    
    Args:
        intent: Parsed intent object with command type and data
        chart_generator: Chart/table generator instance
        display: Display handler for showing messages
    
    Returns:
        Generated visualization or data structure (path to file or DataFrame)
    
    TODO: Implement intent processing:
    1. Handle different intent types (chart, table, note, etc.)
    2. Extract data from intent
    3. Generate appropriate visualization
    4. Return result for display
    """
    from nlp.parser import IntentType
    
    try:
        if intent.type == IntentType.CREATE_CHART:
            # Prepare data from intent
            data = chart_generator.prepare_data_from_intent(intent)
            
            # Generate chart
            chart_path = await chart_generator.generate_chart(
                chart_type=intent.chart_type,
                data=data,
                title=intent.title,
                x_label=intent.x_label,
                y_label=intent.y_label
            )
            display.show_message(f"Generated chart: {chart_path}")
            return chart_path
        
        elif intent.type == IntentType.CREATE_TABLE:
            # TODO: Implement table generation
            from visualization.table_builder import TableBuilder
            table_builder = TableBuilder()
            table = table_builder.build_table_from_intent(intent)
            display.show_message("Generated table")
            return table
        
        elif intent.type == IntentType.ADD_DATA:
            # TODO: Implement data addition
            display.show_message("Data added successfully")
            return None
        
        else:
            display.show_message(f"Intent type {intent.type} not yet implemented")
            return None
    
    except Exception as e:
        logger.error(f"Error processing intent: {e}", exc_info=True)
        display.show_error(f"Error processing intent: {e}")
        return None


if __name__ == "__main__":
    main()

