# Product: Transcribe

## Problem & Value
- People and teams record calls, meetings, interviews, and podcasts but rarely re‑listen; searching by ear is slow and error‑prone.
- Existing transcription tools are either too complex for non‑technical users or too limited for developers who need an API.
- Transcribe provides a focused workflow: upload media, get a clean text transcript, and use it in downstream tools or workflows.

## Target Users
- Solo founders and small teams who need a simple SaaS to transcribe customer calls, demos, and interviews.
- Developers who want an authenticated HTTP API to offload transcription to a managed service.
- Internal users (you) while the product is in MVP/alpha stage, dogfooding the platform before wider release.

## Core Use Cases
- Upload an audio/video file, wait for processing, and download a `.txt` transcript.
- Decide whether diarization is needed (mono vs. dialogue mode) to better separate speakers.
- Store transcripts in a central place so they can be searched, shared, or copied into other tools.
- Run the stack locally or in Yandex Cloud for demos, internal usage, or early customer pilots.

## Main User Flows (High‑Level)
- **Authentication**
  - User signs up with email/password, confirms credentials, and receives a JWT for subsequent requests.
- **Upload & Job Creation**
  - User requests a presigned URL, uploads media to storage, and creates a transcription job tied to that file.
- **Processing & Status Tracking**
  - Background worker sends the file to the ASR provider, tracks status, and updates the job state until completion or failure.
- **Result Delivery**
  - User checks job status and, once ready, downloads the transcript as plain text (and optionally structured/diarized data later).

## Product Principles
- **MVP‑first** – ship a narrow but reliable core (auth, upload, transcription, download) before adding editing, search, or billing.
- **Predictable costs** – keep infrastructure simple (single FastAPI app, one database, one storage backend) to control usage and hosting costs.
- **Transparent failures** – when transcription fails, the product should surface clear status and error messages for debugging.

## Out of Scope (for the current MVP)
- Rich in‑browser transcript editing, comments, or collaboration.
- Complex billing/subscriptions and quota enforcement.
- Deep analytics on transcripts (topic modeling, summarization, etc.) beyond what can be layered on later.
