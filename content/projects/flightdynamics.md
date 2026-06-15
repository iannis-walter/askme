---
title: "FlightDynamics — High-fidelity C++ flight simulator"
slug: flightdynamics
stack: [C++17, OpenGL 3.2, CMake, ImGui, Catch2, GLFW]
tags: [cpp, systems, numerical-methods, real-time, simulation, testing]
role_relevance: [systems, fullstack]
---

## Problem
Build a high-fidelity 6-DoF (six degrees of freedom) flight dynamics simulator for a Cessna 172, in modern C++, with real-time physics and a production-grade software architecture — rigorous enough to stand next to professional aerospace engineering work.

## What I built
A complete flight simulator: full six-degrees-of-freedom rigid-body dynamics, real-time physics at **100 Hz**, OpenGL 3.2 3D rendering at **60 FPS**, and a professional ImGui HUD (airspeed, altitude, attitude, engine parameters). It includes a Cessna 172 aerodynamic model (full CL/CD/Cm coefficient set), an ISA 1976 atmosphere model, and telemetry recording (all state variables logged to CSV at 100 Hz).

## Technical decisions
- **Newton–Euler rigid-body dynamics** with a 12-dimensional state vector (position, velocity, orientation, angular velocity).
- **RK4 (Runge–Kutta 4th order)** numerical integration for stable, long-term-accurate simulation.
- **Quaternion-based orientation** to avoid gimbal lock — robust attitude tracking with no singularities.
- **Modular C++17 architecture on SOLID principles**: separate Physics Engine, Rendering System, Control Input, Telemetry Logger, Atmosphere Model and Aircraft Model.
- Build system with CMake; dependencies (GLFW, ImGui, Catch2) vendored via FetchContent.

## Engineering rigor
- 2,500+ lines of production code, 2,000+ lines of test code.
- 58 unit tests (Catch2), ~95% code coverage, passing build.
- Full CMake → unit-testing → packaging/deployment pipeline.

## Why this matters for Mistral
Demonstrates strong low-level C++ and applied numerical computing — real-time integration schemes, state-space models, stability and error analysis — backed by serious testing discipline. The same foundations (numerical methods, performance, rigorous engineering) that underpin real ML/systems work, shown end to end.
