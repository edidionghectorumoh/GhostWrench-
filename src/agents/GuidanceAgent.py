"""
GuidanceAgent: Voice-guided repair instructions using Amazon Nova Sonic.

This agent uses Nova Sonic for:
- Voice transcription and command processing
- Speech synthesis for repair instructions
- Step-by-step repair guidance
- Safety compliance validation
- Emergency protocol handling
"""

import json
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from config import bedrock_runtime, NOVA_2_SONIC_MODEL_ID
from src.models.agents import DiagnosisResult, RepairGuide, GuidanceStep
from src.models.domain import SiteContext
from src.judge.cloud_judge import CloudJudge

logger = logging.getLogger(__name__)


class GuidanceAgent:
    """
    Conversational guidance agent using Amazon Nova Sonic for voice interaction.
    
    Capabilities:
    - Generate repair guides tailored to technician skill level
    - Process voice commands (next, repeat, clarification, emergency)
    - Synthesize speech with urgency levels
    - Track repair session state
    - Validate safety compliance before each step
    - Handle emergency protocols
    """
    
    def __init__(self, cloud_judge: Optional[CloudJudge] = None):
        """Initialize the guidance agent with Nova 2 Sonic."""
        self.model_id = NOVA_2_SONIC_MODEL_ID
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.cloud_judge = cloud_judge
        
        # Session state tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def generate_repair_guide(
        self,
        diagnosis_result: DiagnosisResult,
        site_context: SiteContext,
        manual_sections: Optional[List[str]] = None
    ) -> RepairGuide:
        """
        Generate step-by-step repair guide tailored to technician skill level.
        
        Args:
            diagnosis_result: Diagnosis result with issue details
            site_context: Site context including technician skill level
            manual_sections: Optional relevant manual sections
            
        Returns:
            RepairGuide with sequenced steps
        """
        # Build prompt for repair guide generation
        prompt = self._build_repair_guide_prompt(
            diagnosis_result,
            site_context,
            manual_sections
        )
        
        # Call Nova Sonic for guide generation
        response = self._call_nova_sonic_text(prompt)
        
        # Parse response into structured repair guide
        guide = self._parse_repair_guide(response, diagnosis_result, site_context)
        
        return guide
    
    def _build_repair_guide_prompt(
        self,
        diagnosis_result: DiagnosisResult,
        site_context: SiteContext,
        manual_sections: Optional[List[str]]
    ) -> str:
        """Build prompt for repair guide generation."""
        skill_level_guidance = {
            "beginner": "Provide detailed step-by-step instructions with explanations. Include safety warnings and verification steps.",
            "intermediate": "Provide clear instructions with key safety points. Assume basic technical knowledge.",
            "advanced": "Provide concise instructions focusing on critical steps. Assume strong technical background.",
            "expert": "Provide high-level guidance with technical details. Assume expert-level knowledge."
        }
        
        parts_list = "\n".join([
            f"- {part.part_number}: {part.description} (Quantity: {part.quantity})"
            for part in diagnosis_result.required_parts
        ])
        
        tools_list = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in diagnosis_result.required_tools
        ]) if diagnosis_result.required_tools else "- Standard technician toolkit"
        
        safety_concerns = "\n".join([
            f"- {concern}"
            for concern in diagnosis_result.safety_concerns
        ]) if diagnosis_result.safety_concerns else "- Standard safety precautions"
        
        manual_context = ""
        if manual_sections:
            manual_context = "\n\n**Reference Manual Sections:**\n" + "\n".join([
                f"- {section}" for section in manual_sections
            ])
        
        prompt = f"""You are an expert field technician instructor. Generate a step-by-step repair guide for the following issue.

**Site Information:**
- Location: {site_context.location}
- Equipment Type: {site_context.equipment_type}
- Technician Skill Level: {site_context.skill_level}

**Issue Details:**
- Issue Type: {diagnosis_result.issue_type}
- Description: {diagnosis_result.description}
- Root Cause: {diagnosis_result.root_cause}
- Severity: {diagnosis_result.severity}

**Required Parts:**
{parts_list}

**Required Tools:**
{tools_list}

**Safety Concerns:**
{safety_concerns}

**Estimated Repair Time:** {diagnosis_result.estimated_repair_time_minutes} minutes
{manual_context}

**Instruction Style:** {skill_level_guidance.get(site_context.skill_level, skill_level_guidance['intermediate'])}

Generate a detailed repair guide with the following structure:
1. Pre-repair safety checks
2. Preparation steps (gather tools, parts, PPE)
3. Step-by-step repair procedure
4. Verification and testing steps
5. Post-repair documentation

For each step, include:
- Clear instruction
- Safety warnings (if applicable)
- Expected duration
- Verification method
- Troubleshooting tips

Format as JSON with this structure:
{{
  "steps": [
    {{
      "step_number": 1,
      "instruction": "...",
      "safety_warning": "...",
      "duration_minutes": 5,
      "verification": "...",
      "dependencies": []
    }}
  ]
}}
"""
        return prompt
    
    def _call_nova_sonic_text(self, prompt: str) -> str:
        """
        Call Nova Sonic for text generation.
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated text response
        """
        for attempt in range(self.max_retries):
            try:
                response = bedrock_runtime.converse(
                    modelId=self.model_id,
                    messages=[
                        {
                            "role": "user",
                            "content": [{"text": prompt}]
                        }
                    ],
                    inferenceConfig={
                        "maxTokens": 4096,
                        "temperature": 0.3
                    }
                )
                
                # Extract text from response
                output_message = response['output']['message']
                text_content = [
                    block['text'] for block in output_message['content']
                    if 'text' in block
                ]
                
                return " ".join(text_content)
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise Exception(f"Failed to call Nova Sonic after {self.max_retries} attempts: {e}")
    
    def _parse_repair_guide(
        self,
        response: str,
        diagnosis_result: DiagnosisResult,
        site_context: SiteContext
    ) -> RepairGuide:
        """Parse Nova Sonic response into RepairGuide."""
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
            else:
                # Fallback: create structured guide from text
                data = self._create_fallback_guide(response)
            
            # Convert to GuidanceStep objects
            steps = []
            for step_data in data.get('steps', []):
                steps.append(GuidanceStep(
                    step_number=step_data.get('step_number', len(steps) + 1),
                    instruction=step_data.get('instruction', ''),
                    safety_warning=step_data.get('safety_warning'),
                    duration_minutes=step_data.get('duration_minutes', 5),
                    verification=step_data.get('verification'),
                    dependencies=step_data.get('dependencies', []),
                    completed=False
                ))
            
            # Create RepairGuide
            return RepairGuide(
                guide_id=f"GUIDE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                diagnosis_result=diagnosis_result,
                steps=steps,
                estimated_total_time_minutes=sum(step.duration_minutes for step in steps),
                skill_level_required=site_context.skill_level,
                safety_requirements=diagnosis_result.safety_concerns or [],
                required_ppe=self._determine_ppe(diagnosis_result),
                emergency_contacts=[]
            )
            
        except Exception as e:
            # Fallback: create basic guide
            return self._create_basic_guide(diagnosis_result, site_context)
    
    def _create_fallback_guide(self, text: str) -> Dict[str, Any]:
        """Create fallback guide structure from unstructured text."""
        # Simple parsing: split by numbered steps
        lines = text.split('\n')
        steps = []
        current_step = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line starts with a number
            if line[0].isdigit() and '.' in line[:5]:
                if current_step:
                    steps.append(current_step)
                current_step = {
                    "step_number": len(steps) + 1,
                    "instruction": line,
                    "duration_minutes": 5
                }
            elif current_step and line:
                current_step["instruction"] += " " + line
        
        if current_step:
            steps.append(current_step)
        
        return {"steps": steps}
    
    def _create_basic_guide(
        self,
        diagnosis_result: DiagnosisResult,
        site_context: SiteContext
    ) -> RepairGuide:
        """Create basic repair guide as fallback."""
        steps = [
            GuidanceStep(
                step_number=1,
                instruction="Review safety requirements and gather required PPE",
                safety_warning="Ensure all safety equipment is available before proceeding",
                duration_minutes=5,
                verification="Confirm all PPE is present and in good condition",
                dependencies=[],
                completed=False
            ),
            GuidanceStep(
                step_number=2,
                instruction=f"Gather required parts: {', '.join([p.part_number for p in diagnosis_result.required_parts])}",
                duration_minutes=10,
                verification="Verify all parts are correct and undamaged",
                dependencies=[1],
                completed=False
            ),
            GuidanceStep(
                step_number=3,
                instruction=f"Follow standard procedure for {diagnosis_result.issue_type} repair",
                safety_warning="Follow all safety protocols for this equipment type",
                duration_minutes=diagnosis_result.estimated_repair_time_minutes - 20,
                verification="Test equipment functionality after repair",
                dependencies=[2],
                completed=False
            ),
            GuidanceStep(
                step_number=4,
                instruction="Verify repair completion and document work performed",
                duration_minutes=5,
                verification="Equipment operating normally, all tests passed",
                dependencies=[3],
                completed=False
            )
        ]
        
        return RepairGuide(
            guide_id=f"GUIDE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            diagnosis_result=diagnosis_result,
            steps=steps,
            estimated_total_time_minutes=diagnosis_result.estimated_repair_time_minutes,
            skill_level_required=site_context.skill_level,
            safety_requirements=diagnosis_result.safety_concerns or [],
            required_ppe=self._determine_ppe(diagnosis_result),
            emergency_contacts=[]
        )
    
    def _determine_ppe(self, diagnosis_result: DiagnosisResult) -> List[str]:
        """Determine required PPE based on diagnosis."""
        ppe = ["Safety glasses", "Work gloves"]
        
        if diagnosis_result.issue_type == "electrical_malfunction":
            ppe.extend(["Insulated gloves", "Electrical safety shoes"])
        
        if "high voltage" in " ".join(diagnosis_result.safety_concerns).lower():
            ppe.extend(["Arc flash suit", "Face shield"])
        
        if diagnosis_result.issue_type == "environmental":
            ppe.append("Respirator")
        
        return list(set(ppe))  # Remove duplicates
    
    def process_voice_command(
        self,
        audio_data: bytes,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Process voice command from technician using Nova 2 Sonic speech-to-speech.
        
        Sends audio to Nova 2 Sonic, receives transcription and audio response,
        then classifies intent and routes to the appropriate handler.
        
        Args:
            audio_data: Audio data bytes (PCM/WAV)
            session_id: Repair session ID
            
        Returns:
            VoiceResponse dict with transcription, audio_response,
            requires_human_escalation, intent, and timestamp
        """
        # Transcribe audio via Nova 2 Sonic
        transcription = self._transcribe_audio(audio_data)
        
        # Classify intent from transcription
        intent = self._classify_intent(transcription)
        
        # Generate text response based on intent
        response = self._handle_intent(intent, session_id, transcription)
        
        # Safety gate: run guidance text through CloudJudge before TTS
        response_text = response.get("text", "")
        if self.cloud_judge and response_text:
            try:
                from src.models.validation import AgentOutput
                safety_output = AgentOutput(
                    agent_type="guidance",
                    session_id=session_id,
                    output_data={"guidance_text": response_text},
                    confidence=0.9,
                )
                judgment = self.cloud_judge.validate_diagnosis_safety(
                    type("FakeDiag", (), {
                        "issue_id": session_id,
                        "issue_type": "guidance_response",
                        "severity": "medium",
                        "description": response_text,
                        "root_cause": "",
                        "affected_components": [],
                    })()
                )
                if not judgment.is_safe:
                    logger.warning(f"CloudJudge flagged guidance response as unsafe: {judgment.hazards_identified}")
                    response_text = (
                        "Safety review flagged this guidance. "
                        "Please consult your supervisor before proceeding."
                    )
                    response["text"] = response_text
                    response["safety_flagged"] = True
            except Exception as e:
                logger.warning(f"CloudJudge safety check failed, proceeding with original response: {e}")
        
        # Synthesize audio response via Nova 2 Sonic
        audio_response = self.synthesize_speech(
            response_text,
            urgency="critical" if intent == "emergency" else "normal"
        )
        
        # Determine if human escalation is needed
        requires_human_escalation = intent == "emergency" or response.get("action") == "error"
        
        return {
            "transcription": transcription,
            "audio_response": audio_response,
            "requires_human_escalation": requires_human_escalation,
            "intent": intent,
            "response": response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio using Nova 2 Sonic via Bedrock Converse API.
        
        Sends audio bytes as an audio content block and asks the model
        to transcribe. Falls back to a placeholder if the API call fails.
        
        Args:
            audio_data: Audio data bytes (PCM/WAV)
            
        Returns:
            Transcribed text
        """
        try:
            response = bedrock_runtime.converse(
                modelId=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "audio": {
                                    "format": "wav",
                                    "source": {"bytes": audio_data},
                                }
                            },
                            {"text": "Transcribe the audio command from the field technician."},
                        ],
                    }
                ],
                inferenceConfig={"maxTokens": 512, "temperature": 0.1},
            )
            
            output_message = response["output"]["message"]
            text_parts = [
                block["text"]
                for block in output_message["content"]
                if "text" in block
            ]
            return " ".join(text_parts).strip() or "[Transcribed voice command]"
            
        except Exception as e:
            logger.warning(f"Nova 2 Sonic transcription failed, using fallback: {e}")
            return "[Transcribed voice command]"
    
    def _classify_intent(self, transcription: str) -> str:
        """
        Classify intent from transcription.
        
        Args:
            transcription: Transcribed text
            
        Returns:
            Intent classification
        """
        text_lower = transcription.lower()
        
        if any(word in text_lower for word in ["next", "continue", "proceed"]):
            return "next_step"
        elif any(word in text_lower for word in ["repeat", "again", "say that"]):
            return "repeat"
        elif any(word in text_lower for word in ["help", "clarify", "explain", "what"]):
            return "clarification"
        elif any(word in text_lower for word in ["emergency", "stop", "danger", "unsafe"]):
            return "emergency"
        elif any(word in text_lower for word in ["done", "complete", "finished"]):
            return "completion"
        else:
            return "unknown"
    
    def _handle_intent(
        self,
        intent: str,
        session_id: str,
        transcription: str
    ) -> Dict[str, Any]:
        """Handle classified intent."""
        session = self.active_sessions.get(session_id)
        
        if not session:
            return {
                "text": "No active repair session found. Please start a new session.",
                "audio": None,
                "action": "error"
            }
        
        if intent == "next_step":
            return self._get_next_step(session_id)
        elif intent == "repeat":
            return self._repeat_current_step(session_id)
        elif intent == "clarification":
            return self._provide_clarification(session_id, transcription)
        elif intent == "emergency":
            return self._handle_emergency(session_id)
        elif intent == "completion":
            return self._handle_completion(session_id)
        else:
            return {
                "text": "I didn't understand that command. Please say 'next', 'repeat', 'help', or 'emergency'.",
                "audio": None,
                "action": "clarification_needed"
            }
    
    def synthesize_speech(
        self,
        text: str,
        urgency: str = "normal"
    ) -> bytes:
        """
        Synthesize speech from text using Nova 2 Sonic via Converse API.
        
        Args:
            text: Text to synthesize
            urgency: Urgency level (normal, warning, critical)
            
        Returns:
            Audio data bytes
        """
        # Adjust prompt based on urgency
        urgency_prefix = {
            "normal": "",
            "warning": "Speak clearly and firmly: ",
            "critical": "Speak urgently and loudly: ",
        }
        
        speech_text = urgency_prefix.get(urgency, "") + text
        
        try:
            response = bedrock_runtime.converse(
                modelId=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"text": f"Convert the following instruction to speech audio for a field technician: {speech_text}"}
                        ],
                    }
                ],
                inferenceConfig={"maxTokens": 512, "temperature": 0.3},
            )
            
            # Extract audio bytes from response if available
            output_message = response["output"]["message"]
            for block in output_message["content"]:
                if "audio" in block:
                    return block["audio"].get("source", {}).get("bytes", b"")
            
            # If no audio block, return placeholder (text-only response)
            return b"[Synthesized audio data]"
            
        except Exception as e:
            logger.warning(f"Nova 2 Sonic TTS failed, returning placeholder: {e}")
            return b"[Synthesized audio data]"
    
    def start_repair_session(
        self,
        session_id: str,
        repair_guide: RepairGuide,
        site_context: SiteContext
    ) -> Dict[str, Any]:
        """
        Start a new repair session.
        
        Args:
            session_id: Unique session ID
            repair_guide: Repair guide to follow
            site_context: Site context
            
        Returns:
            Session initialization details
        """
        self.active_sessions[session_id] = {
            "session_id": session_id,
            "repair_guide": repair_guide,
            "site_context": site_context,
            "current_step": 0,
            "completed_steps": [],
            "failed_steps": [],
            "started_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "paused": False
        }
        
        return {
            "session_id": session_id,
            "status": "started",
            "total_steps": len(repair_guide.steps),
            "estimated_time_minutes": repair_guide.estimated_total_time_minutes,
            "message": f"Repair session started. {len(repair_guide.steps)} steps to complete."
        }
    
    def _get_next_step(self, session_id: str) -> Dict[str, Any]:
        """Get next step in repair guide."""
        session = self.active_sessions[session_id]
        guide = session["repair_guide"]
        current_step_idx = session["current_step"]
        
        if current_step_idx >= len(guide.steps):
            return {
                "text": "All steps completed. Please confirm completion.",
                "audio": self.synthesize_speech("All steps completed. Please confirm completion.", "normal"),
                "action": "completion"
            }
        
        step = guide.steps[current_step_idx]
        
        # Check dependencies
        for dep in step.dependencies:
            if dep not in session["completed_steps"]:
                return {
                    "text": f"Cannot proceed. Step {dep} must be completed first.",
                    "audio": self.synthesize_speech(f"Cannot proceed. Step {dep} must be completed first.", "warning"),
                    "action": "dependency_not_met"
                }
        
        # Safety check
        safety_text = ""
        urgency = "normal"
        if step.safety_warning:
            safety_text = f" SAFETY WARNING: {step.safety_warning}."
            urgency = "warning"
        
        instruction_text = f"Step {step.step_number}: {step.instruction}.{safety_text}"
        
        # Update session
        session["current_step"] = current_step_idx + 1
        session["last_activity"] = datetime.now(timezone.utc)
        
        return {
            "text": instruction_text,
            "audio": self.synthesize_speech(instruction_text, urgency),
            "action": "next_step",
            "step": step
        }
    
    def _repeat_current_step(self, session_id: str) -> Dict[str, Any]:
        """Repeat current step."""
        session = self.active_sessions[session_id]
        guide = session["repair_guide"]
        current_step_idx = session["current_step"] - 1
        
        if current_step_idx < 0:
            return {
                "text": "No current step to repeat. Say 'next' to begin.",
                "audio": self.synthesize_speech("No current step to repeat. Say next to begin.", "normal"),
                "action": "no_step"
            }
        
        step = guide.steps[current_step_idx]
        instruction_text = f"Repeating step {step.step_number}: {step.instruction}."
        
        return {
            "text": instruction_text,
            "audio": self.synthesize_speech(instruction_text, "normal"),
            "action": "repeat",
            "step": step
        }
    
    def _provide_clarification(self, session_id: str, question: str) -> Dict[str, Any]:
        """Provide clarification on current step."""
        session = self.active_sessions[session_id]
        guide = session["repair_guide"]
        current_step_idx = session["current_step"] - 1
        
        if current_step_idx < 0:
            return {
                "text": "No current step. Say 'next' to begin.",
                "audio": self.synthesize_speech("No current step. Say next to begin.", "normal"),
                "action": "no_step"
            }
        
        step = guide.steps[current_step_idx]
        
        # Generate clarification (simplified)
        clarification = f"For step {step.step_number}: {step.instruction}. "
        if step.verification:
            clarification += f"Verify by: {step.verification}."
        
        return {
            "text": clarification,
            "audio": self.synthesize_speech(clarification, "normal"),
            "action": "clarification",
            "step": step
        }
    
    def _handle_emergency(self, session_id: str) -> Dict[str, Any]:
        """Handle emergency protocol."""
        session = self.active_sessions[session_id]
        session["paused"] = True
        
        emergency_text = "EMERGENCY PROTOCOL ACTIVATED. Stop all work immediately. Secure the area. Contact your supervisor."
        
        return {
            "text": emergency_text,
            "audio": self.synthesize_speech(emergency_text, "critical"),
            "action": "emergency",
            "session_paused": True
        }
    
    def _handle_completion(self, session_id: str) -> Dict[str, Any]:
        """Handle repair completion."""
        session = self.active_sessions[session_id]
        guide = session["repair_guide"]
        
        completion_text = f"Repair session completed. {len(guide.steps)} steps finished. Please document your work."
        
        # Mark session as completed
        session["completed_at"] = datetime.now(timezone.utc)
        
        return {
            "text": completion_text,
            "audio": self.synthesize_speech(completion_text, "normal"),
            "action": "completed",
            "session_completed": True
        }
    
    def handle_step_confirmation(
        self,
        session_id: str,
        step_number: int,
        success: bool,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle step completion confirmation.
        
        Args:
            session_id: Session ID
            step_number: Step number
            success: Whether step completed successfully
            notes: Optional notes
            
        Returns:
            Confirmation details
        """
        session = self.active_sessions.get(session_id)
        
        if not session:
            return {"error": "Session not found"}
        
        if success:
            session["completed_steps"].append(step_number)
            return {
                "status": "confirmed",
                "step_number": step_number,
                "message": f"Step {step_number} marked as completed."
            }
        else:
            session["failed_steps"].append(step_number)
            return {
                "status": "failed",
                "step_number": step_number,
                "message": f"Step {step_number} marked as failed. Troubleshooting may be required.",
                "notes": notes
            }
    
    def validate_safety_compliance(
        self,
        session_id: str,
        step_number: int
    ) -> Dict[str, Any]:
        """
        Validate safety compliance before step execution.
        
        Args:
            session_id: Session ID
            step_number: Step number to validate
            
        Returns:
            Safety validation result
        """
        session = self.active_sessions.get(session_id)
        
        if not session:
            return {"compliant": False, "reason": "Session not found"}
        
        guide = session["repair_guide"]
        
        if step_number < 1 or step_number > len(guide.steps):
            return {"compliant": False, "reason": "Invalid step number"}
        
        step = guide.steps[step_number - 1]
        
        # Check if step has safety warnings
        if step.safety_warning:
            return {
                "compliant": True,
                "requires_acknowledgment": True,
                "safety_warning": step.safety_warning,
                "message": "Safety warning present. Technician must acknowledge before proceeding."
            }
        
        return {
            "compliant": True,
            "requires_acknowledgment": False,
            "message": "No specific safety concerns for this step."
        }
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current session state."""
        session = self.active_sessions.get(session_id)
        
        if not session:
            return None
        
        guide = session["repair_guide"]
        
        return {
            "session_id": session_id,
            "current_step": session["current_step"],
            "total_steps": len(guide.steps),
            "completed_steps": session["completed_steps"],
            "failed_steps": session["failed_steps"],
            "started_at": session["started_at"].isoformat(),
            "last_activity": session["last_activity"].isoformat(),
            "paused": session["paused"],
            "progress_percentage": (len(session["completed_steps"]) / len(guide.steps)) * 100
        }
