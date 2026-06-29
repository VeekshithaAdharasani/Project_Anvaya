# AGENTS.md

# Project ANVAYA

**Working Title:** From Memory to Understanding

Version: 1.0 (Architecture Locked)

Status: MVP Development

---

# Purpose

This document is the authoritative engineering specification for every AI assistant contributing to Project ANVAYA.

It defines:

- Project vision
- Architecture
- Design philosophy
- Coding standards
- Development workflow
- Current implementation status

Every AI assistant must read this document before generating code.

If generated code conflicts with this document, this document always takes priority.

---

# Executive Summary

Project ANVAYA is an understanding-driven multi-agent AI system.

Traditional conversational AI systems remember previous conversations.

ANVAYA goes beyond memory.

It continuously constructs an evolving Understanding Graph representing the user's goals, dreams, motivations, values, skills, interests, learning style, confidence, and personal growth.

Instead of answering:

"What happened?"

ANVAYA answers:

"Who is this person becoming?"

The project is being developed as a Google × Kaggle 5-Day AI Agents Intensive Capstone.

---

# Research Motivation

Current AI assistants suffer from several limitations:

- Conversation history grows indefinitely.
- Long context is expensive.
- Stored memories become outdated.
- Systems rarely distinguish temporary emotions from permanent changes.
- User understanding is implicit instead of explicit.

ANVAYA addresses these problems by introducing a dedicated Understanding Layer between Memory and Decision Making.

This layer continuously maintains an explicit Understanding Graph that evolves over time.

---

# Core Innovation

The primary innovation is NOT memory.

The primary innovation is the Understanding Layer.

Conversation

↓

Memory

↓

Understanding Layer

↓

Understanding Graph

↓

Specialized Agents

↓

Personalized Response

The Understanding Layer performs reasoning.

The Understanding Graph stores structured knowledge.

The graph itself never reasons.

---

# Design Philosophy

This project prioritizes:

- Simplicity
- Explainability
- Modularity
- Maintainability
- Readability
- Production-quality implementation
- Research-quality architecture

Avoid unnecessary abstractions.

Prefer clear code over clever code.

---

# Locked Architecture

The architecture is finalized.

Do NOT redesign it.

Overall pipeline:

User

↓

Conversation

↓

Memory Agent

↓

Understanding Agent

↓

Reflection Agent

↓

Understanding Graph

↓

Curiosity Agent

↓

Coordinator Agent

↓

Final Response

---

# Understanding Layer

The Understanding Layer is the cognitive engine.

Responsibilities:

- Extract understanding
- Update understanding
- Resolve contradictions
- Estimate confidence
- Manage evidence
- Validate changes
- Detect long-term patterns

No other module performs reasoning.

---

# Understanding Graph

The graph is a structured representation of user understanding.

It stores:

- Dreams
- Goals
- Skills
- Interests
- Motivations
- Values
- Learning Style
- Confidence

Each node stores:

- UUID
- Node Type
- Name
- Description
- Confidence
- Validation Status
- Evidence
- Created Timestamp
- Updated Timestamp

Relationships connect nodes.

The graph stores knowledge only.

The graph never performs reasoning.

---

# Agents

## Memory Agent

Responsibilities

- Store conversation history
- Retrieve relevant memories
- Provide context

---

## Understanding Agent

Responsibilities

- Analyze conversations
- Extract structured understanding
- Generate proposed graph updates

---

## Reflection Agent

Responsibilities

- Validate updates
- Detect contradictions
- Reject temporary emotional changes
- Update confidence

---

## Curiosity Agent

Responsibilities

- Detect uncertainty
- Find missing information
- Generate clarification questions

---

## Coordinator Agent

Responsibilities

- Coordinate all agents
- Merge outputs
- Produce final response

---

# Domain Model

The Domain layer contains only business objects.

Examples:

- Node
- Relationship
- Evidence
- UnderstandingGraph

Rules:

- Pure Python dataclasses
- No FastAPI imports
- No React imports
- No HTTP logic
- No Database logic
- No UI logic

---

# Services Layer

Responsible for:

- Gemini API
- Graph persistence
- SQLite
- File I/O
- External services

No business reasoning belongs here.

---

# API Layer

Responsible for:

- FastAPI
- HTTP endpoints
- Request validation
- Response validation

Pydantic belongs ONLY here.

---

# Frontend

Technology:

- React
- Vite
- React Flow

Responsibilities:

- Chat Interface
- Understanding Graph Visualization
- Evidence Display
- Confidence Display
- User Editing

Frontend never performs reasoning.

---

# Folder Structure

Code/

backend/

agents/

models/

services/

api/

utils/

frontend/

components/

pages/

hooks/

shared/

Research/

Implementation/

Evaluation/

Experiments/

Deployment/

Assets/

---

# Technology Stack

Backend

- Python 3.12
- FastAPI
- NetworkX
- SQLite
- Google Gemini API

Frontend

- React
- Vite
- React Flow

Development

- Git
- GitHub
- VS Code

---

# Coding Standards

Always:

- Use Python type hints
- Write meaningful docstrings
- Prefer composition over inheritance
- Keep functions small
- Keep classes focused
- Use descriptive variable names
- Validate inputs
- Remove dead code
- Remove duplicate logic
- Keep modules independent
- Follow SOLID where practical
- Produce production-quality code

---

# Never

Never:

- Redesign architecture
- Rename core models
- Modify unrelated modules
- Introduce unnecessary abstractions
- Introduce unnecessary dependencies
- Leak UI logic into backend
- Leak database logic into domain
- Generate placeholder implementations
- Skip validation
- Skip self-review

---

# Development Workflow

For every task:

1. Read AGENTS.md.
2. Explain implementation plan.
3. Modify ONE module only.
4. Generate production-ready code.
5. Explain important design decisions.
6. Perform self-review.
7. Stop and wait for approval.

Never implement multiple unrelated modules in one response.

---

# Current Progress

Completed

- Research
- Literature Review
- Project Design Document
- Overall Architecture
- Understanding Layer Design
- Understanding Graph Design
- Agent Design
- Tech Stack
- Folder Structure
- Enums
- Evidence Model
- Node Model
- Relationship Model

Current Module

- UnderstandingGraph

Upcoming Modules

- GraphService
- GeminiService
- Memory Agent
- Understanding Agent
- Reflection Agent
- Curiosity Agent
- Coordinator Agent
- FastAPI API
- React Frontend
- Evaluation
- Testing

---

# AI Assistant Instructions

Before generating any code:

1. Read this file completely.
2. Treat this file as the single source of truth.
3. Preserve the existing architecture.
4. Never redesign completed modules.
5. Explain implementation before coding.
6. Modify only one module.
7. Perform a self-review.
8. Wait for approval before continuing.

Your objective is not simply to generate code.

Your objective is to help build a production-quality research prototype of Project ANVAYA.

End of AGENTS.md