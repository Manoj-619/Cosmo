# User Data Collection Documentation

This document outlines all the data points collected for users in the Zavmo platform, organized by different stages and models.

## 1. Basic Profile Information
Data collected in the UserProfile model for basic user information.

### Personal Information
- First Name
- Last Name
- Age
- Education Level (choices):
  1. Primary School
  2. Middle School
  3. High School
  4. Associate Degree
  5. Bachelor's Degree
  6. Master's Degree
  7. PhD

### Professional Information
- Current Role
- Current Industry
- Years of Experience
- Job Duration
- Manager
- Department

## 2. Training Needs Analysis (TNA)
Data collected during the assessment phase.

- Assessment Area
- Bloom's Taxonomy Criteria (JSON)
- User Assessed Knowledge Level (scale 1-7):
  1. Novice (Basic awareness)
  2. Advanced Beginner (Limited practical application)
  3. Competent (Independent application)
  4. Proficient (Deep understanding)
  5. Expert (Strategic application)
  6. Master (Industry leading)
  7. Thought Leader (Setting industry standards)
- Zavmo Assessed Knowledge Level (same scale as above)
- Evidence of Assessment
- Knowledge Gaps

## 3. 4D Framework Stages

### 3.1 Discover Stage
Initial learning assessment and goal setting.

- Learning Goals
- Learning Goal Rationale
- Knowledge Level:
  1. Beginner
  2. Intermediate
  3. Advanced
  4. Expert
- Application Area

### 3.2 Discuss Stage
Planning and curriculum development.

- Learning Style
- Timeline (hours per week)
- Curriculum Plan (JSON)

### 3.3 Deliver Stage
Learning execution and progress tracking.

- Lessons (JSON)
  - List of dictionaries, each representing a lesson
- Completion Status (Boolean)

### 3.4 Demonstrate Stage
Assessment and evaluation of learning outcomes.

- Evaluations (JSON)
  - List of dictionaries, each representing an evaluation
- Understanding Level:
  1. Beginner
  2. Intermediate
  3. Advanced
  4. Expert
- Feedback Summary

## 4. Organization Information
Data about the user's organization.

- Organization ID
- Organization Name

## Notes

1. All stages include timestamps for creation and updates
2. Each stage maintains a relationship with the user and the sequence
3. JSON fields allow for flexible data structures while maintaining database integrity
4. Most fields include null/blank options to allow for gradual data collection
5. Each stage includes methods for:
   - Checking completion status
   - Generating summaries
   - Displaying formatted data

## Data Usage

This data is collected and used to:
1. Personalize learning experiences
2. Track progress through the 4D framework
3. Generate insights about learning patterns
4. Provide targeted feedback and support
5. Measure learning outcomes 