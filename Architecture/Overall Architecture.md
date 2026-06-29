# Overall Architecture

## Purpose

This document defines the high-level architecture of Project ANVAYA and describes how the major components interact. It serves as the bridge between the Project Design Document (PDD) and the implementation phase.

---

# System Overview

Project ANVAYA is an Understanding-Driven Multi-Agent AI Architecture.

Instead of allowing every AI agent to directly interact with conversation history, all agents collaborate through a centralized **Understanding Layer**.

The Understanding Layer continuously builds, updates, and maintains a structured understanding of the user.

This shared understanding enables every agent to make consistent and personalized decisions.

---

# High-Level Architecture

```
                     User
                       │
               Conversation/Input
                       │
               Coordinator Agent
                       │
      ┌────────────────┼────────────────┐
      │                │                │
 Memory Agent   Understanding Agent  Reflection Agent
      │                │                │
      └────────────────┼────────────────┘
                       │
               Understanding Layer
                       │
              Understanding Graph
                       │
      ┌─────────┬─────────┬─────────┐
      │         │         │         │
 Planner   Learning   Opportunity  Shield
   Agent      Agent      Agent      Agent
      │         │         │         │
      └─────────┴─────────┴─────────┘
                       │
              Personalized Response
```

---

# Component Overview

## User

Provides conversations, goals, feedback, and interactions.

---

## Coordinator Agent

Acts as the orchestrator.

It decides which specialized agents should participate for a particular request and combines their outputs into a final response.

---

## Memory Agent

Stores conversation history and important events.

Responsibilities include:

* Conversation history
* Important events
* Session context
* Previous interactions

Memory answers:

> What happened?

---

## Understanding Agent

Transforms memories and conversations into structured understanding.

Responsibilities include:

* Extract goals
* Detect motivations
* Identify interests
* Update confidence
* Build relationships between concepts

Understanding answers:

> What does this mean about the user?

---

## Reflection Agent

Validates major understanding updates before they become permanent.

Responsibilities include:

* Detect temporary emotions
* Detect contradictions
* Request clarification
* Prevent unstable updates

Reflection answers:

> Should the understanding change?

---

## Understanding Layer

Acts as the central reasoning layer.

Every specialized agent consults the Understanding Layer before making recommendations.

---

## Understanding Graph

Stores the structured understanding of the user.

Unlike conversation history, it represents relationships between goals, motivations, skills, values, confidence, and growth.

---

## Planner Agent

Creates personalized plans based on the current Understanding Graph.

---

## Learning Agent

Suggests learning resources aligned with the user's goals, skills, and learning style.

---

## Opportunity Agent

Identifies internships, scholarships, competitions, projects, jobs, and other relevant opportunities.

---

## Shield Agent

Ensures privacy, safety, transparency, and explainability throughout the system.

---

# Design Principles

1. Memory stores information.
2. Understanding interprets information.
3. Reflection validates understanding.
4. Curiosity improves understanding.
5. Every specialized agent relies on the Understanding Layer.
6. Users remain in control of their Understanding Graph.

---

# Out of Scope

This document does not describe:

* Internal agent prompts
* Database schema
* APIs
* Implementation details
* Deployment

These are covered in separate documents.

---

# Next Document

The next document is:

**Understanding Layer.md**

This document explains the core innovation of Project ANVAYA.
