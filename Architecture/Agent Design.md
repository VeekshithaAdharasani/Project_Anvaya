# Agent Design

## Purpose

This document defines the responsibilities, inputs, outputs, and interactions of each agent in Project ANVAYA.

Each agent has a single responsibility and communicates through the Coordinator Agent and the Understanding Layer.

---

# 1. Coordinator Agent

## Purpose

Acts as the orchestrator of the system.

## Responsibilities

* Receives user requests.
* Determines which agents should execute.
* Combines outputs.
* Returns the final response.

## Input

* User message

## Output

* Final response

---

# 2. Memory Agent

## Purpose

Stores conversation history and important events.

## Responsibilities

* Store conversations
* Retrieve previous context
* Store important milestones

## Output

Conversation memory

---

# 3. Understanding Agent ⭐

## Purpose

Converts conversations into structured understanding.

## Responsibilities

* Extract goals
* Extract motivations
* Extract interests
* Update confidence
* Update Understanding Graph

## Output

Updated Understanding Graph

---

# 4. Reflection Agent

## Purpose

Validates understanding updates.

## Responsibilities

* Detect contradictions
* Detect temporary emotions
* Ask for clarification
* Approve long-term updates

---

# 5. Curiosity Agent

## Purpose

Improves understanding through questions.

## Responsibilities

* Detect uncertainty
* Ask meaningful questions
* Reduce ambiguity

---

# 6. Planner Agent

## Purpose

Generates personalized plans.

## Responsibilities

* Daily plans
* Weekly goals
* Long-term roadmap

---

# 7. Learning Agent

## Purpose

Recommends learning resources.

## Responsibilities

* Courses
* Tutorials
* Books
* Practice tasks

---

# 8. Opportunity Agent

## Purpose

Finds opportunities matching the user's understanding.

## Responsibilities

* Internships
* Jobs
* Competitions
* Scholarships
* Hackathons

---

# 9. Shield Agent

## Purpose

Maintains safety, transparency, and privacy.

## Responsibilities

* Safety checks
* Privacy
* Explainability
* User control

---

# Agent Communication

All agents communicate through:

Coordinator Agent

↓

Understanding Layer

↓

Understanding Graph

Agents never directly modify another agent's state.

---

# MVP

Version 1 implements:

* Coordinator
* Memory
* Understanding
* Reflection
* Curiosity

Planner, Learning, Opportunity, and Shield can start simple and grow over time.
