# Step Functions Module - Creates state machine for DICOM processing workflow

# Load and substitute variables in state machine definition
locals {
  state_machine_definition = templatefile(var.definition_path, {
    IngestionLambdaArn        = var.ingestion_lambda_arn
    ValidationLambdaArn       = var.validation_lambda_arn
    DeidentificationLambdaArn = var.deidentification_lambda_arn
    S3Bucket                  = var.raw_bucket_name
  })
}

# Step Functions State Machine
resource "aws_sfn_state_machine" "dicom_processing" {
  name     = var.state_machine_name
  role_arn = var.execution_role_arn

  definition = local.state_machine_definition

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = merge(
    var.tags,
    {
      Name = var.state_machine_name
      Type = "DICOM Processing Workflow"
    }
  )
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/stepfunctions/${var.state_machine_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# EventBridge Rule to trigger Step Functions on S3 events (alternative to direct Lambda trigger)
resource "aws_cloudwatch_event_rule" "s3_upload" {
  count       = var.enable_eventbridge_trigger ? 1 : 0
  name        = "${var.project_name}-s3-upload-trigger"
  description = "Trigger Step Functions when DICOM file uploaded to S3"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [var.raw_bucket_name]
      }
      object = {
        key = [{
          suffix = ".dcm"
        }]
      }
    }
  })

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "step_functions" {
  count     = var.enable_eventbridge_trigger ? 1 : 0
  rule      = aws_cloudwatch_event_rule.s3_upload[0].name
  target_id = "TriggerStepFunctions"
  arn       = aws_sfn_state_machine.dicom_processing.arn
  role_arn  = var.eventbridge_role_arn
}

# CloudWatch Alarms for Step Functions monitoring
resource "aws_cloudwatch_metric_alarm" "execution_failed" {
  alarm_name          = "${var.state_machine_name}-execution-failed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert when Step Functions execution fails"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.dicom_processing.arn
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "execution_timeout" {
  alarm_name          = "${var.state_machine_name}-execution-timeout"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionTimedOut"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert when Step Functions execution times out"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.dicom_processing.arn
  }

  tags = var.tags
}
