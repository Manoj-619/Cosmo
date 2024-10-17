import json

def parse_curriculum(curriculum_json):
    try:
        # Load the curriculum JSON
        curriculum_data = json.loads(curriculum_json)

        # Validate that the input is a list
        if not isinstance(curriculum_data, list) or not curriculum_data:
            raise ValueError("Expected a non-empty list of curriculums.")

        # Extract relevant fields for the first curriculum
        curriculum = curriculum_data[0]  # Assuming we want to process the first curriculum
        parsed_data = {
            "title": curriculum.get('title', '').strip(),
            "subject": curriculum.get('subject', '').strip(),
            "level": str(curriculum.get('level', '')).strip(),
            "modules": []
        }

        # Validate main curriculum fields
        if not parsed_data["title"]:
            raise ValueError("Curriculum title is required.")
        if not parsed_data["subject"]:
            raise ValueError("Curriculum subject is required.")
        if not parsed_data["level"].isdigit():
            raise ValueError("Curriculum level must be a numeric value.")

        # Loop through modules and extract information
        for module in curriculum.get('modules', []):
            module_info = {
                "module_title": module.get('title', '').strip(),
                "lessons": [],
                "learning_outcomes": []
            }

            # Validate module fields
            if not module_info["module_title"]:
                raise ValueError("Module title is required.")

            # Extract lessons within the module
            for lesson in module.get('lessons', []):
                lesson_title = lesson.get('title', '').strip()
                content = lesson.get('content', '').strip()
                duration = lesson.get('duration', 0)

                if not lesson_title:
                    raise ValueError("Lesson title is required.")
                if not content:
                    raise ValueError("Lesson content is required.")
                if not isinstance(duration, (int, float)) or duration <= 0:
                    raise ValueError(f"Lesson duration must be a positive number. Got: {duration}")

                module_info["lessons"].append({
                    "lesson_title": lesson_title,
                    "content": content,
                    "duration": duration
                })

            # Extract learning outcomes and assessment criteria
            for outcome in module.get('learning_outcomes', []):
                description = outcome.get('description', '').strip()
                assessment_criteria = outcome.get('assessment_criteria', [])

                if not description:
                    raise ValueError("Learning outcome description is required.")
                
                # Validate assessment criteria
                if not isinstance(assessment_criteria, list):
                    raise ValueError("Assessment criteria must be a list.")
                assessment_criteria = [criterion.strip() for criterion in assessment_criteria if criterion.strip()]

                module_info["learning_outcomes"].append({
                    "description": description,
                    "assessment_criteria": assessment_criteria
                })

            parsed_data["modules"].append(module_info)

        return parsed_data

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None
    except ValueError as ve:
        print(f"Validation error: {ve}")
        return None
