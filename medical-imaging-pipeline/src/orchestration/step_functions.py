"""
AWS Step Functions handler for DICOM processing workflow.

Provides methods for managing Step Functions state machines and executions.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from src.utils.logger import get_logger, log_execution

logger = get_logger(__name__)


class StepFunctionsHandler:
    """
    Handler for AWS Step Functions workflow orchestration.

    Manages state machine creation, execution, and monitoring.
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ) -> None:
        """
        Initialize Step Functions handler.

        Args:
            region_name: AWS region (default: us-east-1)
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
        """
        self.region_name = region_name

        # Initialize Step Functions client
        session_kwargs = {"region_name": region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.sfn_client = boto3.client("stepfunctions", **session_kwargs)

    def create_state_machine(
        self,
        name: str,
        definition: Dict[str, Any],
        role_arn: str,
        logging_config: Optional[Dict[str, Any]] = None,
        tags: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Create Step Functions state machine.

        Args:
            name: State machine name
            definition: State machine definition (ASL JSON)
            role_arn: IAM role ARN for execution
            logging_config: CloudWatch logging configuration
            tags: Resource tags

        Returns:
            Dictionary with state machine ARN and creation date

        Raises:
            ClientError: If creation fails
        """
        log_execution(
            logger,
            operation="create_state_machine",
            status="started",
            details={"name": name},
        )

        try:
            # Convert definition to JSON string if dict
            if isinstance(definition, dict):
                definition_str = json.dumps(definition)
            else:
                definition_str = definition

            # Prepare create request
            create_kwargs = {
                "name": name,
                "definition": definition_str,
                "roleArn": role_arn,
                "type": "STANDARD",
            }

            if logging_config:
                create_kwargs["loggingConfiguration"] = logging_config

            if tags:
                create_kwargs["tags"] = tags

            # Create state machine
            response = self.sfn_client.create_state_machine(**create_kwargs)

            result = {
                "state_machine_arn": response["stateMachineArn"],
                "creation_date": response["creationDate"].isoformat(),
            }

            log_execution(
                logger,
                operation="create_state_machine",
                status="completed",
                details=result,
            )

            return result

        except ClientError as e:
            log_execution(
                logger,
                operation="create_state_machine",
                status="failed",
                details={"name": name},
                error=e,
            )
            raise

    def start_execution(
        self,
        state_machine_arn: str,
        execution_input: Dict[str, Any],
        execution_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Start Step Functions execution.

        Args:
            state_machine_arn: State machine ARN
            execution_input: Input data for execution
            execution_name: Execution name (auto-generated if None)

        Returns:
            Dictionary with execution ARN and start date

        Raises:
            ClientError: If execution fails to start
        """
        log_execution(
            logger,
            operation="start_execution",
            status="started",
            details={"state_machine_arn": state_machine_arn},
        )

        try:
            # Convert input to JSON string
            input_str = json.dumps(execution_input)

            # Prepare start request
            start_kwargs = {
                "stateMachineArn": state_machine_arn,
                "input": input_str,
            }

            if execution_name:
                start_kwargs["name"] = execution_name

            # Start execution
            response = self.sfn_client.start_execution(**start_kwargs)

            result = {
                "execution_arn": response["executionArn"],
                "start_date": response["startDate"].isoformat(),
            }

            log_execution(
                logger,
                operation="start_execution",
                status="completed",
                details=result,
            )

            return result

        except ClientError as e:
            log_execution(
                logger,
                operation="start_execution",
                status="failed",
                details={"state_machine_arn": state_machine_arn},
                error=e,
            )
            raise

    def describe_execution(self, execution_arn: str) -> Dict[str, Any]:
        """
        Get execution details and status.

        Args:
            execution_arn: Execution ARN

        Returns:
            Dictionary with execution details

        Raises:
            ClientError: If describe fails
        """
        log_execution(
            logger,
            operation="describe_execution",
            status="started",
            details={"execution_arn": execution_arn},
        )

        try:
            response = self.sfn_client.describe_execution(executionArn=execution_arn)

            result = {
                "execution_arn": response["executionArn"],
                "state_machine_arn": response["stateMachineArn"],
                "name": response["name"],
                "status": response["status"],
                "start_date": response["startDate"].isoformat(),
            }

            # Add optional fields if present
            if "stopDate" in response:
                result["stop_date"] = response["stopDate"].isoformat()

            if "input" in response:
                result["input"] = json.loads(response["input"])

            if "output" in response:
                result["output"] = json.loads(response["output"])

            if "error" in response:
                result["error"] = response["error"]

            if "cause" in response:
                result["cause"] = response["cause"]

            log_execution(
                logger,
                operation="describe_execution",
                status="completed",
                details={"status": result["status"]},
            )

            return result

        except ClientError as e:
            log_execution(
                logger,
                operation="describe_execution",
                status="failed",
                details={"execution_arn": execution_arn},
                error=e,
            )
            raise

    def list_executions(
        self,
        state_machine_arn: str,
        status_filter: Optional[str] = None,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List executions for a state machine.

        Args:
            state_machine_arn: State machine ARN
            status_filter: Filter by status (RUNNING, SUCCEEDED, FAILED, etc.)
            max_results: Maximum number of results

        Returns:
            List of execution summaries

        Raises:
            ClientError: If list operation fails
        """
        log_execution(
            logger,
            operation="list_executions",
            status="started",
            details={"state_machine_arn": state_machine_arn},
        )

        try:
            # Prepare list request
            list_kwargs = {
                "stateMachineArn": state_machine_arn,
                "maxResults": max_results,
            }

            if status_filter:
                list_kwargs["statusFilter"] = status_filter

            # List executions
            response = self.sfn_client.list_executions(**list_kwargs)

            executions = []
            for execution in response.get("executions", []):
                exec_summary = {
                    "execution_arn": execution["executionArn"],
                    "name": execution["name"],
                    "status": execution["status"],
                    "start_date": execution["startDate"].isoformat(),
                }

                if "stopDate" in execution:
                    exec_summary["stop_date"] = execution["stopDate"].isoformat()

                executions.append(exec_summary)

            log_execution(
                logger,
                operation="list_executions",
                status="completed",
                details={"count": len(executions)},
            )

            return executions

        except ClientError as e:
            log_execution(
                logger,
                operation="list_executions",
                status="failed",
                details={"state_machine_arn": state_machine_arn},
                error=e,
            )
            raise

    def stop_execution(
        self,
        execution_arn: str,
        error: Optional[str] = None,
        cause: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Stop a running execution.

        Args:
            execution_arn: Execution ARN
            error: Error code
            cause: Error cause description

        Returns:
            Dictionary with stop date

        Raises:
            ClientError: If stop fails
        """
        log_execution(
            logger,
            operation="stop_execution",
            status="started",
            details={"execution_arn": execution_arn},
        )

        try:
            # Prepare stop request
            stop_kwargs = {"executionArn": execution_arn}

            if error:
                stop_kwargs["error"] = error

            if cause:
                stop_kwargs["cause"] = cause

            # Stop execution
            response = self.sfn_client.stop_execution(**stop_kwargs)

            result = {"stop_date": response["stopDate"].isoformat()}

            log_execution(
                logger,
                operation="stop_execution",
                status="completed",
                details=result,
            )

            return result

        except ClientError as e:
            log_execution(
                logger,
                operation="stop_execution",
                status="failed",
                details={"execution_arn": execution_arn},
                error=e,
            )
            raise

    def delete_state_machine(self, state_machine_arn: str) -> bool:
        """
        Delete a state machine.

        Args:
            state_machine_arn: State machine ARN

        Returns:
            True if deleted successfully

        Raises:
            ClientError: If deletion fails
        """
        log_execution(
            logger,
            operation="delete_state_machine",
            status="started",
            details={"state_machine_arn": state_machine_arn},
        )

        try:
            self.sfn_client.delete_state_machine(stateMachineArn=state_machine_arn)

            log_execution(
                logger,
                operation="delete_state_machine",
                status="completed",
                details={"state_machine_arn": state_machine_arn},
            )

            return True

        except ClientError as e:
            log_execution(
                logger,
                operation="delete_state_machine",
                status="failed",
                details={"state_machine_arn": state_machine_arn},
                error=e,
            )
            raise

    def describe_state_machine(self, state_machine_arn: str) -> Dict[str, Any]:
        """
        Get state machine details.

        Args:
            state_machine_arn: State machine ARN

        Returns:
            Dictionary with state machine details

        Raises:
            ClientError: If describe fails
        """
        try:
            response = self.sfn_client.describe_state_machine(stateMachineArn=state_machine_arn)

            result = {
                "state_machine_arn": response["stateMachineArn"],
                "name": response["name"],
                "status": response["status"],
                "definition": json.loads(response["definition"]),
                "role_arn": response["roleArn"],
                "type": response["type"],
                "creation_date": response["creationDate"].isoformat(),
            }

            if "loggingConfiguration" in response:
                result["logging_configuration"] = response["loggingConfiguration"]

            return result

        except ClientError as e:
            log_execution(
                logger,
                operation="describe_state_machine",
                status="failed",
                details={"state_machine_arn": state_machine_arn},
                error=e,
            )
            raise

    @staticmethod
    def load_state_machine_definition(file_path: str) -> Dict[str, Any]:
        """
        Load state machine definition from JSON file.

        Args:
            file_path: Path to ASL JSON file

        Returns:
            State machine definition as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"State machine definition not found: {file_path}")

        with open(path, "r") as f:
            definition = json.load(f)

        return definition

    def substitute_variables(
        self, definition: Dict[str, Any], variables: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Substitute variables in state machine definition.

        Replaces ${VariableName} placeholders with actual values.

        Args:
            definition: State machine definition
            variables: Variable name to value mapping

        Returns:
            Definition with substituted variables
        """
        # Convert to JSON string
        definition_str = json.dumps(definition)

        # Substitute each variable
        for var_name, var_value in variables.items():
            placeholder = f"${{{var_name}}}"
            definition_str = definition_str.replace(placeholder, var_value)

        # Convert back to dict
        return json.loads(definition_str)
