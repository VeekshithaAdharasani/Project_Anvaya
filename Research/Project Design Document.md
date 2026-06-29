# Project Design Document

---

# Project ANVAYA *(Working Title)*

## From Memory to Understanding

### An Understanding-Driven Multi-Agent AI Architecture

---

## Author

**Veekshitha Adharasani**

B.Tech Computer Science (Artificial Intelligence & Machine Learning)

SR University

---

## Project Type

Google × Kaggle

5-Day AI Agents: Intensive Vibe Coding Course

Capstone Project

---

## Version

Version 1.0

---

## Status

Research & Design Phase

---

## Date

June 2026

---

# Table of Contents

1. Definition of Terms

2. Abstract

3. Introduction

4. Background

5. Problem Statement

6. Motivation

7. Research Question

8. Hypothesis

9. Proposed Solution

10. Understanding Layer

11. Understanding Graph

12. Multi-Agent Architecture

13. Novel Contributions

14. Ethical Principles

15. Non Goals

16. Failure Modes

17. Evaluation

18. Expected Impact

19. Future Work

20. References

---

# 1. Definition of Terms

## Memory

Memory is the ability of an AI system to retain and retrieve previously observed information, conversations, events, or facts.

Memory answers one question:

> **What happened?**

---

## Understanding

Understanding is the continuous process of interpreting information to build an evolving representation of a person's goals, motivations, values, learning style, decision-making behavior, preferences, and growth.

Unlike memory, understanding is not a collection of facts. It is an evolving model that changes through evidence, reflection, and user feedback.

Understanding answers one question:

> **Who is this person becoming?**

---

## Reflection

Reflection is the process of evaluating whether newly observed information represents a temporary situation, a contradiction, or a genuine long-term change before modifying the user's Understanding Graph.

Reflection answers:

> **Should the understanding change?**

---

## Curiosity

Curiosity is the intentional process of asking meaningful questions to reduce uncertainty and improve the accuracy of the Understanding Graph.

Curiosity answers:

> **What am I still missing?**

---

## Understanding Layer

The Understanding Layer is an architectural component positioned between Memory and Decision Making.

Its responsibility is to construct, maintain, explain, validate, and continuously revise an explicit understanding of the user.

Rather than relying solely on stored conversations, all specialized agents consult the Understanding Layer before making recommendations or taking actions.

---

## Understanding Graph

The Understanding Graph is a structured representation of the user's evolving journey.

It contains interconnected information such as:

- Long-Term Dreams
- Current Goals
- Motivations
- Skills
- Interests
- Learning Style
- Decision Style
- Values
- Confidence Trends
- Milestones
- Growth History
- Evidence
- Confidence Scores

Unlike a user profile, the Understanding Graph evolves through continuous interaction, reflection, and user validation.

## Purpose

This document defines the vision, terminology, and high-level design principles for Project ANVAYA. It serves as the primary reference for all architectural and implementation decisions throughout the project.

## Project Scope

This document defines the overall vision and terminology of the project. Detailed implementation, agent specifications, workflows, APIs, and database schemas are documented separately.

## Design Principles

1. Memory stores information; understanding interprets it.

2. Users own their Understanding Graph.

3. Every important inference should have supporting evidence.

4. Reflection precedes major understanding updates.

5. AI supports human decisions; it does not replace them.

6. Understanding continuously evolves through interaction and feedback.