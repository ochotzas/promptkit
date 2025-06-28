PromptKit Documentation
=======================

A production-grade library for structured prompt engineering for LLMs. Define, validate, and execute LLM prompts using YAML files with input validation, engine abstraction, and CLI support.

Features
--------

- 📝 **YAML-based prompt definitions** with Jinja2 templating
- 🔍 **Input validation** using Pydantic schemas
- 🏗️ **Engine abstraction** supporting OpenAI and local models
- 💰 **Token estimation** and cost calculation
- 🖥️ **CLI interface** for quick prompt execution
- 🧪 **Fully tested** with comprehensive test suite

Quick Start
-----------

Install PromptKit:

.. code-block:: bash

   pip install promptkit-core

Define a prompt in YAML:

.. code-block:: yaml

   name: greet_user
   description: Basic greeting
   template: |
     Hello {{ name }}, how can I help you today?
   input_schema:
     name: str

Use in Python:

.. code-block:: python

   from promptkit.core.loader import load_prompt
   from promptkit.core.runner import run_prompt
   from promptkit.engines.openai import OpenAIEngine

   # Load prompt from YAML
   prompt = load_prompt("greet_user")

   # Configure engine
   engine = OpenAIEngine(api_key="sk-...")

   # Run prompt
   response = run_prompt(prompt, {"name": "Alice"}, engine)
   print(response)

Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   tutorials/quickstart
   tutorials/first-prompt

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   tutorials/advanced-templates
   tutorials/validation

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/basic
   examples/advanced

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/core
   api/engines
   api/cli

.. toctree::
   :maxdepth: 2
   :caption: Advanced Topics

   concepts

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
