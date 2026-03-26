# ActionAgent Documentation

## Overview

The `ActionAgent` is an agentic AI agent that uses Amazon Nova Act for autonomous tool-calling to execute parts procurement workflows. It searches inventory, checks availability, generates cost estimates, creates purchase requests, and submits them to approval workflows.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ActionAgent                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ Nova Act API │    │  Tool Chain  │    │  External    │ │
│  │  (Bedrock)   │    │  Execution   │    │  Systems     │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                    │                    │        │
│         └────────────────────┴────────────────────┘        │
│                              │                             │
│                    ┌─────────▼─────────┐                   │
│                    │   Action Result   │                   │
│                    └───────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Agentic Tool-Calling with Nova Act
- Autonomous multi-step workflow execution
- Dynamic tool selection based on context
- Dependency management between tool calls
- Automatic retry with exponential backoff

### 2. Inventory Management
- Search inventory with exact and fuzzy matching
- Check part availability and stock levels
- Find alternative compatible parts
- Estimate lead times and delivery dates

### 3. Cost Estimation
- Calculate parts cost with quantities
- Include labor cost based on estimated hours
- Add shipping cost (standard or expedited)
- Provide detailed cost breakdown

### 4. Procurement Workflow
- Generate purchase requests with justification
- Determine approval authority based on cost
- Submit to appropriate approval workflow
- Track approval status and timeline

### 5. Telemetry Integration
- Query historical telemetry data
- Retrieve alerts and anomalies
- Support time-range queries
- Integrate with diagnosis workflow

## API Reference

### ActionAgent Class

#### `__init__()`

Initialize the action agent with Nova Act.

**Example:**
```python
from src.agents.ActionAgent import ActionAgent

agent = ActionAgent()
```

---

#### `execute_tool_chain(diagnosis_result: DiagnosisResult, site_context: SiteContext) -> ActionResult`

Execute complete tool chain for parts procurement using Nova Act.

**Parameters:**
- `diagnosis_result` (DiagnosisResult): Diagnosis result with required parts
- `site_context` (SiteContext): Site context for procurement

**Returns:**
- `ActionResult`: Complete action result with procurement details

**Example:**
```python
from src.models.agents import DiagnosisResult
from src.models.domain import SiteContext, Part

diagnosis_result = DiagnosisResult(
    issue_type="hardware_defect",
    confidence=0.92,
    description="Network switch failure",
    root_cause="Hardware failure",
    severity="critical",
    required_parts=[Part(...)],
    # ... other fields
)

site_context = SiteContext(
    site_id="SITE-001",
    location="Building A",
    equipment_type="network_switch",
    technician_id="TECH-123",
    skill_level="intermediate"
)

result = agent.execute_tool_chain(diagnosis_result, site_context)
print(f"Purchase Request: {result.purchase_request_id}")
print(f"Total Cost: ${result.estimated_cost:.2f}")
```

---

#### `search_inventory(query: str, equipment_type: Optional[str] = None, fuzzy_match: bool = False) -> List[Part]`

Search inventory for parts.

**Parameters:**
- `query` (str): Search query (part number, description, or equipment type)
- `equipment_type` (Optional[str]): Filter by equipment type
- `fuzzy_match` (bool): Enable fuzzy matching for similar parts

**Returns:**
- `List[Part]`: List of matching parts

**Example:**
```python
# Exact search
parts = agent.search_inventory(
    query="NS-2960X-24TS-L",
    equipment_type="network_switch"
)

# Fuzzy search
parts = agent.search_inventory(
    query="Cisco Catalyst",
    fuzzy_match=True
)

for part in parts:
    print(f"{part.part_number}: ${part.unit_price:.2f}")
```

---

#### `check_part_availability(part_number: str, quantity: int) -> Dict[str, Any]`

Check part availability and lead time.

**Parameters:**
- `part_number` (str): Part number to check
- `quantity` (int): Required quantity

**Returns:**
- `Dict[str, Any]`: Availability information including stock, lead time, and delivery date

**Example:**
```python
availability = agent.check_part_availability(
    part_number="NS-2960X-24TS-L",
    quantity=2
)

print(f"Available: {availability['available']}")
print(f"Stock: {availability['stock_quantity']}")
print(f"Lead Time: {availability['lead_time_days']} days")
print(f"Delivery: {availability['estimated_delivery']}")
```

---

#### `generate_cost_estimate(parts: List[Part], labor_hours: float, expedited_shipping: bool = False) -> Dict[str, Any]`

Generate cost estimate for repair.

**Parameters:**
- `parts` (List[Part]): List of required parts
- `labor_hours` (float): Estimated labor hours
- `expedited_shipping` (bool): Use expedited shipping

**Returns:**
- `Dict[str, Any]`: Cost estimate with breakdown

**Example:**
```python
parts = [
    Part(part_number="NS-2960X-24TS-L", quantity=1, unit_price=1250.00, ...),
    Part(part_number="CAB-ETH-10M", quantity=5, unit_price=15.00, ...)
]

estimate = agent.generate_cost_estimate(
    parts=parts,
    labor_hours=2.5,
    expedited_shipping=False
)

print(f"Parts: ${estimate['parts_cost']:.2f}")
print(f"Labor: ${estimate['labor_cost']:.2f}")
print(f"Shipping: ${estimate['shipping_cost']:.2f}")
print(f"Total: ${estimate['total_cost']:.2f}")
```

---

#### `create_purchase_request(parts: List[str], total_cost: float, justification: str, urgency: str, site_id: str) -> Dict[str, Any]`

Create purchase request.

**Parameters:**
- `parts` (List[str]): List of part numbers
- `total_cost` (float): Total estimated cost
- `justification` (str): Business justification
- `urgency` (str): Urgency level (low, medium, high, critical)
- `site_id` (str): Site identifier

**Returns:**
- `Dict[str, Any]`: Purchase request details

**Example:**
```python
request = agent.create_purchase_request(
    parts=["NS-2960X-24TS-L"],
    total_cost=1425.00,
    justification="Critical network switch failure at Building A",
    urgency="high",
    site_id="SITE-001"
)

print(f"Request ID: {request['purchase_request_id']}")
print(f"Status: {request['status']}")
print(f"Approval Required: {request['approval_required']}")
```

---

#### `submit_to_approval_workflow(purchase_request_id: str, total_cost: float) -> Dict[str, Any]`

Submit purchase request to approval workflow.

**Parameters:**
- `purchase_request_id` (str): Purchase request ID
- `total_cost` (float): Total cost for approval routing

**Returns:**
- `Dict[str, Any]`: Approval submission details

**Example:**
```python
approval = agent.submit_to_approval_workflow(
    purchase_request_id="PR-20260225120000",
    total_cost=1425.00
)

print(f"Submitted to: {approval['submitted_to']}")
print(f"Estimated approval time: {approval['estimated_approval_time_hours']} hours")
print(f"Tracking: {approval['tracking_url']}")
```

---

#### `query_telemetry_database(site_id: str, metric_names: Optional[List[str]] = None, time_range_hours: int = 24) -> Dict[str, Any]`

Query telemetry database for historical data.

**Parameters:**
- `site_id` (str): Site identifier
- `metric_names` (Optional[List[str]]): List of metric names to query
- `time_range_hours` (int): Time range in hours (default: 24)

**Returns:**
- `Dict[str, Any]`: Telemetry data with metrics and alerts

**Example:**
```python
telemetry = agent.query_telemetry_database(
    site_id="SITE-001",
    metric_names=["cpu_temperature", "fan_speed_rpm"],
    time_range_hours=48
)

for metric, values in telemetry['metrics'].items():
    print(f"{metric}: {values}")
```

---

## Tool Definitions

The ActionAgent uses the following tools with Nova Act:

### 1. search_inventory
Search inventory database for parts by part number, description, or equipment type.

### 2. check_part_availability
Check availability, stock levels, and lead time for a specific part.

### 3. find_alternative_parts
Find alternative or compatible parts when primary part is unavailable.

### 4. calculate_cost_estimate
Calculate total cost including parts, labor, and shipping.

### 5. create_purchase_request
Create a purchase request with justification and urgency level.

### 6. submit_to_approval_workflow
Submit purchase request to appropriate approval authority based on cost.

### 7. query_telemetry_database
Query telemetry database for historical metrics and alerts.

## Approval Authority Levels

Purchase requests are routed based on total cost:

| Cost Range | Approval Authority | Estimated Time |
|------------|-------------------|----------------|
| < $1,000 | Supervisor | 2 hours |
| $1,000 - $4,999 | Manager | 24 hours |
| ≥ $5,000 | Director | 72 hours |

## Cost Calculation

Total cost is calculated as:

```
Total Cost = Parts Cost + Labor Cost + Shipping Cost

Where:
- Parts Cost = Σ(quantity × unit_price) for all parts
- Labor Cost = labor_hours × $75/hour
- Shipping Cost = $150 (expedited) or $50 (standard)
```

## Workflow Execution

The `execute_tool_chain()` method performs the following steps:

1. **Inventory Search**: Search for each required part
2. **Availability Check**: Verify stock and lead times
3. **Alternative Search**: Find alternatives if parts unavailable
4. **Cost Estimation**: Calculate total cost with breakdown
5. **Purchase Request**: Create request with justification
6. **Approval Submission**: Submit to appropriate authority

Nova Act autonomously determines which tools to call and in what order based on the diagnosis result and site context.

## Integration with Other Components

### DiagnosisAgent Integration

The ActionAgent receives diagnosis results from the DiagnosisAgent:

```python
# Diagnosis phase
diagnosis_agent = DiagnosisAgent()
diagnosis_result = diagnosis_agent.diagnose_issue(diagnosis_input)

# Action phase
action_agent = ActionAgent()
action_result = action_agent.execute_tool_chain(diagnosis_result, site_context)
```

### Cloud Judge Integration

Action results are validated by the Cloud Judge for:
- Budget compliance
- Approval authority correctness
- Cost calculation accuracy
- Procurement policy adherence

### External Systems Integration

The ActionAgent integrates with:
- **Inventory System**: Part search and availability
- **Procurement System**: Purchase order creation
- **Telemetry System**: Historical data queries
- **Approval System**: Workflow submission

## Performance Characteristics

- **Target Latency**: < 3 seconds at p95 for inventory search
- **Tool Iterations**: Typically 3-7 iterations for complete workflow
- **Retry Logic**: Max 3 retries with exponential backoff
- **Concurrent Requests**: Supports parallel tool execution

## Error Handling

The agent handles the following error scenarios:

1. **API Failures**: Automatic retry with exponential backoff
2. **Part Not Found**: Alternative parts search
3. **Out of Stock**: Lead time estimation and alternatives
4. **Invalid Cost**: Recalculation with validation
5. **Approval Timeout**: Status tracking and notifications

## Best Practices

### For Optimal Results

1. **Provide Complete Diagnosis**: Include all required parts and details
2. **Accurate Labor Estimates**: Use realistic repair time estimates
3. **Appropriate Urgency**: Set urgency based on severity
4. **Clear Justification**: Provide business justification for approval

### For Cost Optimization

1. **Check Alternatives**: Enable fuzzy matching for compatible parts
2. **Standard Shipping**: Use expedited only when necessary
3. **Batch Orders**: Combine multiple repairs when possible
4. **Lead Time Planning**: Consider lead times in scheduling

## Example Workflows

### Basic Procurement Workflow

```python
# 1. Create diagnosis result
diagnosis_result = DiagnosisResult(...)

# 2. Create site context
site_context = SiteContext(...)

# 3. Execute tool chain
action_agent = ActionAgent()
result = action_agent.execute_tool_chain(diagnosis_result, site_context)

# 4. Check result
if result.status == "completed":
    print(f"Purchase request created: {result.purchase_request_id}")
    print(f"Total cost: ${result.estimated_cost:.2f}")
else:
    print(f"Action failed: {result.description}")
```

### Manual Inventory Search

```python
# 1. Search inventory
parts = agent.search_inventory(
    query="network switch",
    equipment_type="network_switch",
    fuzzy_match=True
)

# 2. Check availability
for part in parts:
    availability = agent.check_part_availability(
        part_number=part.part_number,
        quantity=1
    )
    print(f"{part.part_number}: {availability['available']}")
```

### Cost Estimation Only

```python
# 1. Define parts
parts = [Part(...), Part(...)]

# 2. Generate estimate
estimate = agent.generate_cost_estimate(
    parts=parts,
    labor_hours=3.0,
    expedited_shipping=False
)

# 3. Review breakdown
print(f"Total: ${estimate['total_cost']:.2f}")
print(f"Breakdown: {estimate['breakdown']}")
```

## Troubleshooting

### Part Not Found

**Problem**: Inventory search returns no results

**Solutions:**
- Enable fuzzy matching
- Use broader search terms
- Check equipment type filter
- Search by category instead of part number

### High Cost Estimate

**Problem**: Cost exceeds budget

**Solutions:**
- Search for alternative parts
- Use standard shipping instead of expedited
- Reduce labor hours estimate
- Consider temporary workarounds

### Approval Delays

**Problem**: Purchase request pending for extended time

**Solutions:**
- Check approval authority routing
- Verify justification is clear
- Escalate if SLA violated
- Consider expedited approval process

## Future Enhancements

Planned improvements for future versions:

1. **Bulk Procurement**: Handle multiple sites simultaneously
2. **Vendor Comparison**: Compare prices across suppliers
3. **Inventory Prediction**: Predict part needs based on trends
4. **Contract Pricing**: Apply contract discounts automatically
5. **Supplier Integration**: Direct API integration with suppliers

## Related Documentation

- [DiagnosisAgent Documentation](./diagnosis_agent.md)
- [Cloud Judge Architecture](./cloud_judge_architecture.md)
- [Data Models Reference](../src/models/README.md)
- [API Examples](../examples/action_agent_example.py)
