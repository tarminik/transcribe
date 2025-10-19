from calendar import c
from config import env_settings
from pathlib import Path  # used to derive output .txt path from audio file name
import assemblyai as aai

aai.settings.api_key = env_settings.assemblyai.api_key

audio_file = "./2025-07-08 14-32-08.mkv"

config = aai.TranscriptionConfig(
    language_code="ru",
    speaker_labels=True,
)

transcript = aai.Transcriber().transcribe(audio_file, config=config)

if transcript.status == "error":
  raise RuntimeError(f"Transcription failed: {transcript.error}")

# Print diarized speaker-labeled utterances
for utterance in (transcript.utterances or []):
  print(f"Speaker {utterance.speaker}: {utterance.text}")

# Save the transcript text to a .txt file near the audio file
# We keep it simple: same base name, .txt extension, UTF-8 encoding for Cyrillic
output_txt_path = Path(audio_file).with_suffix(".txt")

# Prepare diarized lines for saving; fallback to full text if no utterances
diarized_lines = [f"Speaker {u.speaker}: {u.text}" for u in (transcript.utterances or [])]
if not diarized_lines:
  diarized_lines = [transcript.text or ""]

output_txt_path.write_text("\n".join(diarized_lines), encoding="utf-8")
print(f"Saved transcript to {output_txt_path}")
