# Advanced Examples

Comprehensive examples demonstrating sophisticated PromptKit usage patterns for real-world applications.

## Overview

This collection showcases advanced PromptKit implementations including multi-step workflows, complex data processing, integration patterns, and production-ready solutions.

## Multi-Step Workflow System

### Sequential Processing Pipeline
```yaml
# prompts/data_analysis_pipeline.yaml
name: data_analysis_pipeline
description: Multi-step data analysis workflow
template: |
  # Step {{ current_step }}: {{ step_name }}

  {% if current_step == 1 %}
  ## Data Validation
  Validating dataset with {{ data.rows|length }} rows and {{ data.columns|length }} columns.

  Columns: {{ data.columns|join(', ') }}
  Data types: {{ data.dtypes|join(', ') }}

  {% elif current_step == 2 %}
  ## Exploratory Analysis
  Previous validation: {{ previous_results.validation_status }}

  Performing exploratory analysis:
  - Statistical summary
  - Missing value analysis
  - Correlation analysis
  - Distribution analysis

  Focus areas: {{ analysis_focus|join(', ') }}

  {% elif current_step == 3 %}
  ## Insights Generation
  Based on previous analysis:
  {{ previous_results.summary }}

  Key findings:
  {% for finding in previous_results.key_findings %}
  - {{ finding }}
  {% endfor %}

  Generate actionable insights for: {{ business_context }}

  {% endif %}
input_schema:
  current_step:
    type: int
    minimum: 1
    maximum: 3
  step_name: str
  data:
    type: object
    properties:
      rows:
        type: array
        items: object
      columns:
        type: array
        items: str
      dtypes:
        type: array
        items: str
  previous_results:
    type: object
    properties:
      validation_status: str
      summary: str
      key_findings:
        type: array
        items: str
  analysis_focus:
    type: array
    items: str
  business_context: str
```

### Workflow Controller
```python
# workflow_controller.py
from promptkit.core.loader import load_prompt
from promptkit.core.runner import run_prompt
from promptkit.engines.openai import OpenAIEngine
from typing import Dict, Any, List
import json

class AnalysisWorkflow:
    def __init__(self, engine):
        self.engine = engine
        self.prompt = load_prompt("data_analysis_pipeline.yaml")
        self.results = {}

    def run_step(self, step: int, data: Dict[str, Any]) -> str:
        """Run a single step in the workflow"""
        step_data = {
            "current_step": step,
            "step_name": self._get_step_name(step),
            "data": data.get("data", {}),
            "previous_results": self.results.get("previous", {}),
            "analysis_focus": data.get("analysis_focus", []),
            "business_context": data.get("business_context", "")
        }

        result = run_prompt(self.prompt, step_data, self.engine)
        self.results[f"step_{step}"] = result

        return result

    def run_complete_workflow(self, initial_data: Dict[str, Any]) -> List[str]:
        """Run the complete workflow"""
        results = []

        for step in range(1, 4):
            # Update previous results for next step
            if step > 1:
                initial_data["previous_results"] = self._extract_results(step - 1)

            result = self.run_step(step, initial_data)
            results.append(result)

        return results

    def _get_step_name(self, step: int) -> str:
        names = {1: "Data Validation", 2: "Exploratory Analysis", 3: "Insights Generation"}
        return names.get(step, f"Step {step}")

    def _extract_results(self, step: int) -> Dict[str, Any]:
        """Extract structured results from previous step"""
        # This would parse the LLM response and extract structured data
        # Implementation depends on your specific needs
        return self.results.get(f"step_{step}", {})

# Usage
engine = OpenAIEngine(api_key="your-key")
workflow = AnalysisWorkflow(engine)

data = {
    "data": {
        "rows": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}],
        "columns": ["name", "age"],
        "dtypes": ["string", "integer"]
    },
    "analysis_focus": ["demographics", "trends"],
    "business_context": "customer segmentation"
}

results = workflow.run_complete_workflow(data)
```

## Content Generation System

### Dynamic Content Templates
```yaml
# prompts/content_generator.yaml
name: content_generator
description: Advanced content generation with multiple formats
template: |
  {% set content_types = {
    'blog_post': {
      'structure': ['introduction', 'main_points', 'conclusion'],
      'tone': 'informative and engaging',
      'length': 'long-form'
    },
    'social_media': {
      'structure': ['hook', 'value', 'call_to_action'],
      'tone': 'casual and conversational',
      'length': 'short-form'
    },
    'email': {
      'structure': ['subject', 'greeting', 'body', 'signature'],
      'tone': 'professional yet friendly',
      'length': 'medium-form'
    }
  } %}

  {% set config = content_types[content_type] %}

  # {{ content_type.title().replace('_', ' ') }} Content Generation

  **Target Audience**: {{ target_audience }}
  **Topic**: {{ topic }}
  **Tone**: {{ config.tone }}
  **Structure**: {{ config.structure|join(' → ') }}

  {% if content_type == 'blog_post' %}
  ## Blog Post Requirements
  - Word count: {{ word_count|default(800) }} words
  - SEO keywords: {{ seo_keywords|join(', ') }}
  - Include subheadings and bullet points
  - Add a compelling introduction and conclusion

  {% elif content_type == 'social_media' %}
  ## Social Media Requirements
  - Platform: {{ platform }}
  - Character limit: {{ char_limit|default(280) }}
  - Include relevant hashtags: {{ hashtags|join(' ') }}
  - Strong hook in first 5 words

  {% elif content_type == 'email' %}
  ## Email Requirements
  - Subject line must be under 50 characters
  - Personalization: {{ personalization|join(', ') }}
  - Clear call-to-action
  - Professional signature

  {% endif %}

  ## Content Guidelines
  {% for guideline in content_guidelines %}
  - {{ guideline }}
  {% endfor %}

  {% if brand_voice %}
  ## Brand Voice
  {{ brand_voice }}
  {% endif %}

  {% if examples %}
  ## Examples for Reference
  {% for example in examples %}
  ### {{ example.title }}
  {{ example.content }}

  {% endfor %}
  {% endif %}

  Please create {{ content_type.replace('_', ' ') }} content following these specifications.
input_schema:
  content_type:
    type: str
    enum: ["blog_post", "social_media", "email"]
  target_audience: str
  topic: str
  word_count:
    type: int
    minimum: 50
    maximum: 5000
  seo_keywords:
    type: array
    items: str
    maxItems: 10
  platform:
    type: str
    enum: ["twitter", "linkedin", "facebook", "instagram"]
  char_limit:
    type: int
    minimum: 50
    maximum: 500
  hashtags:
    type: array
    items: str
    maxItems: 10
  personalization:
    type: array
    items: str
  content_guidelines:
    type: array
    items: str
  brand_voice: str
  examples:
    type: array
    items:
      type: object
      properties:
        title: str
        content: str
      required: ["title", "content"]
```

## AI Assistant Integration

### Context-Aware Assistant
```yaml
# prompts/ai_assistant.yaml
name: ai_assistant
description: Context-aware AI assistant with memory and capabilities
template: |
  # AI Assistant Session

  ## Context
  **User**: {{ user.name }} ({{ user.role }})
  **Session ID**: {{ session.id }}
  **Conversation Turn**: {{ session.turn_count }}
  **Time**: {{ session.timestamp }}

  {% if user.preferences %}
  ## User Preferences
  {% for pref_key, pref_value in user.preferences.items() %}
  - {{ pref_key.replace('_', ' ').title() }}: {{ pref_value }}
  {% endfor %}
  {% endif %}

  {% if conversation_history %}
  ## Recent Conversation History
  {% for exchange in conversation_history[-3:] %}
  **{{ exchange.timestamp }}**
  User: {{ exchange.user_message }}
  Assistant: {{ exchange.assistant_response[:100] }}{% if exchange.assistant_response|length > 100 %}...{% endif %}

  {% endfor %}
  {% endif %}

  ## Available Capabilities
  {% for capability in available_capabilities %}
  - {{ capability.name }}: {{ capability.description }}
    {% if capability.parameters %}
    Required: {{ capability.parameters|join(', ') }}
    {% endif %}
  {% endfor %}

  ## Current Request
  **Type**: {{ request.type }}
  **Priority**: {{ request.priority }}
  **Content**: {{ request.content }}

  {% if request.context %}
  **Additional Context**: {{ request.context }}
  {% endif %}

  {% if request.files %}
  ## Attached Files
  {% for file in request.files %}
  - {{ file.name }} ({{ file.type }}, {{ file.size }})
  {% endfor %}
  {% endif %}

  ## Instructions
  1. Consider the user's preferences and conversation history
  2. Use appropriate capabilities for the request type
  3. Provide clear, actionable responses
  4. Ask for clarification if needed
  5. Maintain context throughout the conversation

  {% if request.type == "code_review" %}
  **Code Review Guidelines**:
  - Check for bugs and security issues
  - Suggest performance improvements
  - Verify coding standards compliance
  - Provide specific line-by-line feedback

  {% elif request.type == "data_analysis" %}
  **Data Analysis Guidelines**:
  - Identify patterns and trends
  - Highlight anomalies or outliers
  - Suggest visualizations
  - Provide statistical insights

  {% elif request.type == "creative_writing" %}
  **Creative Writing Guidelines**:
  - Match the requested tone and style
  - Ensure narrative consistency
  - Use vivid descriptions and dialogue
  - Follow genre conventions

  {% endif %}

  Please respond appropriately to the user's request.
input_schema:
  user:
    type: object
    properties:
      name: str
      role: str
      preferences:
        type: object
        additionalProperties: true
    required: ["name", "role"]
  session:
    type: object
    properties:
      id: str
      turn_count: int
      timestamp: str
    required: ["id", "turn_count", "timestamp"]
  conversation_history:
    type: array
    items:
      type: object
      properties:
        timestamp: str
        user_message: str
        assistant_response: str
      required: ["timestamp", "user_message", "assistant_response"]
  available_capabilities:
    type: array
    items:
      type: object
      properties:
        name: str
        description: str
        parameters:
          type: array
          items: str
      required: ["name", "description"]
  request:
    type: object
    properties:
      type:
        type: str
        enum: ["general", "code_review", "data_analysis", "creative_writing", "research", "planning"]
      priority:
        type: str
        enum: ["low", "medium", "high", "urgent"]
      content: str
      context: str
      files:
        type: array
        items:
          type: object
          properties:
            name: str
            type: str
            size: str
          required: ["name", "type", "size"]
    required: ["type", "priority", "content"]
```

## Testing and Quality Assurance

### Automated Testing Framework
```python
# testing/prompt_test_suite.py
import pytest
from promptkit.core.loader import load_prompt
from promptkit.core.runner import run_prompt
from promptkit.engines.mock import MockEngine
from typing import Dict, Any, List

class PromptTestSuite:
    def __init__(self, prompt_file: str):
        self.prompt = load_prompt(prompt_file)
        self.mock_engine = MockEngine()

    def test_input_validation(self, test_cases: List[Dict[str, Any]]):
        """Test input validation with various scenarios"""
        results = []

        for case in test_cases:
            try:
                validated = self.prompt.validate_input(case["input"])
                results.append({
                    "case": case["name"],
                    "status": "valid" if case["expected"] == "valid" else "unexpected_valid",
                    "data": validated
                })
            except Exception as e:
                results.append({
                    "case": case["name"],
                    "status": "invalid" if case["expected"] == "invalid" else "unexpected_invalid",
                    "error": str(e)
                })

        return results

    def test_template_rendering(self, test_cases: List[Dict[str, Any]]):
        """Test template rendering with mock responses"""
        results = []

        for case in test_cases:
            self.mock_engine.set_response(case.get("mock_response", "Test response"))

            try:
                result = run_prompt(self.prompt, case["input"], self.mock_engine)
                results.append({
                    "case": case["name"],
                    "status": "success",
                    "rendered_template": result,
                    "contains_expected": all(
                        expected in result
                        for expected in case.get("expected_content", [])
                    )
                })
            except Exception as e:
                results.append({
                    "case": case["name"],
                    "status": "error",
                    "error": str(e)
                })

        return results

    def performance_test(self, input_data: Dict[str, Any], iterations: int = 100):
        """Test prompt rendering performance"""
        import time

        times = []
        for _ in range(iterations):
            start = time.time()
            self.prompt.render_template(input_data)
            end = time.time()
            times.append(end - start)

        return {
            "iterations": iterations,
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "total_time": sum(times)
        }

# Usage Example
test_suite = PromptTestSuite("content_generator.yaml")

validation_tests = [
    {
        "name": "valid_blog_post",
        "input": {
            "content_type": "blog_post",
            "target_audience": "developers",
            "topic": "Python tips",
            "word_count": 800,
            "seo_keywords": ["python", "programming"]
        },
        "expected": "valid"
    },
    {
        "name": "invalid_content_type",
        "input": {
            "content_type": "invalid_type",
            "target_audience": "developers",
            "topic": "Python tips"
        },
        "expected": "invalid"
    }
]

validation_results = test_suite.test_input_validation(validation_tests)
print("Validation Test Results:", validation_results)
```

## Production Deployment

### Configuration Management
```yaml
# config/production.yaml
name: production_config
description: Production-ready configuration management
template: |
  # Production Configuration

  Environment: {{ environment }}
  Application: {{ app_name }}
  Version: {{ version }}

  ## Database Configuration
  {% if environment == "production" %}
  Database: {{ db_config.prod_host }}
  Pool Size: {{ db_config.prod_pool_size }}
  SSL: Required
  {% else %}
  Database: {{ db_config.dev_host }}
  Pool Size: {{ db_config.dev_pool_size }}
  SSL: Optional
  {% endif %}

  ## API Configuration
  {% for api in api_configs %}
  ### {{ api.name }}
  - Endpoint: {{ api.endpoint }}
  - Rate Limit: {{ api.rate_limit }} requests/minute
  - Timeout: {{ api.timeout }}s
  - Retry Attempts: {{ api.retry_attempts }}
  {% endfor %}

  ## Security Settings
  {% if security.encryption_enabled %}
  - Encryption: AES-256
  - Key Rotation: {{ security.key_rotation_days }} days
  {% endif %}
  - Authentication: {{ security.auth_method }}
  - Session Timeout: {{ security.session_timeout }} minutes

  ## Monitoring
  - Logging Level: {{ monitoring.log_level }}
  - Metrics Collection: {{ monitoring.metrics_enabled }}
  - Health Check Interval: {{ monitoring.health_check_interval }}s

  ## Feature Flags
  {% for feature, enabled in feature_flags.items() %}
  - {{ feature }}: {{ "Enabled" if enabled else "Disabled" }}
  {% endfor %}
input_schema:
  environment:
    type: str
    enum: ["development", "staging", "production"]
  app_name: str
  version: str
  db_config:
    type: object
    properties:
      prod_host: str
      prod_pool_size: int
      dev_host: str
      dev_pool_size: int
    required: ["prod_host", "prod_pool_size", "dev_host", "dev_pool_size"]
  api_configs:
    type: array
    items:
      type: object
      properties:
        name: str
        endpoint: str
        rate_limit: int
        timeout: int
        retry_attempts: int
      required: ["name", "endpoint", "rate_limit", "timeout", "retry_attempts"]
  security:
    type: object
    properties:
      encryption_enabled: bool
      key_rotation_days: int
      auth_method: str
      session_timeout: int
    required: ["encryption_enabled", "auth_method", "session_timeout"]
  monitoring:
    type: object
    properties:
      log_level:
        type: str
        enum: ["DEBUG", "INFO", "WARNING", "ERROR"]
      metrics_enabled: bool
      health_check_interval: int
    required: ["log_level", "metrics_enabled", "health_check_interval"]
  feature_flags:
    type: object
    additionalProperties: bool
```

These advanced examples demonstrate real-world applications of PromptKit, showing how to build complex, maintainable, and production-ready prompt-driven systems.
