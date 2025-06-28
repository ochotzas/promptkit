# Input Validation and Schema Management

Learn how to create robust prompts with comprehensive input validation using Pydantic schemas and PromptKit's validation features.

## Overview

PromptKit uses Pydantic for input validation, ensuring that your prompts receive the correct data types and formats. This guide covers everything from basic validation to advanced schema patterns.

## Basic Validation

### Simple Types
```yaml
name: basic_validation
description: Basic type validation
template: |
  Hello {{ name }}, you are {{ age }} years old.
  Your email is {{ email }}.
input_schema:
  name: str
  age: int
  email: str
```

### Optional Fields
```yaml
name: optional_fields
description: Validation with optional fields
template: |
  User: {{ username }}
  {% if full_name %}Full Name: {{ full_name }}{% endif %}
  {% if bio %}Bio: {{ bio }}{% endif %}
input_schema:
  username: str
  full_name:
    type: str
    required: false
  bio:
    type: str
    required: false
    default: "No bio provided"
```

## Advanced Type Validation

### Enum Validation
```yaml
name: enum_validation
description: Validation with enum constraints
template: |
  Processing {{ task_type }} task with {{ priority }} priority.
  Status: {{ status }}
input_schema:
  task_type:
    type: str
    enum: ["analysis", "generation", "summarization", "translation"]
  priority:
    type: str
    enum: ["low", "medium", "high", "critical"]
  status:
    type: str
    enum: ["pending", "in_progress", "completed", "failed"]
```

### Numeric Constraints
```yaml
name: numeric_constraints
description: Validation with numeric limits
template: |
  Generating {{ count }} items with quality score {{ quality_score }}.
  Budget: ${{ budget }}
input_schema:
  count:
    type: int
    minimum: 1
    maximum: 100
  quality_score:
    type: float
    minimum: 0.0
    maximum: 1.0
  budget:
    type: float
    minimum: 0
    maximum: 10000
```

### String Constraints
```yaml
name: string_constraints
description: Validation with string constraints
template: |
  Username: {{ username }}
  Password strength: {{ password_strength }}
  Description: {{ description }}
input_schema:
  username:
    type: str
    minLength: 3
    maxLength: 20
    pattern: "^[a-zA-Z0-9_]+$"
  password_strength:
    type: str
    enum: ["weak", "medium", "strong"]
  description:
    type: str
    maxLength: 500
```

## Complex Object Validation

### Nested Objects
```yaml
name: nested_objects
description: Validation with nested object structures
template: |
  User Profile:
  Name: {{ user.first_name }} {{ user.last_name }}
  Email: {{ user.contact.email }}
  Phone: {{ user.contact.phone }}

  Address:
  {{ user.address.street }}
  {{ user.address.city }}, {{ user.address.state }} {{ user.address.zip_code }}
input_schema:
  user:
    type: object
    properties:
      first_name: str
      last_name: str
      contact:
        type: object
        properties:
          email:
            type: str
            format: email
          phone:
            type: str
            pattern: "^\\+?[1-9]\\d{1,14}$"
      address:
        type: object
        properties:
          street: str
          city: str
          state: str
          zip_code:
            type: str
            pattern: "^\\d{5}(-\\d{4})?$"
        required: ["street", "city", "state", "zip_code"]
    required: ["first_name", "last_name", "contact", "address"]
```

### Array Validation
```yaml
name: array_validation
description: Validation for arrays and lists
template: |
  Processing {{ items|length }} items:
  {% for item in items %}
  - {{ item.name }}: {{ item.description }}
    Priority: {{ item.priority }}
    Tags: {{ item.tags|join(", ") }}
  {% endfor %}
input_schema:
  items:
    type: array
    minItems: 1
    maxItems: 10
    items:
      type: object
      properties:
        name:
          type: str
          minLength: 1
          maxLength: 100
        description:
          type: str
          maxLength: 500
        priority:
          type: int
          minimum: 1
          maximum: 5
        tags:
          type: array
          items: str
          maxItems: 5
      required: ["name", "description", "priority"]
```

## Date and Time Validation

```yaml
name: datetime_validation
description: Validation for dates and timestamps
template: |
  Event: {{ event_name }}
  Start: {{ start_date }}
  End: {{ end_date }}
  Duration: {{ duration_hours }} hours
  Created: {{ created_at }}
input_schema:
  event_name: str
  start_date:
    type: str
    format: date
    description: "Date in YYYY-MM-DD format"
  end_date:
    type: str
    format: date
    description: "Date in YYYY-MM-DD format"
  duration_hours:
    type: float
    minimum: 0.5
    maximum: 24
  created_at:
    type: str
    format: date-time
    description: "ISO 8601 datetime"
```

## Custom Validators

### Using Pydantic Models in Python

```python
from pydantic import BaseModel, validator, Field
from typing import List, Optional
from datetime import datetime

class ContactInfo(BaseModel):
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    phone: Optional[str] = Field(None, regex=r'^\+?[1-9]\d{1,14}$')

class User(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    age: int = Field(..., ge=13, le=120)
    contact: ContactInfo
    tags: List[str] = Field(default_factory=list, max_items=10)
    created_at: datetime = Field(default_factory=datetime.now)

    @validator('username')
    def username_alphanumeric(cls, v):
        assert v.isalnum(), 'Username must be alphanumeric'
        return v

    @validator('tags')
    def validate_tags(cls, v):
        if len(set(v)) != len(v):
            raise ValueError('Tags must be unique')
        return v

# Use with PromptKit
from promptkit.core.prompt import Prompt

prompt = Prompt(
    name="user_profile",
    template="Welcome {{ username }}! Your email is {{ contact.email }}",
    input_schema=User
)
```

## Conditional Validation

### Schema Variants
```yaml
name: conditional_validation
description: Different schemas based on input type
template: |
  {% if request_type == "user_creation" %}
  Creating user: {{ user_data.username }}
  Email: {{ user_data.email }}
  {% elif request_type == "user_update" %}
  Updating user {{ user_data.user_id }}:
  {% if user_data.new_email %}New email: {{ user_data.new_email }}{% endif %}
  {% if user_data.new_username %}New username: {{ user_data.new_username }}{% endif %}
  {% endif %}
input_schema:
  request_type:
    type: str
    enum: ["user_creation", "user_update"]
  user_data:
    oneOf:
      - # Schema for user creation
        type: object
        properties:
          username:
            type: str
            minLength: 3
            maxLength: 20
          email:
            type: str
            format: email
        required: ["username", "email"]
      - # Schema for user update
        type: object
        properties:
          user_id:
            type: int
            minimum: 1
          new_username:
            type: str
            minLength: 3
            maxLength: 20
          new_email:
            type: str
            format: email
        required: ["user_id"]
```

## Validation Error Handling

### Custom Error Messages
```python
from promptkit.core.exceptions import ValidationError
from promptkit.core.loader import load_prompt
from promptkit.core.runner import run_prompt

def run_with_validation(prompt_file, input_data, engine):
    try:
        prompt = load_prompt(prompt_file)
        return run_prompt(prompt, input_data, engine)
    except ValidationError as e:
        # Handle validation errors gracefully
        print(f"Validation failed: {e}")
        print("Please check your input data:")
        for error in e.errors():
            field = " -> ".join(str(x) for x in error['loc'])
            message = error['msg']
            print(f"  {field}: {message}")
        return None
```

### Validation in Templates
```yaml
name: template_validation
description: Runtime validation within templates
template: |
  {% if email and '@' not in email %}
  ERROR: Invalid email format
  {% elif age and (age < 0 or age > 150) %}
  ERROR: Invalid age
  {% else %}
  Processing request for {{ name }} ({{ age }}) at {{ email }}
  {% endif %}
input_schema:
  name: str
  age:
    type: int
    minimum: 0
    maximum: 150
  email:
    type: str
    format: email
```

## Schema Composition and Reuse

### Shared Schema Components
```yaml
# schemas/common.yaml
definitions:
  Address:
    type: object
    properties:
      street: str
      city: str
      state: str
      zip_code:
        type: str
        pattern: "^\\d{5}(-\\d{4})?$"
    required: ["street", "city", "state", "zip_code"]

  Contact:
    type: object
    properties:
      email:
        type: str
        format: email
      phone:
        type: str
        pattern: "^\\+?[1-9]\\d{1,14}$"
    required: ["email"]

# prompts/user_profile.yaml
name: user_profile
description: User profile with shared schemas
template: |
  User: {{ name }}
  Email: {{ contact.email }}
  Address: {{ address.street }}, {{ address.city }}
input_schema:
  name: str
  contact:
    $ref: "schemas/common.yaml#/definitions/Contact"
  address:
    $ref: "schemas/common.yaml#/definitions/Address"
```

## Testing Validation

### Unit Tests for Schemas
```python
import pytest
from pydantic import ValidationError
from promptkit.core.loader import load_prompt

def test_valid_input():
    prompt = load_prompt("user_profile.yaml")
    valid_data = {
        "name": "John Doe",
        "age": 30,
        "email": "john@example.com"
    }
    # This should not raise an exception
    validated = prompt.validate_input(valid_data)
    assert validated["name"] == "John Doe"

def test_invalid_email():
    prompt = load_prompt("user_profile.yaml")
    invalid_data = {
        "name": "John Doe",
        "age": 30,
        "email": "invalid-email"
    }
    with pytest.raises(ValidationError) as exc_info:
        prompt.validate_input(invalid_data)
    assert "email" in str(exc_info.value)

def test_missing_required_field():
    prompt = load_prompt("user_profile.yaml")
    incomplete_data = {
        "name": "John Doe"
        # Missing required 'age' and 'email'
    }
    with pytest.raises(ValidationError):
        prompt.validate_input(incomplete_data)
```

## Best Practices

1. **Start Simple**: Begin with basic validation and add complexity as needed
2. **Clear Error Messages**: Provide descriptive validation error messages
3. **Consistent Schemas**: Use consistent naming and structure across prompts
4. **Document Constraints**: Include descriptions for validation rules
5. **Test Edge Cases**: Test with boundary values and invalid inputs
6. **Reuse Components**: Create shared schema definitions for common patterns
7. **Validate Early**: Validate inputs before template rendering
8. **Handle Gracefully**: Provide meaningful feedback for validation failures

## Common Validation Patterns

### File Upload Validation
```yaml
name: file_validation
description: Validation for file upload scenarios
input_schema:
  filename:
    type: str
    pattern: "^[^<>:\"/\\|?*]+\\.(txt|pdf|doc|docx)$"
  file_size:
    type: int
    minimum: 1
    maximum: 10485760  # 10MB
  content_type:
    type: str
    enum: ["text/plain", "application/pdf", "application/msword"]
```

### API Configuration Validation
```yaml
name: api_config_validation
description: Validation for API configuration
input_schema:
  endpoint:
    type: str
    format: uri
  method:
    type: str
    enum: ["GET", "POST", "PUT", "DELETE"]
  headers:
    type: object
    additionalProperties:
      type: str
  timeout:
    type: int
    minimum: 1
    maximum: 300
```

This comprehensive guide covers all aspects of input validation in PromptKit, from basic types to complex schemas and custom validators.
