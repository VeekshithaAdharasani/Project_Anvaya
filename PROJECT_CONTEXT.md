# PROJECT_CONTEXT.md

# Project Status

Project: ANVAYA

Status: MVP Development

Current Phase: Phase 1 – Core Domain Models

Architecture Status: Locked

---

# Current Objective

We are building an understanding-driven multi-agent AI system.

The goal of the current phase is to complete the backend domain layer before implementing agents and APIs.

We are implementing one module at a time.

No architectural redesigns are allowed unless explicitly requested.

---

# Architecture Decisions

The following decisions have already been finalized.

## Understanding Layer

The Understanding Layer is the reasoning engine.

It performs:

* understanding extraction
* reflection
* contradiction detection
* confidence updates
* evidence management

The Understanding Graph does not perform reasoning.

---

## Understanding Graph

The graph stores structured knowledge only.

It stores:

* Dreams
* Goals
* Skills
* Interests
* Motivations
* Values
* Learning Style
* Confidence

It is a passive storage model.

---

## Domain Models

Current domain models:

* Node
* Relationship
* Evidence
* UnderstandingGraph

Enums:

* NodeType
* RelationshipType
* ValidationStatus

Domain models are implemented using Python dataclasses.

---

# Completed Modules

Completed

* Research Documents
* Project Design Document
* Overall Architecture
* Understanding Layer
* Understanding Graph Design
* Folder Structure
* NodeType Enum
* RelationshipType Enum
* ValidationStatus Enum
* Evidence Model
* Node Model
* Relationship Model

---

# Current Module

UnderstandingGraph

This module is currently under implementation and review.

---

# Next Modules

After UnderstandingGraph:

1. GraphService

2. GeminiService

3. Memory Agent

4. Understanding Agent

5. Reflection Agent

6. Curiosity Agent

7. Coordinator Agent

8. FastAPI

9. React Frontend

---

# Important Decisions

These decisions are final unless explicitly changed.

* The architecture is locked.

* Modify only one module at a time.

* No placeholder implementations.

* No unnecessary abstractions.

* Business reasoning belongs only to the Understanding Layer.

* Domain models remain independent of FastAPI and React.

* Pydantic belongs only in the API layer.

* React Flow belongs only in the frontend.

---

# Current Folder Structure

Code/

backend/

agents/

models/

services/

api/

utils/

frontend/

shared/

Research/

Implementation/

Evaluation/

Deployment/

Experiments/

Assets/

---

# Working Rules

For every implementation:

1. Read AGENTS.md first.

2. Read PROJECT_CONTEXT.md.

3. Explain implementation.

4. Modify only one module.

5. Produce production-quality code.

6. Perform a self-review.

7. Stop after completing the requested module.

---

# Current Task

Complete the UnderstandingGraph implementation.

Wait for approval before moving to GraphService.

End of PROJECT_CONTEXT.md
