# Understanding Graph

## Purpose

The Understanding Graph is the core knowledge representation used by Project ANVAYA.

Instead of storing isolated facts, it organizes a user's evolving journey as interconnected entities with relationships, evidence, and confidence scores.

It acts as the shared source of understanding for all AI agents.

---

# What is the Understanding Graph?

The Understanding Graph is a dynamic knowledge graph that represents what the AI currently understands about a user.

Unlike conversation history, which stores events in chronological order, the Understanding Graph stores meaningful concepts and the relationships between them.

The graph evolves over time through conversations, user feedback, reflection, and validation.

---

# Objectives

The Understanding Graph is designed to:

* Represent long-term user understanding.
* Connect related concepts rather than storing isolated facts.
* Preserve evidence for every important inference.
* Track confidence for each understanding.
* Support multiple AI agents with a shared understanding.
* Allow users to inspect and correct AI understanding.

---

# Graph Components

The Understanding Graph consists of four primary elements:

## 1. Nodes

Nodes represent concepts about the user.

Examples include:

* Dream
* Goal
* Skill
* Interest
* Motivation
* Value
* Learning Style
* Decision Style
* Confidence
* Milestone

---

## 2. Relationships

Relationships connect nodes.

Examples:

Dream → motivates → Goal

Goal → requires → Skill

Skill → improves → Confidence

Interest → supports → Goal

Value → influences → Decision

Milestone → strengthens → Confidence

Relationships allow AI to reason about how different aspects of a person's life influence one another.

---

## 3. Evidence

Every important node stores supporting evidence.

Evidence may include:

* User statements
* Previous conversations
* Explicit confirmations
* Repeated observations

This makes the graph explainable and transparent.

---

## 4. Confidence

Each node maintains a confidence score.

Confidence increases when:

* The user confirms information.
* Similar evidence appears repeatedly.
* Multiple conversations support the same understanding.

Confidence decreases when:

* Contradictory evidence appears.
* The user edits or removes information.
* Reflection identifies uncertainty.

---

# Node Structure

Every node contains:

* Unique ID
* Type
* Name
* Description
* Confidence Score
* Evidence
* Created Date
* Last Updated
* Validation Status

Example:

Dream

Name: AI Engineer

Confidence: 92%

Evidence:

* "I want to become an AI Engineer."

Validated: Yes

---

# Relationship Structure

Every relationship contains:

* Source Node
* Target Node
* Relationship Type
* Confidence
* Supporting Evidence

Example:

Dream

↓

motivates

↓

Goal

---

# Graph Update Process

The Understanding Graph is updated through the following pipeline:

Conversation

↓

Memory Agent

↓

Understanding Agent

↓

Reflection Agent

↓

Confidence Update

↓

User Validation (if required)

↓

Graph Update

---

# User Control

The Understanding Graph is always user-controlled.

Users can:

* View all nodes
* Edit information
* Delete information
* Correct misunderstandings
* Confirm AI inferences

The AI never permanently locks information.

---

# Version 1 Scope (MVP)

The first version supports only:

* Dreams
* Goals
* Skills
* Interests
* Motivations
* Values
* Learning Style
* Confidence

Additional node types may be introduced in future versions.

---

# Design Principles

The Understanding Graph follows these principles:

1. Every important understanding has evidence.
2. Every understanding has a confidence score.
3. Relationships are as important as individual nodes.
4. Users own and control their graph.
5. The graph continuously evolves through interaction.
6. Reflection validates major updates before they become permanent.

---

# Future Extensions

Future versions may introduce:

* Emotional trends
* Habit tracking
* Multi-user relationship graphs
* Temporal reasoning
* Adaptive confidence models
* Cross-device synchronization

---

# Summary

The Understanding Graph transforms conversation history into a structured, explainable, and evolving representation of the user's journey.

It enables multiple AI agents to collaborate through a shared understanding rather than isolated memories, making personalization more transparent, consistent, and user-controlled.
