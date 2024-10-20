# Zavmo API

Zavmo backend API, built with Django - for managing user profiles, LLM messages, stage transitions, and personalized learning journeys.

## API Endpoints


## Stages of Learning Journey

The learning journey is divided into five stages:

1. Profile: Gathering basic user information
2. Discover: Understanding user's learning goals and interests
3. Discuss: Defining specific learning objectives
4. Deliver: Providing learning materials and tracking progress
5. Demonstrate: Assessing understanding and providing feedback

Each stage is configured using YAML files in the `zavmo/assets/data/` directory.

## Configuration Files

YAML configuration files play a crucial role in defining stage-specific behaviors:

- `curriculum_creation.yaml`: Defines the curriculum creation process
- `deliver.yaml`: Configures the deliver stage
- `discuss.yaml`: Sets up the discuss stage
- `exam_creation.yaml`: Outlines the exam creation process

Example of a configuration file:

```yaml
zavmo/assets/data/curriculum_creation.yaml
```