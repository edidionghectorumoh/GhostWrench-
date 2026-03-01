"""
Multimodal Diagnosis Agent using Amazon Nova Pro.

This module implements the diagnosis agent that analyzes site photos and
telemetry data to identify hardware defects, installation errors, and
infrastructure issues by comparing against technical reference materials.
"""

import json
import logging
import base64
from typing import Optional, List, Dict, Any
from datetime import datetime

from config import bedrock_runtime, NOVA_PRO_MODEL_ID
from ..models.agents import (
    DiagnosisInput,
    DiagnosisResult,
    IssueType,
    Severity,
    Component,
    AnnotatedImage,
    Action,
    Urgency,
    ManualReference,
    ComparisonResult,
)
from ..models.domain import TelemetrySnapshot
from ..rag.RAGSystem import RAGSystem


logger = logging.getLogger(__name__)


class DiagnosisAgent:
    """
    Multimodal diagnosis agent using Amazon Nova Pro.
    
    Analyzes site photos and telemetry to identify infrastructure issues
    by comparing against technical manuals and reference materials.
    
    Confidence Threshold: 0.85
    - Below 0.85: Escalates to human expert review
    - Below 0.70: Requests additional photos
    """
    
    # Confidence thresholds
    CONFIDENCE_THRESHOLD_EXPERT_REVIEW = 0.85  # Escalate to human expert
    CONFIDENCE_THRESHOLD_ADDITIONAL_PHOTOS = 0.70  # Request more photos
    
    def __init__(
        self,
        rag_system: Optional[RAGSystem] = None,
    ):
        """
        Initialize Diagnosis Agent.
        
        Args:
            rag_system: Optional RAG system for technical manual retrieval
        """
        self.bedrock = bedrock_runtime
        self.model_id = NOVA_PRO_MODEL_ID
        self.rag_system = rag_system
        
        logger.info(
            f"Diagnosis Agent initialized with Nova Pro "
            f"(confidence threshold: {self.CONFIDENCE_THRESHOLD_EXPERT_REVIEW})"
        )
    
    def _call_nova_pro(
        self,
        prompt: str,
        image_data: Optional[bytes] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Call Amazon Nova Pro for multimodal analysis.
        
        Args:
            prompt: Text prompt for analysis
            image_data: Optional image binary data
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated analysis text
        """
        try:
            # Build content array
            content = []
            
            # Add image if provided
            if image_data:
                # Encode image to base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                content.append({
                    "image": {
                        "format": "jpeg",  # Assume JPEG, could detect format
                        "source": {
                            "bytes": image_base64
                        }
                    }
                })
            
            # Add text prompt
            content.append({
                "text": prompt
            })
            
            # Build request
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                "inferenceConfig": {
                    "temperature": temperature,
                    "max_new_tokens": max_tokens
                }
            }
            
            # Call Nova Pro
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['output']['message']['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Nova Pro API call failed: {e}")
            raise RuntimeError(f"Failed to call Nova Pro: {e}")
    
    def diagnose_issue(
        self,
        diagnosis_input: DiagnosisInput,
    ) -> DiagnosisResult:
        """
        Primary diagnosis method - analyzes image and context to identify issues.
        
        Args:
            diagnosis_input: Input containing image, context, and telemetry
            
        Returns:
            DiagnosisResult with identified issues and recommendations
        """
        logger.info("Starting diagnosis analysis")
        
        # Step 1: Identify equipment type from image
        equipment_type = diagnosis_input.equipment_type
        if not equipment_type:
            equipment_type = self._identify_equipment_type(
                diagnosis_input.image_data
            )
            logger.info(f"Identified equipment type: {equipment_type}")
        
        # Step 2: Retrieve reference materials from RAG
        manual_sections = []
        if self.rag_system:
            query = self._generate_rag_query(diagnosis_input, equipment_type)
            manual_sections = self.rag_system.retrieve_relevant_sections(
                query=query,
                equipment_type=equipment_type,
                top_k=5,
            )
            logger.info(f"Retrieved {len(manual_sections)} manual sections")
        
        # Step 3: Perform multimodal analysis with Nova Pro
        analysis_prompt = self._build_diagnosis_prompt(
            diagnosis_input,
            equipment_type,
            manual_sections,
        )
        
        raw_analysis = self._call_nova_pro(
            prompt=analysis_prompt,
            image_data=diagnosis_input.image_data.raw_image,
            temperature=0.7,
        )
        
        logger.info("Nova Pro analysis complete")
        
        # Step 4: Parse and structure diagnosis result
        diagnosis_result = self._parse_diagnosis_response(
            raw_analysis,
            diagnosis_input,
            equipment_type,
            manual_sections,
        )
        
        # Step 5: Enrich with telemetry if available
        if diagnosis_input.telemetry_data:
            diagnosis_result = self._enrich_with_telemetry(
                diagnosis_result,
                diagnosis_input.telemetry_data,
            )
        
        # Step 6: Check confidence threshold and escalate if needed
        diagnosis_result = self._check_confidence_and_escalate(diagnosis_result)
        
        logger.info(
            f"Diagnosis complete: {diagnosis_result.issue_type.value}, "
            f"severity={diagnosis_result.severity.value}, "
            f"confidence={diagnosis_result.confidence:.2f}, "
            f"escalation_required={getattr(diagnosis_result, 'escalation_required', False)}"
        )
        
        return diagnosis_result
    
    def _identify_equipment_type(self, image_data: Any) -> str:
        """
        Identify equipment type from image using Nova Pro.
        
        Args:
            image_data: Image data object
            
        Returns:
            Equipment type string
        """
        prompt = """Analyze this image and identify the type of equipment shown.

Possible equipment types:
- network_switch
- network_router
- server
- power_supply
- electrical_panel
- hvac_unit
- ups_system
- storage_array
- cable_infrastructure
- other

Respond with just the equipment type, nothing else."""
        
        equipment_type = self._call_nova_pro(
            prompt=prompt,
            image_data=image_data.raw_image,
            temperature=0.3,
        )
        
        return equipment_type.strip().lower().replace(" ", "_")
    
    def _generate_rag_query(
        self,
        diagnosis_input: DiagnosisInput,
        equipment_type: str,
    ) -> str:
        """Generate search query for RAG system."""
        query_parts = [equipment_type]
        
        if diagnosis_input.technician_notes:
            query_parts.append(diagnosis_input.technician_notes)
        
        if diagnosis_input.site_context:
            query_parts.append(f"site type: {diagnosis_input.site_context.site_type}")
        
        return " ".join(query_parts)
    
    def _build_diagnosis_prompt(
        self,
        diagnosis_input: DiagnosisInput,
        equipment_type: str,
        manual_sections: List[Dict[str, Any]],
    ) -> str:
        """Build comprehensive diagnosis prompt for Nova Pro."""
        
        # Build reference context from manual sections
        reference_context = ""
        if manual_sections:
            reference_context = "\n\nReference Materials:\n"
            for i, section in enumerate(manual_sections[:3], 1):
                reference_context += f"\n{i}. {section['title']}\n"
                reference_context += f"   {section['content'][:300]}...\n"
        
        # Build site context
        site_context = ""
        if diagnosis_input.site_context:
            site_context = f"""
Site Context:
- Site Type: {diagnosis_input.site_context.site_type}
- Criticality: {diagnosis_input.site_context.criticality_level}
"""
        
        # Build technician notes
        tech_notes = ""
        if diagnosis_input.technician_notes:
            tech_notes = f"\nTechnician Notes: {diagnosis_input.technician_notes}"
        
        prompt = f"""You are an expert field engineer analyzing infrastructure equipment for issues.

Equipment Type: {equipment_type}
{site_context}{tech_notes}{reference_context}

Analyze the provided image and identify any issues, defects, or anomalies. Consider:
1. Hardware defects (damage, wear, corrosion)
2. Installation errors (incorrect wiring, improper mounting, missing components)
3. Network failures (connectivity issues, port problems)
4. Electrical malfunctions (power issues, overheating, arcing)
5. Environmental issues (temperature, humidity, physical damage)

Provide your analysis in JSON format:
{{
  "issue_type": "hardware_defect|installation_error|network_failure|electrical_malfunction|environmental",
  "severity": "critical|high|medium|low",
  "confidence": 0.0-1.0,
  "description": "detailed description of the issue",
  "root_cause": "identified root cause",
  "affected_components": [
    {{
      "component_type": "type",
      "manufacturer": "manufacturer if visible",
      "model_number": "model if visible"
    }}
  ],
  "recommended_actions": [
    {{
      "action_type": "action type",
      "description": "what to do",
      "urgency": "emergency|urgent|normal|low",
      "requires_parts": true|false
    }}
  ]
}}"""
        
        return prompt
    
    def _parse_diagnosis_response(
        self,
        raw_analysis: str,
        diagnosis_input: DiagnosisInput,
        equipment_type: str,
        manual_sections: List[Dict[str, Any]],
    ) -> DiagnosisResult:
        """Parse Nova Pro response into structured DiagnosisResult."""
        
        try:
            # Extract JSON from response
            json_start = raw_analysis.find('{')
            json_end = raw_analysis.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = raw_analysis[json_start:json_end]
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
            
            # Parse issue type
            issue_type_str = data.get('issue_type', 'hardware_defect')
            issue_type = IssueType(issue_type_str)
            
            # Parse severity
            severity_str = data.get('severity', 'medium')
            severity = Severity(severity_str)
            
            # Parse confidence
            confidence = float(data.get('confidence', 0.7))
            
            # Parse affected components
            affected_components = []
            for comp_data in data.get('affected_components', []):
                component = Component(
                    component_id=f"comp_{len(affected_components)}",
                    component_type=comp_data.get('component_type', equipment_type),
                    manufacturer=comp_data.get('manufacturer', 'Unknown'),
                    model_number=comp_data.get('model_number', 'Unknown'),
                )
                affected_components.append(component)
            
            # If no components identified, create a default one
            if not affected_components:
                affected_components.append(Component(
                    component_id="comp_0",
                    component_type=equipment_type,
                    manufacturer="Unknown",
                    model_number="Unknown",
                ))
            
            # Parse recommended actions
            recommended_actions = []
            for action_data in data.get('recommended_actions', []):
                urgency_str = action_data.get('urgency', 'normal')
                urgency = Urgency(urgency_str)
                
                action = Action(
                    action_id=f"action_{len(recommended_actions)}",
                    action_type=action_data.get('action_type', 'inspect'),
                    description=action_data.get('description', ''),
                    urgency=urgency,
                    requires_parts=action_data.get('requires_parts', False),
                )
                recommended_actions.append(action)
            
            # Convert manual sections to ManualReference objects
            manual_references = [
                ManualReference(
                    manual_id=section.get('manual_id', 'unknown'),
                    section_id=section.get('section_id', 'unknown'),
                    title=section.get('title', ''),
                    relevance_score=section.get('relevance_score', 0.0),
                )
                for section in manual_sections
            ]
            
            # Create annotated image (simplified - would need actual annotation logic)
            visual_evidence = AnnotatedImage(
                image_id=diagnosis_input.image_data.image_id,
                original_image=diagnosis_input.image_data.raw_image,
                annotations=[],
            )
            
            # Create diagnosis result
            diagnosis_result = DiagnosisResult(
                issue_id=f"issue_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                issue_type=issue_type,
                severity=severity,
                confidence=confidence,
                description=data.get('description', ''),
                affected_components=affected_components,
                root_cause=data.get('root_cause', ''),
                visual_evidence=visual_evidence,
                reference_manual_sections=manual_references,
                recommended_actions=recommended_actions,
            )
            
            return diagnosis_result
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse diagnosis response: {e}")
            logger.debug(f"Raw response: {raw_analysis[:500]}")
            
            # Return a conservative fallback diagnosis
            return self._create_fallback_diagnosis(
                diagnosis_input,
                equipment_type,
                manual_sections,
            )
    
    def _create_fallback_diagnosis(
        self,
        diagnosis_input: DiagnosisInput,
        equipment_type: str,
        manual_sections: List[Dict[str, Any]],
    ) -> DiagnosisResult:
        """Create a conservative fallback diagnosis when parsing fails."""
        
        manual_references = [
            ManualReference(
                manual_id=section.get('manual_id', 'unknown'),
                section_id=section.get('section_id', 'unknown'),
                title=section.get('title', ''),
                relevance_score=section.get('relevance_score', 0.0),
            )
            for section in manual_sections
        ]
        
        visual_evidence = AnnotatedImage(
            image_id=diagnosis_input.image_data.image_id,
            original_image=diagnosis_input.image_data.raw_image,
            annotations=[],
        )
        
        return DiagnosisResult(
            issue_id=f"issue_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            issue_type=IssueType.HARDWARE_DEFECT,
            severity=Severity.MEDIUM,
            confidence=0.5,
            description="Unable to complete automated diagnosis. Manual inspection recommended.",
            affected_components=[
                Component(
                    component_id="comp_0",
                    component_type=equipment_type,
                    manufacturer="Unknown",
                    model_number="Unknown",
                )
            ],
            root_cause="Automated analysis inconclusive",
            visual_evidence=visual_evidence,
            reference_manual_sections=manual_references,
            recommended_actions=[
                Action(
                    action_id="action_0",
                    action_type="manual_inspection",
                    description="Perform manual inspection by qualified technician",
                    urgency=Urgency.NORMAL,
                    requires_parts=False,
                )
            ],
        )
    
    def _enrich_with_telemetry(
        self,
        diagnosis: DiagnosisResult,
        telemetry: TelemetrySnapshot,
    ) -> DiagnosisResult:
        """
        Enrich diagnosis with telemetry data correlation.
        
        Args:
            diagnosis: Initial diagnosis result
            telemetry: Telemetry data snapshot
            
        Returns:
            Enhanced diagnosis result
        """
        logger.info("Enriching diagnosis with telemetry data")
        
        # Check if telemetry is stale
        if telemetry.is_stale(max_age_seconds=600):
            logger.warning("Telemetry data is stale, reducing confidence")
            diagnosis.confidence = max(0.0, diagnosis.confidence - 0.15)
            return diagnosis
        
        # Analyze telemetry for anomalies
        anomalies_found = False
        telemetry_notes = []
        
        for metric_name, metric_value in telemetry.metrics.items():
            # Check for critical metrics
            if "temperature" in metric_name.lower():
                if hasattr(metric_value, 'value') and float(metric_value.value) > 80:
                    anomalies_found = True
                    telemetry_notes.append(f"High temperature detected: {metric_value.value}°C")
            
            elif "power" in metric_name.lower():
                if hasattr(metric_value, 'value') and metric_value.value == 0:
                    anomalies_found = True
                    telemetry_notes.append("Power loss detected")
            
            elif "status" in metric_name.lower():
                if hasattr(metric_value, 'value') and str(metric_value.value).lower() in ['down', 'failed', 'error']:
                    anomalies_found = True
                    telemetry_notes.append(f"Status issue: {metric_value.value}")
        
        # Check alerts
        if telemetry.alerts:
            anomalies_found = True
            critical_alerts = [a for a in telemetry.alerts if a.severity == "critical"]
            if critical_alerts:
                telemetry_notes.append(f"{len(critical_alerts)} critical alerts active")
        
        # Update diagnosis if telemetry correlates
        if anomalies_found:
            # Increase confidence if telemetry supports visual diagnosis
            diagnosis.confidence = min(1.0, diagnosis.confidence + 0.10)
            
            # Append telemetry notes to description
            if telemetry_notes:
                diagnosis.description += "\n\nTelemetry Correlation:\n- " + "\n- ".join(telemetry_notes)
            
            logger.info(f"Telemetry correlation increased confidence to {diagnosis.confidence:.2f}")
        
        return diagnosis
    
    def compare_with_reference_materials(
        self,
        image_data: Any,
        equipment_type: str,
    ) -> ComparisonResult:
        """
        Compare site image with reference materials from RAG.
        
        Args:
            image_data: Site image data
            equipment_type: Type of equipment
            
        Returns:
            ComparisonResult with deviations and compliance status
        """
        logger.info(f"Comparing image with reference materials for {equipment_type}")
        
        if not self.rag_system:
            logger.warning("RAG system not available for comparison")
            return ComparisonResult(
                deviations_found=[],
                compliance_status="partial",
                reference_images=[],
                annotated_differences=AnnotatedImage(
                    image_id=image_data.image_id,
                    original_image=image_data.raw_image,
                    annotations=[],
                ),
            )
        
        # Retrieve similar reference images
        similar_images = self.rag_system.retrieve_similar_images(
            query_image=image_data.raw_image,
            equipment_type=equipment_type,
            top_k=3,
        )
        
        # Use Nova Pro to compare
        prompt = f"""Compare this site image with the reference images for {equipment_type}.

Identify any deviations from standard installation or configuration:
1. Missing components
2. Incorrect wiring or connections
3. Improper mounting or positioning
4. Physical damage or wear
5. Non-standard configurations

Provide comparison in JSON format:
{{
  "compliance_status": "compliant|non_compliant|partial",
  "deviations": [
    {{
      "type": "deviation type",
      "description": "what is different",
      "severity": "critical|high|medium|low"
    }}
  ]
}}"""
        
        comparison_response = self._call_nova_pro(
            prompt=prompt,
            image_data=image_data.raw_image,
            temperature=0.5,
        )
        
        # Parse comparison result
        try:
            json_start = comparison_response.find('{')
            json_end = comparison_response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(comparison_response[json_start:json_end])
                
                return ComparisonResult(
                    deviations_found=data.get('deviations', []),
                    compliance_status=data.get('compliance_status', 'partial'),
                    reference_images=similar_images,
                    annotated_differences=AnnotatedImage(
                        image_id=image_data.image_id,
                        original_image=image_data.raw_image,
                        annotations=[],
                    ),
                )
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse comparison response: {e}")
        
        # Fallback
        return ComparisonResult(
            deviations_found=[],
            compliance_status="partial",
            reference_images=similar_images,
            annotated_differences=AnnotatedImage(
                image_id=image_data.image_id,
                original_image=image_data.raw_image,
                annotations=[],
            ),
        )
    
    def analyze_telemetry(
        self,
        telemetry: TelemetrySnapshot,
    ) -> Dict[str, Any]:
        """
        Analyze telemetry patterns for anomalies.
        
        Args:
            telemetry: Telemetry snapshot
            
        Returns:
            Analysis results dictionary
        """
        logger.info("Analyzing telemetry patterns")
        
        anomalies = []
        
        # Check each metric
        for metric_name, metric_value in telemetry.metrics.items():
            if hasattr(metric_value, 'value'):
                value = metric_value.value
                
                # Temperature checks
                if "temperature" in metric_name.lower():
                    if float(value) > 85:
                        anomalies.append({
                            "metric": metric_name,
                            "value": value,
                            "issue": "Critical temperature",
                            "severity": "critical",
                        })
                    elif float(value) > 75:
                        anomalies.append({
                            "metric": metric_name,
                            "value": value,
                            "issue": "High temperature",
                            "severity": "high",
                        })
                
                # Power checks
                elif "power" in metric_name.lower():
                    if value == 0 or value == "0":
                        anomalies.append({
                            "metric": metric_name,
                            "value": value,
                            "issue": "Power loss",
                            "severity": "critical",
                        })
        
        return {
            "anomalies_detected": len(anomalies) > 0,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "system_status": telemetry.system_status.value,
            "alert_count": len(telemetry.alerts),
        }
    
    def detect_multiple_issues(
        self,
        image_data: Any,
    ) -> List[DiagnosisResult]:
        """
        Detect multiple issues in a single image.
        
        Args:
            image_data: Image data object
            
        Returns:
            List of diagnosis results for each detected issue
        """
        logger.info("Detecting multiple issues in image")
        
        prompt = """Analyze this image for ALL visible issues, defects, or anomalies.

List every issue you can identify, even minor ones. For each issue, provide:
1. Type of issue
2. Severity
3. Location in image
4. Description

Respond in JSON format with an array of issues."""
        
        response = self._call_nova_pro(
            prompt=prompt,
            image_data=image_data.raw_image,
            temperature=0.7,
        )
        
        # For now, return single diagnosis
        # Full implementation would parse multiple issues
        diagnosis_input = DiagnosisInput(
            image_data=image_data,
            equipment_type=None,
            site_context=None,
        )
        
        return [self.diagnose_issue(diagnosis_input)]
    
    def _check_confidence_and_escalate(
        self,
        diagnosis: DiagnosisResult,
    ) -> DiagnosisResult:
        """
        Check confidence threshold and add escalation flags if needed.
        
        Thresholds:
        - < 0.70: Request additional photos
        - < 0.85: Escalate to human expert review
        
        Args:
            diagnosis: Diagnosis result to check
            
        Returns:
            Diagnosis with escalation flags added
        """
        # Add escalation attributes (these will be added to the dict representation)
        escalation_required = False
        escalation_reason = None
        requires_additional_photos = False
        
        if diagnosis.confidence < self.CONFIDENCE_THRESHOLD_ADDITIONAL_PHOTOS:
            requires_additional_photos = True
            escalation_required = True
            escalation_reason = (
                f"Low confidence ({diagnosis.confidence:.2f} < {self.CONFIDENCE_THRESHOLD_ADDITIONAL_PHOTOS}). "
                "Additional photos from multiple angles recommended for accurate diagnosis."
            )
            logger.warning(
                f"Confidence {diagnosis.confidence:.2f} below threshold "
                f"{self.CONFIDENCE_THRESHOLD_ADDITIONAL_PHOTOS}. Requesting additional photos."
            )
        
        elif diagnosis.confidence < self.CONFIDENCE_THRESHOLD_EXPERT_REVIEW:
            escalation_required = True
            escalation_reason = (
                f"Confidence ({diagnosis.confidence:.2f}) below expert review threshold "
                f"({self.CONFIDENCE_THRESHOLD_EXPERT_REVIEW}). Human expert review required."
            )
            logger.warning(
                f"Confidence {diagnosis.confidence:.2f} below threshold "
                f"{self.CONFIDENCE_THRESHOLD_EXPERT_REVIEW}. Escalating to human expert."
            )
        
        # Store escalation info as attributes (will be included in dict conversion)
        diagnosis.escalation_required = escalation_required
        diagnosis.escalation_reason = escalation_reason
        diagnosis.requires_additional_photos = requires_additional_photos
        
        return diagnosis
