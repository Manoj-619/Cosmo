# Agent architecture

### NOTE: very experimental, inspired by OpenAI's swarm.

## **Main Ideas:**


**4D Sequence Framework**: `In Progress`
   - The 4D agent represents the four distinct stages: **Discussion**, **Discovery**, **Delivery**, and **Demonstration**.

   - **Profile Collection**: This stage should be done only once. After the profile is collected, the 4D sequence can be repeated, establishing a one-to-many relationship between the user profile and multiple 4D sequences.
   - Use a one-to-many model for the profile collection, allowing each user? / user profile?to have multiple associated 4D sequences.

**Goals:**
- Single Profile, Multiple 4D Sequences:
   Ensure that each learner/user profile is collected once, and then allow them to go through multiple 4D sequences (i.e., multiple learning sessions).


**Swarm and Agent Structure**: 
   - Explore using swarm concepts and a multiple agent system to manage the 4D sequence.
   - The system will focus on a central **4D-agent**, which manages the four stages (Discussion, Discovery, Delivery, Demonstration).

---

## **Goals:**

1. **Create Modular Agents**: Design a modular, scalable system where each of the 4D stages can operate independently, while being centrally managed by the 4D-agent.

2. **Optimize Transitions between Agents**: Seamless handoffs between the stages (from discussion to demonstration) to ensure smooth progression through the learning/task process.

---

## **Methods:**

### 1. **Discussion Agent**:
   Have a conversation with the learner to identify their goals, learning style, and preferences.

   - **Functions**:
     - `update_discussion`: Update the learner's discussion profile, (perhaps asynchronously or in cache until the conversation is complete).
     - `discussion_completed`: Once the conversation is complete, handoff to the **Discovery Agent**.

- **Considerations**:
   - Perhaps when the discussion is complete (handoff to Discovery Agent), we should update the discussion data in DB.
   - What is the condition for the discussion to be complete?
   - IDEA: We should summarize the discussion and ask the learner if they would like to make any changes?


### 2. **Discovery Agent**:
   Generate a curriculum based on the learner's input. Engage in a discussion with the user and customize the curriculum accordingly so that they are happy with the direction.

- **Functions**:
   - `generate_curriculum`: Generate a curriculum based on the learner's input.
   - `curriculum_approved`: Once the learner approves, hand off to the **Delivery Agent** to create lessons or revert to the **4D-agent** if needed.

- **Considerations**:
   - Do we need an edit/update curriculum function?
   - Probably good to explain the curriculum to the learner, and then ask if they would like to make any changes.


### 3. **Delivery Agent**:
   Develop lessons for the learner based on the approved curriculum and _deliver_ (or teach) them one by one.

- **Functions**:
   - `get_next_lesson` or `get_lessons`: Generate lesson(s) tailored to the curriculum.
   - `lessons_completed`: Once the learner has completed all lessons, handoff to the **Demonstration Agent**.

- **Considerations**:
   - It may be a good idea to make this generate 1 lesson at a time, and then handoff to the Demonstration Agent for evaluation. Need to evaluate pros and cons.
   - How many lessons in total should be generated? How to track their states? When do we consider a lesson to be _delivered_?
   - Later, we can connect this method to a vector DB / `@AMI` to generate lessons from retrieved context.
   - Not sure if we should handoff to **Demonstration Agent** or if it should be routed back to the **4D-agent** to determine the next step.

### 4. **Demonstration Agent**:
   Evaluate the learner's progress through quizzes or exercises.

- **Functions**:
   - `question_answer`: Generate evaluation content, such as question-answer pairs or multiple-choice questions.
   - `evaluation_completed`: Complete the evaluation and return the results to the **4D-agent** for further steps or revisions.

- **Considerations**:
   - How many questions should be generated? How to track their states? When do we consider an evaluation to be _completed_?
   - Should we score them? How to do that?
   - Should we not have a **Feedback Agent** post-evaluation? or is that `@AMI` + `@JAN` ?

### 5. **4D-Agent (Central)**:
   - **Goal**: Manage the entire 4-stage process and ensure seamless handoff between agents.
   - **Functions**:
     - Oversee and coordinate communication and handoffs between the different stages (Discussion, Discovery, Delivery, Demonstration).
     - Monitor progress, manage logging, and ensure feedback loops between stages.
