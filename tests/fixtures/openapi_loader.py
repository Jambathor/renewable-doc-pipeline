"""
OpenAPI specification loader and validation fixtures for renewable energy pipeline tests.

Provides fixtures for loading and validating API responses against the OpenAPI schema,
ensuring contract compliance and consistent API behavior.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
import yaml
from jsonschema import Draft7Validator, ValidationError
from jsonschema.validators import RefResolver


@pytest.fixture(scope="session")
def openapi_spec_path() -> Path:
    """Path to the OpenAPI specification file."""
    project_root = Path(__file__).parent.parent.parent
    spec_path = project_root / "specs" / "001-we-re-building" / "contracts" / "openapi.yaml"

    if not spec_path.exists():
        pytest.fail(f"OpenAPI specification not found at {spec_path}")

    return spec_path


@pytest.fixture(scope="session")
def openapi_spec(openapi_spec_path: Path) -> dict[str, Any]:
    """Loaded OpenAPI specification as dictionary."""
    try:
        with open(openapi_spec_path, encoding="utf-8") as f:
            spec = yaml.safe_load(f)

        # Validate basic OpenAPI structure
        required_fields = ["openapi", "info", "paths", "components"]
        for field in required_fields:
            if field not in spec:
                pytest.fail(f"OpenAPI spec missing required field: {field}")

        return spec

    except Exception as e:
        pytest.fail(f"Failed to load OpenAPI specification: {e}")


@pytest.fixture(scope="session")
def openapi_schemas(openapi_spec: dict[str, Any]) -> dict[str, Any]:
    """Extract component schemas from OpenAPI specification."""
    return openapi_spec.get("components", {}).get("schemas", {})


@pytest.fixture(scope="session")
def openapi_paths(openapi_spec: dict[str, Any]) -> dict[str, Any]:
    """Extract path definitions from OpenAPI specification."""
    return openapi_spec.get("paths", {})


class OpenAPIValidator:
    """Validator for OpenAPI schema compliance."""

    def __init__(self, spec: dict[str, Any]):
        self.spec = spec
        self.schemas = spec.get("components", {}).get("schemas", {})
        self.paths = spec.get("paths", {})

        # Create resolver for $ref resolution
        self.resolver = RefResolver(
            base_uri="",
            referrer=spec,
        )

    def get_schema(self, schema_name: str) -> dict[str, Any]:
        """Get a component schema by name."""
        if schema_name not in self.schemas:
            raise ValueError(f"Schema '{schema_name}' not found in OpenAPI spec")
        return self.schemas[schema_name]

    def get_response_schema(self, path: str, method: str, status_code: str) -> dict[str, Any]:
        """Get response schema for a specific endpoint and status code."""
        if path not in self.paths:
            raise ValueError(f"Path '{path}' not found in OpenAPI spec")

        path_spec = self.paths[path]
        if method.lower() not in path_spec:
            raise ValueError(f"Method '{method}' not found for path '{path}'")

        method_spec = path_spec[method.lower()]
        responses = method_spec.get("responses", {})

        if status_code not in responses:
            raise ValueError(f"Status code '{status_code}' not found for {method} {path}")

        response_spec = responses[status_code]
        content = response_spec.get("content", {})

        # Try to find JSON response schema
        json_content = content.get("application/json", {})
        if "schema" not in json_content:
            raise ValueError(f"No JSON schema found for {method} {path} {status_code}")

        return json_content["schema"]

    def validate_response(self, data: Any, path: str, method: str, status_code: str) -> None:
        """Validate response data against OpenAPI schema."""
        try:
            schema = self.get_response_schema(path, method, status_code)

            # Resolve any $ref references in the schema if needed
            if "$ref" in str(schema):
                url, resolved = self.resolver.resolve(schema.get("$ref", ""))
                schema = resolved

            # Create validator and validate
            validator = Draft7Validator(schema, resolver=self.resolver)
            validator.validate(data)

        except ValidationError as e:
            pytest.fail(f"Response validation failed for {method} {path} {status_code}: {e}")
        except Exception as e:
            pytest.fail(f"Error validating response: {e}")

    def validate_schema_data(self, data: Any, schema_name: str) -> None:
        """Validate data against a named component schema."""
        try:
            schema = self.get_schema(schema_name)

            # Create validator with proper resolver
            validator = Draft7Validator(schema, resolver=self.resolver)
            validator.validate(data)

        except ValidationError as e:
            pytest.fail(f"Schema validation failed for '{schema_name}': {e}")
        except Exception as e:
            pytest.fail(f"Error validating schema: {e}")

    def validate_request_body(self, data: Any, path: str, method: str) -> None:
        """Validate request body data against OpenAPI schema."""
        try:
            if path not in self.paths:
                raise ValueError(f"Path '{path}' not found in OpenAPI spec")

            path_spec = self.paths[path]
            if method.lower() not in path_spec:
                raise ValueError(f"Method '{method}' not found for path '{path}'")

            method_spec = path_spec[method.lower()]
            request_body = method_spec.get("requestBody", {})

            if not request_body:
                pytest.fail(f"No request body schema found for {method} {path}")

            content = request_body.get("content", {})
            json_content = content.get("application/json", {})

            if "schema" not in json_content:
                pytest.fail(f"No JSON schema found for request body {method} {path}")

            schema = json_content["schema"]
            schema = self.resolver.resolve_fragment(schema, "")[1]

            validator = Draft7Validator(schema, resolver=self.resolver)
            validator.validate(data)

        except ValidationError as e:
            pytest.fail(f"Request body validation failed for {method} {path}: {e}")
        except Exception as e:
            pytest.fail(f"Error validating request body: {e}")

    def get_example_data(self, schema_name: str) -> Any:
        """Generate example data from schema (basic implementation)."""
        schema = self.get_schema(schema_name)
        return self._generate_example_from_schema(schema)

    def _generate_example_from_schema(self, schema: dict[str, Any]) -> Any:
        """Generate example data from a schema definition."""
        schema_type = schema.get("type")

        if schema_type == "object":
            example = {}
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            for prop_name, prop_schema in properties.items():
                if prop_name in required:
                    example[prop_name] = self._generate_example_from_schema(prop_schema)

            return example

        elif schema_type == "array":
            items_schema = schema.get("items", {})
            return [self._generate_example_from_schema(items_schema)]

        elif schema_type == "string":
            format_type = schema.get("format")
            if format_type == "uuid":
                return "550e8400-e29b-41d4-a716-446655440000"
            elif format_type == "date-time":
                return "2024-01-15T10:30:00Z"
            elif format_type == "date":
                return "2024-01-15"
            else:
                return schema.get("example", "example string")

        elif schema_type == "integer":
            return schema.get("example", 42)

        elif schema_type == "number":
            return schema.get("example", 3.14)

        elif schema_type == "boolean":
            return schema.get("example", True)

        else:
            return None


@pytest.fixture
def openapi_validator(openapi_spec: dict[str, Any]) -> OpenAPIValidator:
    """OpenAPI validator instance for schema validation."""
    return OpenAPIValidator(openapi_spec)


@pytest.fixture
def response_validator(openapi_validator: OpenAPIValidator):
    """Helper function for validating API responses."""
    def validate(response_data: Any, path: str, method: str, status_code: str) -> None:
        """Validate response data against OpenAPI schema."""
        openapi_validator.validate_response(response_data, path, method, status_code)

    return validate


@pytest.fixture
def schema_validator(openapi_validator: OpenAPIValidator):
    """Helper function for validating data against component schemas."""
    def validate(data: Any, schema_name: str) -> None:
        """Validate data against named schema."""
        openapi_validator.validate_schema_data(data, schema_name)

    return validate


@pytest.fixture
def request_validator(openapi_validator: OpenAPIValidator):
    """Helper function for validating request bodies."""
    def validate(request_data: Any, path: str, method: str) -> None:
        """Validate request body data against OpenAPI schema."""
        openapi_validator.validate_request_body(request_data, path, method)

    return validate


# Specific schema fixtures for common use cases

@pytest.fixture
def document_upload_schema(openapi_validator: OpenAPIValidator) -> dict[str, Any]:
    """DocumentUploadResponse schema."""
    return openapi_validator.get_schema("DocumentUploadResponse")


@pytest.fixture
def job_status_schema(openapi_validator: OpenAPIValidator) -> dict[str, Any]:
    """JobStatusResponse schema."""
    return openapi_validator.get_schema("JobStatusResponse")


@pytest.fixture
def search_response_schema(openapi_validator: OpenAPIValidator) -> dict[str, Any]:
    """SearchResponse schema."""
    return openapi_validator.get_schema("SearchResponse")


@pytest.fixture
def question_response_schema(openapi_validator: OpenAPIValidator) -> dict[str, Any]:
    """QuestionResponse schema."""
    return openapi_validator.get_schema("QuestionResponse")


@pytest.fixture
def error_response_schema(openapi_validator: OpenAPIValidator) -> dict[str, Any]:
    """ErrorResponse schema."""
    return openapi_validator.get_schema("ErrorResponse")


@pytest.fixture
def health_response_schema(openapi_validator: OpenAPIValidator) -> dict[str, Any]:
    """HealthResponse schema."""
    return openapi_validator.get_schema("HealthResponse")


# Contract testing helpers

def validate_endpoint_contract(
    response_data: Any,
    path: str,
    method: str,
    status_code: int,
    validator: OpenAPIValidator,
) -> None:
    """Validate that an endpoint response matches its OpenAPI contract."""
    status_str = str(status_code)

    try:
        validator.validate_response(response_data, path, method, status_str)
    except Exception as e:
        pytest.fail(f"Contract validation failed for {method} {path} {status_code}: {e}")


def assert_schema_compliance(data: Any, schema_name: str, validator: OpenAPIValidator) -> None:
    """Assert that data complies with a named schema."""
    try:
        validator.validate_schema_data(data, schema_name)
    except Exception as e:
        pytest.fail(f"Schema compliance failed for '{schema_name}': {e}")


@pytest.fixture
def contract_tester(openapi_validator: OpenAPIValidator):
    """Helper for running contract tests."""
    def test_contract(response_data: Any, path: str, method: str, status_code: int) -> None:
        """Test endpoint contract compliance."""
        validate_endpoint_contract(response_data, path, method, status_code, openapi_validator)

    return test_contract
