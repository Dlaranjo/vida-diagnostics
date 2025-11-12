"""
Unit tests for Step Functions handler.

Tests Step Functions workflow orchestration with mocked AWS services.
"""

import json

import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from src.orchestration.step_functions import StepFunctionsHandler


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def step_functions_handler(aws_credentials):
    """Create StepFunctionsHandler with mocked AWS."""
    with mock_aws():
        handler = StepFunctionsHandler(region_name="us-east-1")
        yield handler


@pytest.fixture
def state_machine_definition():
    """Create minimal state machine definition."""
    return {
        "Comment": "Test state machine",
        "StartAt": "TestState",
        "States": {
            "TestState": {
                "Type": "Pass",
                "Result": "Hello World",
                "End": True,
            }
        },
    }


@pytest.fixture
def role_arn():
    """Mock IAM role ARN."""
    return "arn:aws:iam::123456789012:role/StepFunctionsRole"


class TestStepFunctionsHandlerInitialization:
    """Test Step Functions handler initialization."""

    def test_init_with_default_credentials(self, aws_credentials):
        """Test initialization with default credentials."""
        with mock_aws():
            handler = StepFunctionsHandler(region_name="us-east-1")
            assert handler.region_name == "us-east-1"
            assert handler.sfn_client is not None

    def test_init_with_custom_credentials(self, aws_credentials):
        """Test initialization with custom credentials."""
        with mock_aws():
            handler = StepFunctionsHandler(
                region_name="us-west-2",
                aws_access_key_id="custom_key",
                aws_secret_access_key="custom_secret",
            )
            assert handler.region_name == "us-west-2"
            assert handler.sfn_client is not None


class TestStateMachineCreation:
    """Test state machine creation."""

    def test_create_state_machine_success(
        self, step_functions_handler, state_machine_definition, role_arn
    ):
        """Test successful state machine creation."""
        result = step_functions_handler.create_state_machine(
            name="test-state-machine",
            definition=state_machine_definition,
            role_arn=role_arn,
        )

        assert "state_machine_arn" in result
        assert "creation_date" in result
        assert "test-state-machine" in result["state_machine_arn"]

    def test_create_state_machine_with_logging(
        self, step_functions_handler, state_machine_definition, role_arn
    ):
        """Test state machine creation with logging configuration."""
        logging_config = {
            "level": "ALL",
            "includeExecutionData": True,
            "destinations": [
                {
                    "cloudWatchLogsLogGroup": {
                        "logGroupArn": (
                            "arn:aws:logs:us-east-1:123456789012:"
                            "log-group:/aws/stepfunctions/test"
                        )
                    }
                }
            ],
        }

        result = step_functions_handler.create_state_machine(
            name="test-state-machine-with-logging",
            definition=state_machine_definition,
            role_arn=role_arn,
            logging_config=logging_config,
        )

        assert "state_machine_arn" in result

    def test_create_state_machine_with_tags(
        self, step_functions_handler, state_machine_definition, role_arn
    ):
        """Test state machine creation with tags."""
        tags = [
            {"key": "Environment", "value": "Test"},
            {"key": "Project", "value": "DICOM"},
        ]

        result = step_functions_handler.create_state_machine(
            name="test-state-machine-with-tags",
            definition=state_machine_definition,
            role_arn=role_arn,
            tags=tags,
        )

        assert "state_machine_arn" in result

    def test_create_state_machine_with_string_definition(
        self, step_functions_handler, state_machine_definition, role_arn
    ):
        """Test state machine creation with string definition."""
        definition_str = json.dumps(state_machine_definition)

        result = step_functions_handler.create_state_machine(
            name="test-state-machine-string-def",
            definition=definition_str,
            role_arn=role_arn,
        )

        assert "state_machine_arn" in result

    def test_create_state_machine_failure(
        self, step_functions_handler, state_machine_definition, monkeypatch
    ):
        """Test state machine creation failure."""

        def mock_create_state_machine(*args, **kwargs):
            error_response = {
                "Error": {"Code": "InvalidDefinition", "Message": "Invalid definition"}
            }
            raise ClientError(error_response, "CreateStateMachine")

        monkeypatch.setattr(
            step_functions_handler.sfn_client,
            "create_state_machine",
            mock_create_state_machine,
        )

        with pytest.raises(ClientError):
            step_functions_handler.create_state_machine(
                name="test-failing-state-machine",
                definition=state_machine_definition,
                role_arn="arn:aws:iam::123456789012:role/TestRole",
            )


class TestExecutionManagement:
    """Test execution management."""

    def test_start_execution_success(
        self, step_functions_handler, state_machine_definition, role_arn
    ):
        """Test starting execution successfully."""
        # Create state machine first
        create_result = step_functions_handler.create_state_machine(
            name="test-state-machine-exec",
            definition=state_machine_definition,
            role_arn=role_arn,
        )
        state_machine_arn = create_result["state_machine_arn"]

        # Start execution
        execution_input = {"key": "value", "number": 123}
        result = step_functions_handler.start_execution(
            state_machine_arn=state_machine_arn,
            execution_input=execution_input,
        )

        assert "execution_arn" in result
        assert "start_date" in result

    def test_start_execution_with_name(
        self, step_functions_handler, state_machine_definition, role_arn
    ):
        """Test starting execution with custom name."""
        create_result = step_functions_handler.create_state_machine(
            name="test-state-machine-named-exec",
            definition=state_machine_definition,
            role_arn=role_arn,
        )
        state_machine_arn = create_result["state_machine_arn"]

        result = step_functions_handler.start_execution(
            state_machine_arn=state_machine_arn,
            execution_input={"test": "data"},
            execution_name="test-execution-001",
        )

        assert "execution_arn" in result
        assert "test-execution-001" in result["execution_arn"]

    def test_start_execution_failure(self, step_functions_handler, monkeypatch):
        """Test execution start failure."""

        def mock_start_execution(*args, **kwargs):
            error_response = {
                "Error": {
                    "Code": "StateMachineDoesNotExist",
                    "Message": "State machine does not exist",
                }
            }
            raise ClientError(error_response, "StartExecution")

        monkeypatch.setattr(
            step_functions_handler.sfn_client,
            "start_execution",
            mock_start_execution,
        )

        with pytest.raises(ClientError):
            step_functions_handler.start_execution(
                state_machine_arn="arn:aws:states:us-east-1:123456789012:stateMachine:NonExistent",
                execution_input={},
            )

    def test_describe_execution_success(
        self, step_functions_handler, state_machine_definition, role_arn
    ):
        """Test describing execution."""
        create_result = step_functions_handler.create_state_machine(
            name="test-state-machine-describe",
            definition=state_machine_definition,
            role_arn=role_arn,
        )
        state_machine_arn = create_result["state_machine_arn"]

        start_result = step_functions_handler.start_execution(
            state_machine_arn=state_machine_arn,
            execution_input={"test": "data"},
        )
        execution_arn = start_result["execution_arn"]

        result = step_functions_handler.describe_execution(execution_arn=execution_arn)

        assert result["execution_arn"] == execution_arn
        assert result["state_machine_arn"] == state_machine_arn
        assert "status" in result
        assert "start_date" in result
        assert "input" in result

    def test_describe_execution_failure(self, step_functions_handler, monkeypatch):
        """Test describe execution failure."""

        def mock_describe_execution(*args, **kwargs):
            error_response = {
                "Error": {
                    "Code": "ExecutionDoesNotExist",
                    "Message": "Execution does not exist",
                }
            }
            raise ClientError(error_response, "DescribeExecution")

        monkeypatch.setattr(
            step_functions_handler.sfn_client,
            "describe_execution",
            mock_describe_execution,
        )

        with pytest.raises(ClientError):
            step_functions_handler.describe_execution(
                execution_arn="arn:aws:states:us-east-1:123456789012:execution:test:nonexistent"
            )

    def test_list_executions_success(
        self, step_functions_handler, state_machine_definition, role_arn
    ):
        """Test listing executions."""
        create_result = step_functions_handler.create_state_machine(
            name="test-state-machine-list",
            definition=state_machine_definition,
            role_arn=role_arn,
        )
        state_machine_arn = create_result["state_machine_arn"]

        # Start multiple executions
        for i in range(3):
            step_functions_handler.start_execution(
                state_machine_arn=state_machine_arn,
                execution_input={"index": i},
            )

        result = step_functions_handler.list_executions(state_machine_arn=state_machine_arn)

        assert isinstance(result, list)
        assert len(result) == 3
        for execution in result:
            assert "execution_arn" in execution
            assert "status" in execution

    def test_list_executions_with_filter(
        self, step_functions_handler, state_machine_definition, role_arn
    ):
        """Test listing executions with status filter."""
        create_result = step_functions_handler.create_state_machine(
            name="test-state-machine-list-filter",
            definition=state_machine_definition,
            role_arn=role_arn,
        )
        state_machine_arn = create_result["state_machine_arn"]

        step_functions_handler.start_execution(
            state_machine_arn=state_machine_arn,
            execution_input={"test": "data"},
        )

        result = step_functions_handler.list_executions(
            state_machine_arn=state_machine_arn,
            status_filter="RUNNING",
        )

        assert isinstance(result, list)

    def test_list_executions_failure(self, step_functions_handler, monkeypatch):
        """Test list executions failure."""

        def mock_list_executions(*args, **kwargs):
            error_response = {
                "Error": {
                    "Code": "InvalidArn",
                    "Message": "Invalid state machine ARN",
                }
            }
            raise ClientError(error_response, "ListExecutions")

        monkeypatch.setattr(
            step_functions_handler.sfn_client,
            "list_executions",
            mock_list_executions,
        )

        with pytest.raises(ClientError):
            step_functions_handler.list_executions(state_machine_arn="invalid-arn")

    def test_stop_execution_success(
        self, step_functions_handler, state_machine_definition, role_arn
    ):
        """Test stopping execution."""
        create_result = step_functions_handler.create_state_machine(
            name="test-state-machine-stop",
            definition=state_machine_definition,
            role_arn=role_arn,
        )
        state_machine_arn = create_result["state_machine_arn"]

        start_result = step_functions_handler.start_execution(
            state_machine_arn=state_machine_arn,
            execution_input={"test": "data"},
        )
        execution_arn = start_result["execution_arn"]

        result = step_functions_handler.stop_execution(
            execution_arn=execution_arn,
            error="TestError",
            cause="Test stop",
        )

        assert "stop_date" in result

    def test_stop_execution_failure(self, step_functions_handler, monkeypatch):
        """Test stop execution failure."""

        def mock_stop_execution(*args, **kwargs):
            error_response = {
                "Error": {
                    "Code": "ExecutionDoesNotExist",
                    "Message": "Execution does not exist",
                }
            }
            raise ClientError(error_response, "StopExecution")

        monkeypatch.setattr(
            step_functions_handler.sfn_client,
            "stop_execution",
            mock_stop_execution,
        )

        with pytest.raises(ClientError):
            step_functions_handler.stop_execution(
                execution_arn="arn:aws:states:us-east-1:123456789012:execution:test:nonexistent"
            )


class TestStateMachineManagement:
    """Test state machine management operations."""

    def test_describe_state_machine_success(
        self, step_functions_handler, state_machine_definition, role_arn
    ):
        """Test describing state machine."""
        create_result = step_functions_handler.create_state_machine(
            name="test-state-machine-describe-sm",
            definition=state_machine_definition,
            role_arn=role_arn,
        )
        state_machine_arn = create_result["state_machine_arn"]

        result = step_functions_handler.describe_state_machine(state_machine_arn=state_machine_arn)

        assert result["state_machine_arn"] == state_machine_arn
        assert result["name"] == "test-state-machine-describe-sm"
        assert "definition" in result
        assert result["role_arn"] == role_arn

    def test_describe_state_machine_failure(self, step_functions_handler, monkeypatch):
        """Test describe state machine failure."""

        def mock_describe_state_machine(*args, **kwargs):
            error_response = {
                "Error": {
                    "Code": "StateMachineDoesNotExist",
                    "Message": "State machine does not exist",
                }
            }
            raise ClientError(error_response, "DescribeStateMachine")

        monkeypatch.setattr(
            step_functions_handler.sfn_client,
            "describe_state_machine",
            mock_describe_state_machine,
        )

        with pytest.raises(ClientError):
            step_functions_handler.describe_state_machine(
                state_machine_arn="arn:aws:states:us-east-1:123456789012:stateMachine:nonexistent"
            )

    def test_delete_state_machine_success(
        self, step_functions_handler, state_machine_definition, role_arn
    ):
        """Test deleting state machine."""
        create_result = step_functions_handler.create_state_machine(
            name="test-state-machine-delete",
            definition=state_machine_definition,
            role_arn=role_arn,
        )
        state_machine_arn = create_result["state_machine_arn"]

        result = step_functions_handler.delete_state_machine(state_machine_arn=state_machine_arn)

        assert result is True

    def test_delete_state_machine_failure(self, step_functions_handler, monkeypatch):
        """Test delete state machine failure."""

        def mock_delete_state_machine(*args, **kwargs):
            error_response = {
                "Error": {
                    "Code": "StateMachineDoesNotExist",
                    "Message": "State machine does not exist",
                }
            }
            raise ClientError(error_response, "DeleteStateMachine")

        monkeypatch.setattr(
            step_functions_handler.sfn_client,
            "delete_state_machine",
            mock_delete_state_machine,
        )

        with pytest.raises(ClientError):
            step_functions_handler.delete_state_machine(
                state_machine_arn="arn:aws:states:us-east-1:123456789012:stateMachine:nonexistent"
            )


class TestStateMachineDefinitionHelpers:
    """Test helper methods for state machine definitions."""

    def test_load_state_machine_definition_success(self, tmp_path):
        """Test loading state machine definition from file."""
        definition = {
            "Comment": "Test",
            "StartAt": "Hello",
            "States": {"Hello": {"Type": "Pass", "End": True}},
        }

        # Write definition to temp file
        definition_file = tmp_path / "test_definition.json"
        with open(definition_file, "w") as f:
            json.dump(definition, f)

        result = StepFunctionsHandler.load_state_machine_definition(str(definition_file))

        assert result == definition

    def test_load_state_machine_definition_file_not_found(self):
        """Test loading non-existent definition file."""
        with pytest.raises(FileNotFoundError):
            StepFunctionsHandler.load_state_machine_definition("/nonexistent/path/definition.json")

    def test_load_state_machine_definition_invalid_json(self, tmp_path):
        """Test loading invalid JSON definition."""
        invalid_file = tmp_path / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            StepFunctionsHandler.load_state_machine_definition(str(invalid_file))

    def test_substitute_variables_success(self, step_functions_handler):
        """Test substituting variables in definition."""
        definition = {
            "Comment": "Test with ${Environment}",
            "States": {
                "TestState": {
                    "Type": "Task",
                    "Resource": "${LambdaArn}",
                    "Parameters": {"Bucket": "${S3Bucket}"},
                    "End": True,
                }
            },
        }

        variables = {
            "Environment": "Production",
            "LambdaArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "S3Bucket": "my-bucket",
        }

        result = step_functions_handler.substitute_variables(definition, variables)

        assert result["Comment"] == "Test with Production"
        assert (
            result["States"]["TestState"]["Resource"]
            == "arn:aws:lambda:us-east-1:123456789012:function:test"
        )
        assert result["States"]["TestState"]["Parameters"]["Bucket"] == "my-bucket"

    def test_substitute_variables_partial(self, step_functions_handler):
        """Test substituting some variables."""
        definition = {
            "Comment": "${Env1} and ${Env2}",
            "States": {"Test": {"Type": "Pass", "End": True}},
        }

        variables = {"Env1": "Value1"}

        result = step_functions_handler.substitute_variables(definition, variables)

        assert result["Comment"] == "Value1 and ${Env2}"


class TestIntegration:
    """Integration tests for Step Functions workflow."""

    def test_full_workflow_lifecycle(
        self, step_functions_handler, state_machine_definition, role_arn
    ):
        """Test complete workflow lifecycle."""
        # Create state machine
        create_result = step_functions_handler.create_state_machine(
            name="test-full-lifecycle",
            definition=state_machine_definition,
            role_arn=role_arn,
        )
        state_machine_arn = create_result["state_machine_arn"]

        # Describe state machine
        describe_result = step_functions_handler.describe_state_machine(
            state_machine_arn=state_machine_arn
        )
        assert describe_result["name"] == "test-full-lifecycle"

        # Start execution
        start_result = step_functions_handler.start_execution(
            state_machine_arn=state_machine_arn,
            execution_input={"test": "data"},
        )
        execution_arn = start_result["execution_arn"]

        # Describe execution
        exec_describe = step_functions_handler.describe_execution(execution_arn=execution_arn)
        assert exec_describe["execution_arn"] == execution_arn

        # List executions
        executions = step_functions_handler.list_executions(state_machine_arn=state_machine_arn)
        assert len(executions) >= 1

        # Delete state machine
        delete_result = step_functions_handler.delete_state_machine(
            state_machine_arn=state_machine_arn
        )
        assert delete_result is True
