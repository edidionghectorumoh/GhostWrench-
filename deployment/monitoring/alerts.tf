# CloudWatch Alarms for Autonomous Field Engineer

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts-${var.environment}"
  
  tags = {
    Name        = "AFE Alerts"
    Environment = var.environment
    Project     = var.project_name
  }
}

# High Diagnosis Latency Alarm
resource "aws_cloudwatch_metric_alarm" "high_diagnosis_latency" {
  alarm_name          = "${var.project_name}-high-diagnosis-latency-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "diagnosis_duration_ms"
  namespace           = "AutonomousFieldEngineer"
  period              = "300"
  statistic           = "Average"
  threshold           = "10000"  # 10 seconds
  alarm_description   = "Diagnosis latency exceeds 10 seconds"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  tags = {
    Name        = "High Diagnosis Latency"
    Environment = var.environment
    Severity    = "warning"
  }
}

# High Judge Validation Latency Alarm
resource "aws_cloudwatch_metric_alarm" "high_judge_latency" {
  alarm_name          = "${var.project_name}-high-judge-latency-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "judge_validation_duration_ms"
  namespace           = "AutonomousFieldEngineer"
  period              = "300"
  statistic           = "Average"
  threshold           = "2000"  # 2 seconds
  alarm_description   = "Judge validation latency exceeds 2 seconds"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  tags = {
    Name        = "High Judge Latency"
    Environment = var.environment
    Severity    = "warning"
  }
}

# High Workflow Failure Rate Alarm
resource "aws_cloudwatch_metric_alarm" "high_failure_rate" {
  alarm_name          = "${var.project_name}-high-failure-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "workflow_failure_count"
  namespace           = "AutonomousFieldEngineer"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"  # 5 failures in 5 minutes
  alarm_description   = "Workflow failure rate is high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  tags = {
    Name        = "High Failure Rate"
    Environment = var.environment
    Severity    = "critical"
  }
}

# High Escalation Rate Alarm
resource "aws_cloudwatch_metric_alarm" "high_escalation_rate" {
  alarm_name          = "${var.project_name}-high-escalation-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "escalation_count"
  namespace           = "AutonomousFieldEngineer"
  period              = "3600"  # 1 hour
  statistic           = "Sum"
  threshold           = "10"  # 10 escalations per hour
  alarm_description   = "Escalation rate is unusually high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  tags = {
    Name        = "High Escalation Rate"
    Environment = var.environment
    Severity    = "warning"
  }
}

# Bedrock API Error Rate Alarm
resource "aws_cloudwatch_metric_alarm" "bedrock_errors" {
  alarm_name          = "${var.project_name}-bedrock-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Bedrock"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "High error rate from Bedrock API"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    ModelId = "amazon.nova-pro-v1:0"
  }
  
  tags = {
    Name        = "Bedrock API Errors"
    Environment = var.environment
    Severity    = "critical"
  }
}

# Weaviate Connection Errors
resource "aws_cloudwatch_log_metric_filter" "weaviate_errors" {
  name           = "${var.project_name}-weaviate-errors-${var.environment}"
  log_group_name = "/aws/afe/${var.project_name}-${var.environment}"
  pattern        = "[ERROR] *Weaviate*"
  
  metric_transformation {
    name      = "weaviate_error_count"
    namespace = "AutonomousFieldEngineer"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "weaviate_connection_errors" {
  alarm_name          = "${var.project_name}-weaviate-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "weaviate_error_count"
  namespace           = "AutonomousFieldEngineer"
  period              = "300"
  statistic           = "Sum"
  threshold           = "3"
  alarm_description   = "Weaviate connection errors detected"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  tags = {
    Name        = "Weaviate Errors"
    Environment = var.environment
    Severity    = "critical"
  }
}

# Output
output "alerts_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}
