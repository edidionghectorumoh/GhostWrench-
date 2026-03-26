# Requirements Document

## Introduction

This document specifies the requirements for integrating Chainlit as the web-based chat UI for the Ghostwrench Autonomous Field Engineer (AFE) system and upgrading to the latest Amazon Nova 2 model family. The current system is CLI-only (`main.py` with argparse) and uses first-generation Nova models. The Chainlit UI will provide field technicians with an interactive chat interface that supports image uploads for equipment diagnosis, real-time workflow phase tracking, escalation handling through conversational prompts, and voice-guided repair sessions. The Nova model upgrade will switch to Nova 2 Lite (`us.amazon.nova-2-lite-v1:0`) for reasoning, Nova 2 Sonic for voice AI, and Nova Multimodal Embeddings (`amazon.nova-2-multimodal-embeddings-v1:0`) for the RAG system. This integration targets the Amazon Nova AI Hackathon on Devpost, covering the Agentic AI, Multimodal Understanding, Voice AI, and Freestyle categories.

## Glossary

- **Chainlit_App**: The Chainlit-based web application module (`chainlit_app.py`) that serves as the chat UI entry point and wires user interactions to the OrchestrationLayer.
- **OrchestrationLayer**: The existing Python class (`src/orchestration/OrchestrationLayer.py`) that coordinates the multi-agent workflow through phases: Intake → Diagnosis → Procurement → Guidance → Completion.
- **DiagnosisAgent**: The AI agent powered by Amazon Nova 2 Lite (`us.amazon.nova-2-lite-v1:0`) that performs multimodal image analysis and issue diagnosis with extended thinking capabilities.
- **ActionAgent**: The AI agent powered by Amazon Nova Act that handles parts procurement and inventory management through agentic tool-calling.
- **GuidanceAgent**: The AI agent powered by Amazon Nova 2 Sonic that provides real-time speech-to-speech voice-guided repair instructions and processes voice commands.
- **CloudJudge**: The validation layer using Claude 3.5 Sonnet and Nova 2 Lite that enforces safety, SOP compliance, and budget rules.
- **Nova_Multimodal_Embeddings**: The Amazon Nova Multimodal Embeddings model (`amazon.nova-2-multimodal-embeddings-v1:0`) that generates unified embeddings for text, images, and documents in a single semantic space, replacing Amazon Titan Embeddings and CLIP.
- **Workflow_Phase**: One of the five sequential stages of a field request: INTAKE, DIAGNOSIS, PROCUREMENT, GUIDANCE, COMPLETION.
- **Escalation**: A situation requiring human decision-making, triggered by safety violations, budget overruns, or low-confidence diagnoses.
- **Field_Technician**: The end user who interacts with the Chainlit_App to submit diagnosis requests and receive repair guidance.
- **Step_Indicator**: A Chainlit Step UI element that visually represents the current Workflow_Phase and agent activity within the chat interface.
- **Gate**: A validation checkpoint (safety gate, confidence gate, or budget gate) enforced by the CloudJudge before a phase transition occurs.

## Requirements

### Requirement 1: Chainlit Application Entry Point

**User Story:** As a Field_Technician, I want to open a web-based chat interface, so that I can interact with the AFE system without using the command line.

#### Acceptance Criteria

1. WHEN the Chainlit_App is started, THE Chainlit_App SHALL initialize an OrchestrationLayer instance and present a chat welcome message to the Field_Technician.
2. WHEN a Field_Technician sends a text message in the chat, THE Chainlit_App SHALL create a FieldRequest with request_type DIAGNOSIS and forward the message to OrchestrationLayer.process_field_request.
3. THE Chainlit_App SHALL display all agent responses as chat messages in the Chainlit conversation thread.
4. IF the OrchestrationLayer raises an unhandled exception, THEN THE Chainlit_App SHALL display a user-friendly error message in the chat and log the full exception details.

### Requirement 2: Image Upload for Diagnosis

**User Story:** As a Field_Technician, I want to upload equipment photos through the chat interface, so that the DiagnosisAgent can analyze them for issues.

#### Acceptance Criteria

1. WHEN a Field_Technician uploads an image file through the Chainlit file upload widget, THE Chainlit_App SHALL read the image bytes and construct an ImageData object with a generated image_id, the raw bytes, and the current timestamp.
2. WHEN an ImageData object is constructed from an uploaded file, THE Chainlit_App SHALL include the ImageData in the FieldRequest.image_data field before forwarding to the OrchestrationLayer.
3. IF a Field_Technician uploads a file that is not a supported image format (JPEG, PNG, BMP, TIFF), THEN THE Chainlit_App SHALL reject the upload and display a message listing the supported formats.
4. WHEN the DiagnosisAgent returns an AnnotatedImage in the DiagnosisResult, THE Chainlit_App SHALL render the annotated image inline in the chat conversation.

### Requirement 3: Workflow Phase Visualization

**User Story:** As a Field_Technician, I want to see which workflow phase is currently active, so that I understand the progress of my field request.

#### Acceptance Criteria

1. WHEN the OrchestrationLayer transitions to a new Workflow_Phase, THE Chainlit_App SHALL create a Chainlit Step_Indicator with the phase name (INTAKE, DIAGNOSIS, PROCUREMENT, GUIDANCE, or COMPLETION) as the step title.
2. WHILE a Workflow_Phase is in progress, THE Chainlit_App SHALL display a loading indicator within the corresponding Step_Indicator.
3. WHEN a Workflow_Phase completes, THE Chainlit_App SHALL update the Step_Indicator to show a completion status and include a summary of the phase output.
4. WHEN the DIAGNOSIS phase completes, THE Chainlit_App SHALL display the issue type, severity, confidence score, root cause, and recommended actions from the DiagnosisResult within the Step_Indicator.
5. WHEN the PROCUREMENT phase completes, THE Chainlit_App SHALL display the list of required parts, total cost, and estimated delivery date from the ProcurementState within the Step_Indicator.

### Requirement 4: Escalation Handling Through Chat

**User Story:** As a Field_Technician, I want to respond to safety, budget, and confidence escalations directly in the chat, so that the workflow can proceed without switching to a different interface.

#### Acceptance Criteria

1. WHEN the CloudJudge triggers a safety escalation, THE Chainlit_App SHALL display the safety violation details, required precautions, and PPE requirements as a structured message, and prompt the Field_Technician for acknowledgment.
2. WHEN the CloudJudge triggers a budget escalation, THE Chainlit_App SHALL display the total cost, budget limit, and required approval level, and prompt the Field_Technician to approve, reject, or request alternatives.
3. WHEN a confidence gate fails (confidence score below the quality threshold), THE Chainlit_App SHALL display the low-confidence diagnosis details and prompt the Field_Technician to confirm, reject, or request re-diagnosis.
4. WHEN the Field_Technician responds to an escalation prompt, THE Chainlit_App SHALL forward the resolution to OrchestrationLayer.resolve_escalation and resume the workflow.
5. IF an escalation remains unresolved for more than 5 minutes, THEN THE Chainlit_App SHALL send a reminder message to the Field_Technician.

### Requirement 5: Agent Response Streaming

**User Story:** As a Field_Technician, I want to see agent responses appear progressively in the chat, so that I receive feedback during long-running operations.

#### Acceptance Criteria

1. WHILE the DiagnosisAgent is processing an image, THE Chainlit_App SHALL stream intermediate status updates (e.g., "Analyzing image...", "Identifying components...", "Generating diagnosis...") as chat messages.
2. WHILE the ActionAgent is performing inventory search or procurement, THE Chainlit_App SHALL stream progress updates indicating the current action (e.g., "Searching inventory...", "Generating purchase request...").
3. WHEN the GuidanceAgent generates a RepairGuide, THE Chainlit_App SHALL display each GuidanceStep sequentially as individual chat messages containing the step number, instruction text, safety checks, and expected outcome.

### Requirement 6: Voice Guidance Integration

**User Story:** As a Field_Technician, I want to use voice commands during the repair guidance phase, so that I can follow instructions hands-free.

#### Acceptance Criteria

1. WHEN the workflow enters the GUIDANCE phase, THE Chainlit_App SHALL activate an audio input widget that allows the Field_Technician to send voice commands.
2. WHEN the Field_Technician sends a voice command through the audio input, THE Chainlit_App SHALL forward the audio bytes to GuidanceAgent.process_voice_command and display the transcription and text response in the chat.
3. WHEN the GuidanceAgent returns a VoiceResponse with audio_response bytes, THE Chainlit_App SHALL play the audio response through the Chainlit audio output element.
4. IF the GuidanceAgent sets requires_human_escalation to true in the VoiceResponse, THEN THE Chainlit_App SHALL pause voice guidance and display an escalation prompt in the chat.

### Requirement 7: Session Persistence and Resumption

**User Story:** As a Field_Technician, I want to resume an interrupted workflow session, so that I do not lose progress if the connection drops.

#### Acceptance Criteria

1. WHEN a new chat session starts, THE Chainlit_App SHALL generate a unique session_id and associate the session with the OrchestrationLayer WorkflowState.
2. WHEN a Field_Technician reconnects to the Chainlit_App, THE Chainlit_App SHALL retrieve the existing WorkflowState using the session_id and display the current Workflow_Phase and any pending escalations.
3. IF a WorkflowState has unresolved escalations upon reconnection, THEN THE Chainlit_App SHALL re-display the escalation prompts to the Field_Technician.

### Requirement 8: Hackathon Demo Flow Support

**User Story:** As a hackathon presenter, I want a streamlined demo flow that showcases all AFE capabilities in sequence, so that judges can evaluate the full system in a limited time (~3 minutes for the demo video).

#### Acceptance Criteria

1. WHEN the Field_Technician sends a message containing "demo" as the first message, THE Chainlit_App SHALL initiate a guided demo flow that walks through all five Workflow_Phases with pre-configured sample data.
2. WHEN the demo flow is active, THE Chainlit_App SHALL display explanatory annotations before each phase describing the agent and Amazon Nova model being used (e.g., "🔍 DiagnosisAgent powered by Amazon Nova 2 Lite", "🛒 ActionAgent powered by Amazon Nova Act", "🎤 GuidanceAgent powered by Amazon Nova 2 Sonic").
3. WHEN the demo flow reaches the GUIDANCE phase, THE Chainlit_App SHALL present the repair steps with visual formatting including safety warnings highlighted in a distinct color or style.
4. THE demo flow SHALL complete within approximately 3 minutes to fit the hackathon demo video requirement.
5. WHEN the demo flow completes, THE Chainlit_App SHALL display a summary card showing all Amazon Nova models used (Nova 2 Lite, Nova Act, Nova 2 Sonic, Nova Multimodal Embeddings, Claude 3.5 Sonnet) and the hackathon categories covered (Agentic AI, Multimodal Understanding, Voice AI).

### Requirement 9: Dependency and Configuration

**User Story:** As a developer, I want Chainlit added as a project dependency with proper configuration, so that the UI can be started with a single command.

#### Acceptance Criteria

1. THE requirements.txt SHALL include the chainlit package dependency with a minimum version constraint.
2. THE Chainlit_App SHALL read configuration values (AWS region, model IDs, Weaviate endpoint) from environment variables or the existing .env file using python-dotenv.
3. WHEN the Chainlit_App is started using the `chainlit run chainlit_app.py` command, THE Chainlit_App SHALL launch and be accessible on the default Chainlit port.

### Requirement 10: Nova 2 Model Upgrade — DiagnosisAgent and CloudJudge

**User Story:** As a developer, I want the DiagnosisAgent and CloudJudge to use Amazon Nova 2 Lite instead of Nova Pro, so that the system leverages the latest Nova reasoning model with extended thinking for the hackathon.

#### Acceptance Criteria

1. THE config.py SHALL define the Nova 2 Lite model ID as `us.amazon.nova-2-lite-v1:0` and use it for the DiagnosisAgent and CloudJudge validation calls.
2. THE DiagnosisAgent._call_nova_pro method SHALL be updated to call Nova 2 Lite using the Bedrock Converse API (instead of invoke_model) to support the model's multimodal input format (text, image).
3. THE CloudJudge._call_nova method SHALL be updated to use the Nova 2 Lite model ID for safety, SOP, and quality validation prompts.
4. WHEN the DiagnosisAgent calls Nova 2 Lite, THE DiagnosisAgent SHALL pass image data using the Converse API image content block format with base64-encoded bytes.

### Requirement 11: Nova Multimodal Embeddings for RAG

**User Story:** As a developer, I want the RAG system to use Amazon Nova Multimodal Embeddings instead of Amazon Titan Embeddings and CLIP, so that text and image embeddings share a unified semantic space for better cross-modal retrieval.

#### Acceptance Criteria

1. THE config.py SHALL define the Nova Multimodal Embeddings model ID as `amazon.nova-2-multimodal-embeddings-v1:0`.
2. THE RAGSystem SHALL generate text embeddings by calling the Nova Multimodal Embeddings model via the Bedrock invoke_model API with taskType `SINGLE_EMBEDDING` and embeddingPurpose `GENERIC_INDEX`.
3. THE RAGSystem SHALL generate image embeddings by calling the Nova Multimodal Embeddings model with the image content encoded as base64 in the request body.
4. THE RAGSystem SHALL use a consistent embedding dimension (1024) for both text and image embeddings to enable cross-modal similarity search in Weaviate.
5. THE requirements.txt SHALL remove the sentence-transformers dependency since CLIP is no longer needed for image embeddings.

### Requirement 12: Nova 2 Sonic Voice AI Integration

**User Story:** As a developer, I want the GuidanceAgent to use Amazon Nova 2 Sonic's speech-to-speech capabilities for real-time conversational voice guidance, so that field technicians get a natural voice interaction experience.

#### Acceptance Criteria

1. THE GuidanceAgent SHALL use the Nova 2 Sonic model for both speech-to-text transcription and text-to-speech synthesis via the Bedrock API.
2. WHEN the GuidanceAgent processes a voice command, THE GuidanceAgent SHALL send audio bytes to Nova 2 Sonic and receive both a text transcription and an audio response.
3. THE GuidanceAgent SHALL support streaming audio responses from Nova 2 Sonic to enable real-time voice playback in the Chainlit_App.
4. THE GuidanceAgent._call_nova_sonic_text method SHALL continue to support text-only interactions as a fallback when audio input is not available.

### Requirement 13: Nova Act Mock Inventory Portal (Computer Use Demo)

**User Story:** As a hackathon presenter, I want the ActionAgent to navigate a mock Parts Inventory Portal web page using Nova Act's UI automation capabilities, so that judges can see the "Computer Use" feature driving a browser session in real time.

#### Acceptance Criteria

1. THE project SHALL include a `mock_portal/` directory containing a lightweight single-page HTML inventory portal (`index.html`) with a search input, results table, "Add to Cart" button, and "Submit Purchase Request" button, served by a simple Python HTTP server (`server.py`).
2. WHEN the PROCUREMENT phase begins, THE ActionAgent SHALL use Nova Act to open the mock portal URL, type the required part number into the search field, read the search results, click "Add to Cart", and click "Submit Purchase Request".
3. THE ActionAgent SHALL capture a screenshot at each browser interaction step and forward the screenshots to the Chainlit_App for inline display within the PROCUREMENT Step_Indicator.
4. IF the mock portal is unavailable, THEN THE ActionAgent SHALL fall back to the existing tool-calling procurement flow without browser automation.
5. WHEN the demo flow is active, THE Chainlit_App SHALL display an annotation before the PROCUREMENT phase explaining that Nova Act is automating a web UI workflow (e.g., "🤖 ActionAgent using Nova Act Computer Use to navigate the Parts Inventory Portal").
