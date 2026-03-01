# Implementation Plan: Autonomous Site & Infrastructure Engineer

## Overview

This implementation plan breaks down the Autonomous Field Engineer system into discrete coding tasks. The system uses a multi-agent orchestration pattern with Amazon Nova models (Pro for diagnosis, Act for actions, Sonic for voice guidance) and a local LLM judge for validation. Implementation follows a bottom-up approach: core data models → individual agents → orchestration layer → integration → testing.

## Tasks

- [x] 1. Set up project structure and core data models
  - Create TypeScript project with Node.js runtime
  - Set up directory structure: `/src/models`, `/src/agents`, `/src/orchestration`, `/src/external`, `/src/judge`, `/src/rag`, `/tests`
  - Install dependencies: AWS SDK for Bedrock, TypeScript, fast-check (property testing), SQLite3
  - Define core data models in `/src/models/domain.ts`: `SiteContext`, `Component`, `ImageData`, `TelemetrySnapshot`, `Part`, `Tool`, `SkillLevel`
  - Define workflow models in `/src/models/workflow.ts`: `WorkflowState`, `DiagnosisState`, `ProcurementState`, `GuidanceState`, `Escalation`
  - Define agent interface models in `/src/models/agents.ts`: `FieldRequest`, `FieldResponse`, `DiagnosisInput`, `DiagnosisResult`, `ActionResult`, `GuidanceStep`, `RepairGuide`
  - Define validation models in `/src/models/validation.ts`: `AgentOutput`, `ValidationCriteria`, `JudgmentResult`, `SafetyJudgment`, `ComplianceJudgment`, `BudgetJudgment`
  - _Requirements: 1.1, 1.3, 2.1, 6.2, 7.2, 11.2_

- [ ]* 1.1 Write property tests for data model validation
  - **Property 1: Safety Validation Gate** - All field-executed actions must have approved safety validation
  - **Validates: Requirements 2.1, 2.2**

- [x] 2. Implement Cloud-Based Judge validation layer
  - [x] 2.1 Create Cloud Judge interface and core validation logic
    - Implement `/src/judge/cloud_judge.py` with interface methods: `validate_agent_output()`, `validate_diagnosis_safety()`, `validate_sop_compliance()`, `validate_budget_constraints()`
    - Integrate Amazon Nova Pro via AWS Bedrock for multimodal analysis
    - Integrate Claude 3.5 Sonnet via AWS Bedrock for complex reasoning and validation logic
    - Use Bedrock Runtime client from config.py
    - Implement prompt templates for safety, SOP, budget, and quality validations
    - Implement judgment result parsing and structuring
    - _Requirements: 2.1, 2.2, 2.3, 6.1, 6.2, 6.3_
  
  - [x] 2.2 Implement cloud audit logging
    - Create SQLite database schema for audit logs: `judgments` table with fields (judgmentId, timestamp, agentType, outputData, validationCriteria, approved, violations, reasoning, escalationLevel)
    - Implement `logJudgment()` method to persist all validations
    - Implement audit log synchronization for central system integration
    - _Requirements: 6.3, 6.5, 11.1, 11.4_
  
  - [ ]* 2.3 Write property tests for judge validation
    - **Property 2: Budget Compliance** - All approved purchase requests stay within budget or are escalated
    - **Validates: Requirements 5.1, 5.2, 5.3**
  
  - [ ]* 2.4 Write unit tests for judge validation logic
    - Test safety rule validation with compliant and non-compliant outputs
    - Test SOP compliance checking with various repair procedures
    - Test budget validation with different cost scenarios
    - Test escalation level determination based on violation types
    - _Requirements: 2.1, 2.2, 5.1, 10.1, 10.2_

- [ ] 3. Implement RAG system for technical manuals
  - [ ] 3.1 Create vector database and embedding pipeline
    - Implement `/src/rag/RAGSystem.ts` with interface methods: `ingestManual()`, `ingestReferenceImages()`, `retrieveRelevantSections()`, `retrieveSimilarImages()`, `hybridSearch()`
    - Set up vector database using Pinecone or Weaviate for embeddings storage
    - Implement text embedding generation using Amazon Titan Embeddings
    - Implement image embedding generation using CLIP model
    - Create manual ingestion pipeline to process PDF technical manuals
    - _Requirements: 8.1, 8.2, 8.6, 12.6_
  
  - [ ] 3.2 Implement semantic search and retrieval
    - Implement HNSW approximate nearest neighbor search for fast retrieval
    - Implement hybrid search combining text and image similarity
    - Implement query result caching with 1-hour TTL for performance
    - Implement fallback logic when no relevant manuals found
    - _Requirements: 8.1, 8.2, 8.3, 8.5, 12.6_
  
  - [ ]* 3.3 Write unit tests for RAG retrieval
    - Test manual section retrieval with various equipment types
    - Test image similarity search with reference images
    - Test hybrid search combining text and image queries
    - Test fallback behavior when no documentation available
    - _Requirements: 8.1, 8.2, 8.5_

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement Multimodal Diagnosis Agent (Amazon Nova Pro)
  - [ ] 5.1 Create Diagnosis Agent core logic
    - Implement `/src/agents/DiagnosisAgent.ts` with interface methods: `diagnoseIssue()`, `compareWithReferenceMaterials()`, `analyzeTelemetry()`, `detectMultipleIssues()`
    - Integrate Amazon Nova Pro via AWS Bedrock API for multimodal image analysis
    - Implement equipment type identification from images
    - Implement issue detection and classification (hardware_defect, installation_error, network_failure, electrical_malfunction, environmental)
    - Implement confidence scoring algorithm
    - Implement image annotation for visual evidence
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6_
  
  - [ ] 5.2 Integrate RAG system for reference comparison
    - Implement RAG query generation from diagnosis context
    - Implement reference material retrieval and comparison logic
    - Implement deviation detection between site photo and reference images
    - Implement manual section linking in diagnosis results
    - _Requirements: 1.2, 8.1, 8.2, 8.3, 8.4_
  
  - [ ] 5.3 Implement telemetry correlation
    - Implement telemetry data analysis for anomaly detection
    - Implement correlation logic between visual evidence and telemetry patterns
    - Implement confidence adjustment based on telemetry availability and staleness
    - Implement baseline deviation detection
    - _Requirements: 1.4, 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [ ]* 5.4 Write property tests for diagnosis agent
    - **Property 4: Diagnosis Confidence Threshold** - Critical diagnoses with confidence < 0.80 must be escalated
    - **Validates: Requirements 1.6, 10.2**
  
  - [ ]* 5.5 Write unit tests for diagnosis agent
    - Test image analysis with various equipment types
    - Test multi-issue detection with complex scenarios
    - Test confidence scoring accuracy
    - Test telemetry correlation logic
    - _Requirements: 1.1, 1.3, 1.4, 1.5_

- [ ] 6. Implement Agentic Action Agent (Amazon Nova Act)
  - [ ] 6.1 Create Action Agent core logic
    - Implement `/src/agents/ActionAgent.ts` with interface methods: `executeToolChain()`, `searchInventory()`, `checkPartAvailability()`, `generateCostEstimate()`, `createPurchaseRequest()`, `submitToApprovalWorkflow()`, `queryTelemetryDatabase()`
    - Integrate Amazon Nova Act via AWS Bedrock API for agentic tool-calling
    - Implement tool chain execution with dependency management
    - Implement retry logic with exponential backoff for external API calls
    - _Requirements: 3.1, 3.2, 3.4, 3.5, 3.6, 13.6_
  
  - [ ] 6.2 Implement inventory search and parts procurement
    - Implement inventory database search with exact and fuzzy matching
    - Implement alternative parts search for compatibility
    - Implement lead time estimation and supplier identification
    - Implement cost calculation including parts, shipping, and labor
    - Implement purchase request generation with justification and urgency
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [ ] 6.3 Implement approval workflow integration
    - Implement approval authority level determination based on cost
    - Implement purchase request submission to procurement system
    - Implement approval status tracking
    - Implement estimated delivery date calculation
    - _Requirements: 3.7, 3.8, 5.3, 5.4, 5.7_
  
  - [ ]* 6.4 Write property tests for action agent
    - **Property 3: Cost Calculation Accuracy** - Total cost equals sum of part costs plus labor
    - **Validates: Requirements 3.4, 5.6**
  
  - [ ]* 6.5 Write unit tests for action agent
    - Test tool chain execution with dependencies
    - Test inventory search with exact and fuzzy matches
    - Test cost calculation accuracy
    - Test purchase request generation
    - Test retry logic for API failures
    - _Requirements: 3.1, 3.2, 3.4, 13.6_

- [ ] 7. Implement Conversational Guidance Agent (Amazon Nova 2 Sonic)
  - [ ] 7.1 Create Guidance Agent core logic
    - Implement `/src/agents/GuidanceAgent.ts` with interface methods: `generateRepairGuide()`, `processVoiceCommand()`, `synthesizeSpeech()`, `getNextStep()`, `handleStepConfirmation()`, `validateSafetyCompliance()`
    - Integrate Amazon Nova 2 Sonic via AWS Bedrock API for voice interaction
    - Implement repair guide generation tailored to technician skill level
    - Implement step sequencing and dependency logic
    - Implement safety check integration before each step
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 15.1, 15.2, 15.3_
  
  - [ ] 7.2 Implement voice command processing
    - Implement voice transcription using Nova Sonic
    - Implement intent classification (next_step, repeat, clarification, emergency, completion)
    - Implement speech synthesis with urgency levels (normal, warning, critical)
    - Implement fallback to text input when voice recognition fails
    - _Requirements: 4.3, 4.4, 4.6, 4.10, 13.4_
  
  - [ ] 7.3 Implement repair session management
    - Implement guidance session state tracking (current step, completed steps, failed steps)
    - Implement step completion confirmation handling
    - Implement troubleshooting tips and clarification responses
    - Implement emergency protocol activation
    - Implement maintenance record creation on completion
    - _Requirements: 4.7, 4.8, 4.9, 7.7, 11.2_
  
  - [ ]* 7.4 Write property tests for guidance agent
    - **Property 10: Voice Interaction Timeout** - Commands timing out after 5 minutes must pause session
    - **Validates: Requirements 4.4, 13.4**
  
  - [ ]* 7.5 Write unit tests for guidance agent
    - Test repair guide generation for different skill levels
    - Test voice command parsing with various intents
    - Test speech synthesis with different urgency levels
    - Test step sequencing logic
    - Test emergency handling
    - _Requirements: 4.1, 4.3, 4.4, 4.8, 15.1, 15.2_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement external system integrations
  - [x] 9.1 Create external system adapter interfaces
    - Implement `/src/external/ExternalSystemsAdapter.ts` with client interfaces: `InventorySystemClient`, `ProcurementSystemClient`, `TelemetrySystemClient`, `MaintenanceLogClient`
    - Implement authentication and authorization handling for each system
    - Implement circuit breaker pattern for resilience
    - Implement data transformation between system-specific and agent formats
    - _Requirements: 3.1, 9.1, 11.2, 13.1, 13.6_
  
  - [x] 9.2 Implement inventory system client
    - Implement REST API client for inventory database
    - Implement part search, details retrieval, stock checking, and reservation
    - Implement response caching to reduce API calls
    - Implement offline fallback with cached data (24-hour window)
    - _Requirements: 3.1, 3.2, 13.1_
  
  - [x] 9.3 Implement procurement system client
    - Implement REST API client for procurement system
    - Implement purchase order creation, approval submission, status tracking, and shipment tracking
    - Implement approval workflow integration
    - _Requirements: 3.5, 3.8, 5.4_
  
  - [x] 9.4 Implement telemetry system client
    - Implement time-series database client for site telemetry
    - Implement metric queries, alert retrieval, and historical baseline queries
    - Implement staleness detection for telemetry data
    - _Requirements: 9.1, 9.2, 9.5, 9.6_
  
  - [x] 9.5 Implement maintenance log client
    - Implement REST API client for maintenance records
    - Implement record creation, updates, and history retrieval
    - Implement audit trail integration
    - _Requirements: 4.9, 11.2, 11.3_
  
  - [ ]* 9.6 Write unit tests for external system clients
    - Test API authentication and authorization
    - Test circuit breaker behavior on failures
    - Test data transformation accuracy
    - Test caching and offline fallback
    - Test retry logic with exponential backoff
    - _Requirements: 13.1, 13.6, 13.7_

- [x] 10. Implement Orchestration Layer
  - [x] 10.1 Create orchestration core logic
    - Implement `/src/orchestration/OrchestrationLayer.ts` with interface methods: `processFieldRequest()`, `routeToDiagnosisAgent()`, `routeToActionAgent()`, `routeToGuidanceAgent()`, `validateWithJudge()`, `getWorkflowState()`, `updateWorkflowState()`
    - Implement session management with unique session IDs
    - Implement workflow state initialization and persistence
    - Implement agent routing logic based on request type
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 14.1, 14.6_
  
  - [x] 10.2 Implement workflow phase management
    - Implement phase transition logic (intake → diagnosis → procurement → guidance → completion)
    - Implement validation gate enforcement at each phase transition
    - Implement checkpoint persistence for crash recovery
    - Implement workflow resumption from saved state
    - _Requirements: 7.3, 7.4, 7.6, 13.2, 13.3_
  
  - [x] 10.3 Implement multi-agent coordination
    - Implement parallel agent execution where possible (diagnosis + telemetry query)
    - Implement agent output aggregation and context sharing
    - Implement fallback strategies when agent operations fail
    - Implement dependency management between agent operations
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_
  
  - [x] 10.4 Implement escalation handling
    - Implement escalation creation and tracking
    - Implement notification system for escalation recipients (email, SMS)
    - Implement workflow pause on escalation
    - Implement escalation resolution handling
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8_
  
  - [ ]* 10.5 Write property tests for orchestration layer
    - **Property 5: Workflow Phase Ordering** - Guidance phase requires confirmed diagnosis
    - **Property 6: Judge Validation Completeness** - Completed workflows have approved validations for all phases
    - **Validates: Requirements 7.3, 7.4, 7.9**
  
  - [ ]* 10.6 Write unit tests for orchestration layer
    - Test workflow state transitions
    - Test session management
    - Test agent routing logic
    - Test validation gate enforcement
    - Test escalation handling
    - Test crash recovery and resumption
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.6, 10.1, 10.5_

- [ ] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implement error handling and resilience
  - [x] 12.1 Implement error recovery for low confidence diagnosis
    - Implement additional photo request logic when confidence < 0.70
    - Implement multi-angle photo aggregation for improved confidence
    - Implement human expert escalation for persistent low confidence
    - _Requirements: 1.6, 10.2_
  
  - [x] 12.2 Implement error recovery for inventory system unavailability
    - Implement cached inventory data fallback (24-hour window)
    - Implement "pending verification" marking for cached results
    - Implement background retry job for inventory search
    - Implement cache validation when connectivity restored
    - _Requirements: 13.1, 13.7_
  
  - [x] 12.3 Implement error recovery for local judge offline
    - Implement judge availability detection (5-second timeout)
    - Implement workflow pause and state persistence on judge failure
    - Implement automatic workflow resumption on judge restart
    - Implement last output re-validation after recovery
    - _Requirements: 6.6, 6.7, 13.2, 13.3_
  
  - [x] 12.4 Implement error recovery for safety violations
    - Implement immediate workflow halt on safety violation detection
    - Implement critical alert notifications to safety officer and supervisor
    - Implement safety clearance requirement before continuation
    - Implement alternative procedure generation with stricter safety constraints
    - _Requirements: 2.2, 2.3, 10.1_
  
  - [x] 12.5 Implement error recovery for budget exceeded scenarios
    - Implement approval workflow queueing for over-budget requests
    - Implement temporary workaround option identification
    - Implement approval timeline estimation
    - Implement notification on approval granted
    - _Requirements: 5.3, 5.4, 5.5, 5.7_
  
  - [x] 12.6 Implement error recovery for voice recognition failures
    - Implement clarification request on parse failure
    - Implement text input fallback option
    - Implement recognition failure logging for model improvement
    - _Requirements: 4.10, 13.4_
  
  - [x] 12.7 Implement error recovery for missing technical manuals
    - Implement fuzzy equipment type matching for similar equipment
    - Implement generic repair procedure fallback
    - Implement "low reference coverage" flagging
    - Implement missing manual notification to documentation team
    - _Requirements: 8.5, 8.6_
  
  - [x] 12.8 Implement error recovery for delayed part delivery
    - Implement expedited shipping search
    - Implement alternative parts with faster availability search
    - Implement cost-benefit analysis for expedited vs standard shipping
    - Implement temporary workaround procedure recommendation
    - Implement management escalation for SLA violations
    - _Requirements: 3.9, 13.8_
  
  - [ ]* 12.9 Write unit tests for error recovery scenarios
    - Test low confidence diagnosis recovery
    - Test inventory system unavailability recovery
    - Test judge offline recovery
    - Test safety violation handling
    - Test budget exceeded handling
    - Test voice recognition failure recovery
    - Test missing manual fallback
    - Test delayed delivery handling
    - _Requirements: 1.6, 2.2, 3.9, 4.10, 6.6, 8.5, 13.1, 13.2, 13.4, 13.8_

- [ ] 13. Implement performance optimizations
  - [ ] 13.1 Implement image processing optimizations
    - Implement image compression to 2048x1536 before upload
    - Implement progressive JPEG encoding for faster initial analysis
    - Implement equipment type detection result caching
    - Target: < 10 seconds for diagnosis at p95
    - _Requirements: 12.1, 12.5_
  
  - [ ] 13.2 Implement RAG system optimizations
    - Implement query result caching with 1-hour TTL
    - Implement common equipment type result pre-caching
    - Verify HNSW index performance for < 500ms retrieval
    - _Requirements: 12.6_
  
  - [ ] 13.3 Implement local judge optimizations
    - Configure quantized Llama 3.1 8B model (Q4_K_M) for faster inference
    - Implement prompt caching for repeated validation patterns
    - Implement batch validation when possible
    - Target: < 2 seconds per validation at p95
    - _Requirements: 12.3_
  
  - [ ] 13.4 Implement voice processing optimizations
    - Implement streaming audio for real-time transcription
    - Implement voice activity detection to reduce processing overhead
    - Implement common repair phrase caching
    - Target: < 1 second for voice response at p95
    - _Requirements: 12.4_
  
  - [ ]* 13.5 Write performance benchmark tests
    - Test diagnosis latency (target: < 10s at p95)
    - Test inventory search latency (target: < 3s at p95)
    - Test judge validation latency (target: < 2s at p95)
    - Test voice response latency (target: < 1s at p95)
    - Test end-to-end workflow latency (target: < 90s at p95)
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [ ] 14. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 15. Implement integration tests for end-to-end workflows
  - [ ] 15.1 Create integration test infrastructure
    - Set up Docker containers for orchestration layer and external system mocks
    - Configure AWS Bedrock staging environment for Nova agents
    - Set up test Linux laptop environment for local judge (Ubuntu 22.04, Ollama with Llama 3.1 8B)
    - Create test data: 500+ equipment photos, 100+ technical manuals, 10,000+ inventory items
    - _Requirements: 12.7_
  
  - [ ]* 15.2 Write integration test: Happy path network switch failure
    - Test complete workflow from photo submission to repair guide generation
    - Verify diagnosis identifies hardware defect
    - Verify inventory search finds replacement part
    - Verify purchase request generated and approved
    - Verify repair guide generated with correct steps
    - Verify all judge validations pass
    - Expected duration: 45-60 seconds
    - _Requirements: 1.1, 1.3, 3.1, 3.5, 4.1, 7.9_
  
  - [ ]* 15.3 Write integration test: Safety escalation for high voltage work
    - Test workflow with electrical panel issue photo
    - Verify diagnosis identifies electrical malfunction
    - Verify judge detects safety violation
    - Verify workflow escalates to safety officer
    - Verify technician receives hold notification
    - Expected outcome: Workflow paused, escalation created
    - _Requirements: 2.1, 2.2, 2.3, 10.1_
  
  - [ ]* 15.4 Write integration test: Budget escalation for expensive repair
    - Test workflow with diagnosis requiring $8,000 in parts
    - Verify diagnosis and inventory search complete
    - Verify judge detects budget violation
    - Verify escalation to manager approval workflow
    - Verify technician receives pending approval status
    - Expected outcome: Purchase request queued for approval
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 10.3_
  
  - [ ]* 15.5 Write integration test: Voice-guided repair session
    - Test complete voice-guided repair for cable termination
    - Simulate voice commands: "next step", "repeat", "clarification"
    - Verify audio responses generated correctly
    - Verify safety checks performed at each step
    - Verify maintenance record created on completion
    - Expected duration: 15-20 minutes (simulated)
    - _Requirements: 4.1, 4.3, 4.4, 4.5, 4.7, 4.9_
  
  - [ ]* 15.6 Write integration test: Offline recovery with judge restart
    - Test workflow with simulated judge process crash
    - Verify workflow pauses and saves state
    - Simulate judge restart
    - Verify workflow resumes from checkpoint
    - Verify no data loss
    - Expected outcome: Seamless recovery
    - _Requirements: 6.6, 6.7, 13.2, 13.3_
  
  - [ ]* 15.7 Write integration test: Multi-issue complex site problem
    - Test workflow with photo showing multiple issues (network + power)
    - Verify diagnosis identifies all issues
    - Verify issues prioritized by severity
    - Verify separate repair guides generated
    - Verify procurement handles multiple part lists
    - Expected outcome: Coordinated multi-issue resolution
    - _Requirements: 1.5, 3.1, 4.1, 14.3_

- [x] 16. Implement deployment configurations
  - [x] 16.1 Create Docker configurations for orchestration layer
    - Create Dockerfile for orchestration layer service
    - Create docker-compose.yml for local development environment
    - Configure environment variables for AWS credentials, database connections, and API endpoints
    - Configure Linux-specific resource limits for laptop deployment
    - Configure structured logging service for agent reasoning
    - _Requirements: 12.7_
  
  - [ ]* 16.2 Create local judge deployment package
    - Create installation script for Ubuntu 22.04 / Fedora 38+
    - Configure Ollama with Llama 3.1 8B Q4_K_M quantized model
    - Create systemd service for automatic judge startup
    - Configure SQLite database for audit logs
    - Document hardware requirements (16GB RAM, 8-core CPU, optional GPU)
    - _Note: System uses cloud-based judge (Amazon Bedrock), not local Ollama_
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  
  - [x] 16.3 Create AWS infrastructure configuration
    - Create Terraform/CloudFormation templates for AWS resources
    - Configure Amazon Bedrock access for Nova Pro, Nova Act, Nova 2 Sonic
    - Configure vector database (Pinecone/Weaviate) for RAG system
    - Configure S3 buckets for image storage and technical manuals
    - Configure API Gateway for orchestration layer endpoints
    - _Requirements: 12.7_
  
  - [x] 16.4 Create monitoring and observability configuration
    - Configure CloudWatch for AWS service monitoring
    - Configure application logging with structured JSON logs
    - Implement Thought-Action-Observation logging for agent reasoning
    - Create smoke test script for deployment verification
    - Configure performance metrics collection (latency, throughput, error rates)
    - Configure alerting for critical failures and SLA violations
    - _Requirements: 11.1, 11.7, 12.1, 12.2, 12.3, 12.4_

- [ ] 17. Create API documentation and developer guides
  - Create OpenAPI/Swagger specification for orchestration layer REST API
  - Document authentication and authorization requirements
  - Create developer guide for adding new equipment types to RAG system
  - Create operator guide for local judge installation and maintenance
  - Create troubleshooting guide for common deployment issues
  - _Requirements: 7.1, 8.6, 11.1_

- [ ] 18. Final checkpoint - Ensure all tests pass and system is ready for deployment
  - Run complete test suite (unit, property, integration)
  - Verify all performance benchmarks meet targets
  - Verify all error recovery scenarios work correctly
  - Verify audit logging is complete and compliant
  - Verify deployment configurations are functional
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at reasonable breaks
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows with all components
- Implementation uses TypeScript with Node.js runtime
- Amazon Nova models accessed via AWS Bedrock API
- Local judge runs on technician's Linux laptop using Ollama with Llama 3.1 8B
- RAG system uses vector database (Pinecone or Weaviate) with HNSW indexing
- External systems mocked for testing, real integrations for production
