"""
ActionAgent: Agentic action execution using Amazon Nova Act.

This agent uses Nova Act's tool-calling capabilities to:
- Search inventory databases
- Check part availability
- Generate cost estimates
- Create purchase requests
- Submit to approval workflows
- Query telemetry databases
"""

import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from config import bedrock_runtime
from src.models.agents import ActionResult, DiagnosisResult
from src.models.domain import Part, SiteContext


class ActionAgent:
    """
    Agentic action agent using Amazon Nova Act for tool-calling.
    
    Capabilities:
    - Inventory search with exact and fuzzy matching
    - Part availability checking
    - Cost estimation (parts + labor + shipping)
    - Purchase request generation
    - Approval workflow submission
    - Telemetry database queries
    """
    
    def __init__(self):
        """Initialize the action agent with Nova Act."""
        self.model_id = "us.amazon.nova-act-v1:0"
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        
        # Tool definitions for Nova Act
        self.tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """
        Define tool schemas for Nova Act tool-calling.
        
        Returns:
            List of tool definitions with schemas
        """
        return [
            {
                "name": "search_inventory",
                "description": "Search inventory database for parts by part number, description, or equipment type. Supports exact and fuzzy matching.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (part number, description, or equipment type)"
                        },
                        "equipment_type": {
                            "type": "string",
                            "description": "Filter by equipment type (optional)"
                        },
                        "fuzzy_match": {
                            "type": "boolean",
                            "description": "Enable fuzzy matching for similar parts"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "check_part_availability",
                "description": "Check availability, stock levels, and lead time for a specific part.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "part_number": {
                            "type": "string",
                            "description": "Part number to check"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Required quantity"
                        }
                    },
                    "required": ["part_number", "quantity"]
                }
            },
            {
                "name": "find_alternative_parts",
                "description": "Find alternative or compatible parts when primary part is unavailable.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "part_number": {
                            "type": "string",
                            "description": "Original part number"
                        },
                        "equipment_type": {
                            "type": "string",
                            "description": "Equipment type for compatibility"
                        }
                    },
                    "required": ["part_number", "equipment_type"]
                }
            },
            {
                "name": "calculate_cost_estimate",
                "description": "Calculate total cost including parts, labor, and shipping.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "parts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "part_number": {"type": "string"},
                                    "quantity": {"type": "integer"},
                                    "unit_price": {"type": "number"}
                                }
                            },
                            "description": "List of parts with quantities and prices"
                        },
                        "labor_hours": {
                            "type": "number",
                            "description": "Estimated labor hours"
                        },
                        "expedited_shipping": {
                            "type": "boolean",
                            "description": "Use expedited shipping"
                        }
                    },
                    "required": ["parts", "labor_hours"]
                }
            },
            {
                "name": "create_purchase_request",
                "description": "Create a purchase request with justification and urgency level.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "parts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of part numbers"
                        },
                        "total_cost": {
                            "type": "number",
                            "description": "Total estimated cost"
                        },
                        "justification": {
                            "type": "string",
                            "description": "Business justification for purchase"
                        },
                        "urgency": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                            "description": "Urgency level"
                        },
                        "site_id": {
                            "type": "string",
                            "description": "Site identifier"
                        }
                    },
                    "required": ["parts", "total_cost", "justification", "urgency", "site_id"]
                }
            },
            {
                "name": "submit_to_approval_workflow",
                "description": "Submit purchase request to appropriate approval authority based on cost.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "purchase_request_id": {
                            "type": "string",
                            "description": "Purchase request ID"
                        },
                        "total_cost": {
                            "type": "number",
                            "description": "Total cost for approval routing"
                        }
                    },
                    "required": ["purchase_request_id", "total_cost"]
                }
            },
            {
                "name": "query_telemetry_database",
                "description": "Query telemetry database for historical metrics and alerts.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "Site identifier"
                        },
                        "metric_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of metric names to query"
                        },
                        "time_range_hours": {
                            "type": "integer",
                            "description": "Time range in hours (default: 24)"
                        }
                    },
                    "required": ["site_id"]
                }
            }
        ]
    
    def _call_nova_act(self, prompt: str, max_tool_iterations: int = 5) -> Dict[str, Any]:
        """
        Call Amazon Nova Act with tool-calling support.
        
        Args:
            prompt: User prompt describing the task
            max_tool_iterations: Maximum number of tool-calling iterations
            
        Returns:
            Final response with tool execution results
        """
        messages = [{"role": "user", "content": prompt}]
        tool_results = []
        
        for iteration in range(max_tool_iterations):
            try:
                # Call Nova Act
                response = bedrock_runtime.converse(
                    modelId=self.model_id,
                    messages=messages,
                    toolConfig={"tools": self.tools}
                )
                
                # Extract response
                output_message = response['output']['message']
                stop_reason = response['stopReason']
                
                # Add assistant message to conversation
                messages.append(output_message)
                
                # Check if tool use is requested
                if stop_reason == 'tool_use':
                    # Execute tools
                    tool_use_blocks = [
                        block for block in output_message['content']
                        if 'toolUse' in block
                    ]
                    
                    tool_result_blocks = []
                    for tool_use in tool_use_blocks:
                        tool_name = tool_use['toolUse']['name']
                        tool_input = tool_use['toolUse']['input']
                        tool_use_id = tool_use['toolUse']['toolUseId']
                        
                        # Execute tool
                        tool_result = self._execute_tool(tool_name, tool_input)
                        tool_results.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "result": tool_result
                        })
                        
                        # Add tool result to conversation
                        tool_result_blocks.append({
                            "toolResult": {
                                "toolUseId": tool_use_id,
                                "content": [{"json": tool_result}]
                            }
                        })
                    
                    # Add tool results as user message
                    messages.append({
                        "role": "user",
                        "content": tool_result_blocks
                    })
                    
                elif stop_reason == 'end_turn':
                    # Final response
                    text_content = [
                        block['text'] for block in output_message['content']
                        if 'text' in block
                    ]
                    
                    return {
                        "response": " ".join(text_content),
                        "tool_executions": tool_results,
                        "iterations": iteration + 1
                    }
                
            except Exception as e:
                print(f"Error calling Nova Act: {e}")
                return {
                    "response": f"Error: {str(e)}",
                    "tool_executions": tool_results,
                    "iterations": iteration + 1,
                    "error": str(e)
                }
        
        # Max iterations reached
        return {
            "response": "Max tool iterations reached",
            "tool_executions": tool_results,
            "iterations": max_tool_iterations
        }
    
    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool and return results.
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Tool input parameters
            
        Returns:
            Tool execution result
        """
        # Map tool names to execution methods
        tool_map = {
            "search_inventory": self._tool_search_inventory,
            "check_part_availability": self._tool_check_part_availability,
            "find_alternative_parts": self._tool_find_alternative_parts,
            "calculate_cost_estimate": self._tool_calculate_cost_estimate,
            "create_purchase_request": self._tool_create_purchase_request,
            "submit_to_approval_workflow": self._tool_submit_to_approval_workflow,
            "query_telemetry_database": self._tool_query_telemetry_database
        }
        
        if tool_name in tool_map:
            return tool_map[tool_name](tool_input)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    # Tool execution methods (mock implementations for now)
    
    def _tool_search_inventory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock inventory search."""
        query = params.get("query", "")
        equipment_type = params.get("equipment_type")
        fuzzy_match = params.get("fuzzy_match", False)
        
        # Mock results
        return {
            "results": [
                {
                    "part_number": "NS-2960X-24TS-L",
                    "description": "Cisco Catalyst 2960-X 24 Port Switch",
                    "category": "network_switch",
                    "unit_price": 1250.00,
                    "in_stock": True,
                    "stock_quantity": 15
                },
                {
                    "part_number": "NS-2960X-48TS-L",
                    "description": "Cisco Catalyst 2960-X 48 Port Switch",
                    "category": "network_switch",
                    "unit_price": 1850.00,
                    "in_stock": True,
                    "stock_quantity": 8
                }
            ],
            "total_results": 2,
            "query": query,
            "fuzzy_match_used": fuzzy_match
        }
    
    def _tool_check_part_availability(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock part availability check."""
        part_number = params.get("part_number", "")
        quantity = params.get("quantity", 1)
        
        return {
            "part_number": part_number,
            "available": True,
            "stock_quantity": 15,
            "requested_quantity": quantity,
            "lead_time_days": 2,
            "supplier": "Primary Distributor",
            "unit_price": 1250.00,
            "estimated_delivery": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        }
    
    def _tool_find_alternative_parts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock alternative parts search."""
        part_number = params.get("part_number", "")
        equipment_type = params.get("equipment_type", "")
        
        return {
            "original_part": part_number,
            "alternatives": [
                {
                    "part_number": "NS-2960X-24TS-LL",
                    "description": "Cisco Catalyst 2960-X 24 Port Switch (Lite)",
                    "compatibility": "full",
                    "unit_price": 1100.00,
                    "in_stock": True,
                    "lead_time_days": 1
                }
            ],
            "total_alternatives": 1
        }
    
    def _tool_calculate_cost_estimate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate total cost estimate."""
        parts = params.get("parts", [])
        labor_hours = params.get("labor_hours", 0)
        expedited_shipping = params.get("expedited_shipping", False)
        
        # Calculate parts cost
        parts_cost = sum(
            part.get("quantity", 1) * part.get("unit_price", 0)
            for part in parts
        )
        
        # Calculate labor cost ($75/hour)
        labor_cost = labor_hours * 75.0
        
        # Calculate shipping cost
        shipping_cost = 150.0 if expedited_shipping else 50.0
        
        # Total cost
        total_cost = parts_cost + labor_cost + shipping_cost
        
        return {
            "parts_cost": parts_cost,
            "labor_cost": labor_cost,
            "labor_hours": labor_hours,
            "labor_rate_per_hour": 75.0,
            "shipping_cost": shipping_cost,
            "expedited_shipping": expedited_shipping,
            "total_cost": total_cost,
            "breakdown": {
                "parts": parts_cost,
                "labor": labor_cost,
                "shipping": shipping_cost
            }
        }
    
    def _tool_create_purchase_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create purchase request."""
        parts = params.get("parts", [])
        total_cost = params.get("total_cost", 0)
        justification = params.get("justification", "")
        urgency = params.get("urgency", "medium")
        site_id = params.get("site_id", "")
        
        # Generate request ID
        request_id = f"PR-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        return {
            "purchase_request_id": request_id,
            "status": "pending_approval",
            "parts": parts,
            "total_cost": total_cost,
            "justification": justification,
            "urgency": urgency,
            "site_id": site_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "approval_required": total_cost > 5000.0
        }
    
    def _tool_submit_to_approval_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Submit to approval workflow."""
        request_id = params.get("purchase_request_id", "")
        total_cost = params.get("total_cost", 0)
        
        # Determine approval authority
        if total_cost < 1000:
            approval_authority = "supervisor"
            estimated_approval_time_hours = 2
        elif total_cost < 5000:
            approval_authority = "manager"
            estimated_approval_time_hours = 24
        else:
            approval_authority = "director"
            estimated_approval_time_hours = 72
        
        return {
            "purchase_request_id": request_id,
            "submitted_to": approval_authority,
            "submission_time": datetime.now(timezone.utc).isoformat(),
            "estimated_approval_time_hours": estimated_approval_time_hours,
            "approval_status": "pending",
            "tracking_url": f"https://procurement.example.com/requests/{request_id}"
        }
    
    def _tool_query_telemetry_database(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock telemetry database query."""
        site_id = params.get("site_id", "")
        metric_names = params.get("metric_names", [])
        time_range_hours = params.get("time_range_hours", 24)
        
        return {
            "site_id": site_id,
            "time_range_hours": time_range_hours,
            "metrics": {
                "cpu_temperature": [45.2, 46.1, 85.5, 87.2],
                "fan_speed_rpm": [3000, 2950, 0, 0],
                "power_draw_watts": [400, 405, 450, 455]
            },
            "alerts": [
                {"timestamp": datetime.now(timezone.utc).isoformat(), "alert": "HIGH_TEMPERATURE"},
                {"timestamp": datetime.now(timezone.utc).isoformat(), "alert": "FAN_FAILURE"}
            ]
        }
    
    # High-level methods
    
    def execute_tool_chain(
        self,
        diagnosis_result: DiagnosisResult,
        site_context: SiteContext
    ) -> ActionResult:
        """
        Execute complete tool chain for parts procurement.
        
        Args:
            diagnosis_result: Diagnosis result with required parts
            site_context: Site context
            
        Returns:
            ActionResult with procurement details
        """
        # Build prompt for Nova Act
        prompt = self._build_procurement_prompt(diagnosis_result, site_context)
        
        # Execute with Nova Act
        result = self._call_nova_act(prompt, max_tool_iterations=10)
        
        # Parse result into ActionResult
        return self._parse_action_result(result, diagnosis_result, site_context)
    
    def _build_procurement_prompt(
        self,
        diagnosis_result: DiagnosisResult,
        site_context: SiteContext
    ) -> str:
        """Build prompt for Nova Act procurement task."""
        parts_list = "\n".join([
            f"- {part.part_number}: {part.description} (Quantity: {part.quantity})"
            for part in diagnosis_result.required_parts
        ])
        
        prompt = f"""You are an autonomous procurement agent. Your task is to procure parts for a field repair.

**Site Information:**
- Site ID: {site_context.site_id}
- Location: {site_context.location}
- Equipment Type: {site_context.equipment_type}

**Diagnosis:**
- Issue: {diagnosis_result.issue_type}
- Description: {diagnosis_result.description}
- Root Cause: {diagnosis_result.root_cause}
- Severity: {diagnosis_result.severity}

**Required Parts:**
{parts_list}

**Estimated Repair Time:** {diagnosis_result.estimated_repair_time_minutes} minutes

**Your Task:**
1. Search inventory for each required part
2. Check availability and lead times
3. If parts unavailable, find alternatives
4. Calculate total cost estimate (parts + labor + shipping)
5. Create purchase request with justification
6. Submit to appropriate approval workflow

**Urgency:** {"high" if diagnosis_result.severity == "critical" else "medium"}

Please execute the procurement workflow and provide a summary of actions taken.
"""
        return prompt
    
    def _parse_action_result(
        self,
        nova_result: Dict[str, Any],
        diagnosis_result: DiagnosisResult,
        site_context: SiteContext
    ) -> ActionResult:
        """Parse Nova Act result into ActionResult."""
        # Extract tool executions
        tool_executions = nova_result.get("tool_executions", [])
        
        # Find purchase request and cost estimate
        purchase_request = None
        cost_estimate = None
        approval_submission = None
        
        for execution in tool_executions:
            if execution["tool"] == "create_purchase_request":
                purchase_request = execution["result"]
            elif execution["tool"] == "calculate_cost_estimate":
                cost_estimate = execution["result"]
            elif execution["tool"] == "submit_to_approval_workflow":
                approval_submission = execution["result"]
        
        # Build ActionResult
        return ActionResult(
            action_type="parts_procurement",
            status="completed" if purchase_request else "failed",
            description=nova_result.get("response", ""),
            tool_calls_executed=[ex["tool"] for ex in tool_executions],
            purchase_request_id=purchase_request.get("purchase_request_id") if purchase_request else None,
            estimated_cost=cost_estimate.get("total_cost") if cost_estimate else 0.0,
            approval_required=purchase_request.get("approval_required", False) if purchase_request else False,
            approval_status=approval_submission.get("approval_status") if approval_submission else "pending",
            estimated_delivery_date=None,  # Would be extracted from availability check
            execution_details={
                "tool_executions": tool_executions,
                "iterations": nova_result.get("iterations", 0),
                "cost_breakdown": cost_estimate.get("breakdown") if cost_estimate else None
            }
        )
    
    def search_inventory(
        self,
        query: str,
        equipment_type: Optional[str] = None,
        fuzzy_match: bool = False
    ) -> List[Part]:
        """
        Search inventory for parts.
        
        Args:
            query: Search query
            equipment_type: Filter by equipment type
            fuzzy_match: Enable fuzzy matching
            
        Returns:
            List of matching parts
        """
        result = self._tool_search_inventory({
            "query": query,
            "equipment_type": equipment_type,
            "fuzzy_match": fuzzy_match
        })
        
        # Convert to Part objects
        parts = []
        for item in result.get("results", []):
            parts.append(Part(
                part_number=item["part_number"],
                description=item["description"],
                category=item["category"],
                quantity=1,
                unit_price=item["unit_price"],
                lead_time_days=2,
                supplier="Primary Distributor"
            ))
        
        return parts
    
    def check_part_availability(
        self,
        part_number: str,
        quantity: int
    ) -> Dict[str, Any]:
        """
        Check part availability.
        
        Args:
            part_number: Part number
            quantity: Required quantity
            
        Returns:
            Availability information
        """
        return self._tool_check_part_availability({
            "part_number": part_number,
            "quantity": quantity
        })
    
    def generate_cost_estimate(
        self,
        parts: List[Part],
        labor_hours: float,
        expedited_shipping: bool = False
    ) -> Dict[str, Any]:
        """
        Generate cost estimate.
        
        Args:
            parts: List of parts
            labor_hours: Estimated labor hours
            expedited_shipping: Use expedited shipping
            
        Returns:
            Cost estimate breakdown
        """
        parts_data = [
            {
                "part_number": part.part_number,
                "quantity": part.quantity,
                "unit_price": part.unit_price
            }
            for part in parts
        ]
        
        return self._tool_calculate_cost_estimate({
            "parts": parts_data,
            "labor_hours": labor_hours,
            "expedited_shipping": expedited_shipping
        })
    
    def create_purchase_request(
        self,
        parts: List[str],
        total_cost: float,
        justification: str,
        urgency: str,
        site_id: str
    ) -> Dict[str, Any]:
        """
        Create purchase request.
        
        Args:
            parts: List of part numbers
            total_cost: Total cost
            justification: Business justification
            urgency: Urgency level
            site_id: Site identifier
            
        Returns:
            Purchase request details
        """
        return self._tool_create_purchase_request({
            "parts": parts,
            "total_cost": total_cost,
            "justification": justification,
            "urgency": urgency,
            "site_id": site_id
        })
    
    def submit_to_approval_workflow(
        self,
        purchase_request_id: str,
        total_cost: float
    ) -> Dict[str, Any]:
        """
        Submit purchase request to approval workflow.
        
        Args:
            purchase_request_id: Purchase request ID
            total_cost: Total cost
            
        Returns:
            Approval submission details
        """
        return self._tool_submit_to_approval_workflow({
            "purchase_request_id": purchase_request_id,
            "total_cost": total_cost
        })
    
    def query_telemetry_database(
        self,
        site_id: str,
        metric_names: Optional[List[str]] = None,
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Query telemetry database.
        
        Args:
            site_id: Site identifier
            metric_names: List of metric names
            time_range_hours: Time range in hours
            
        Returns:
            Telemetry data
        """
        return self._tool_query_telemetry_database({
            "site_id": site_id,
            "metric_names": metric_names or [],
            "time_range_hours": time_range_hours
        })
