


This is from Cosmo's commit on the `CurriculumGeneration` branch.

https://github.com/Iridescent-Technologies/zavmo-api/blob/1c08075122f105861b87bf183cf8eb0f907b8fe2/zavmo/stage_app/models.py

```python
class Curriculum(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='curricula')
    content = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Curriculum for {self.user.username}"

# Stage 4 or (3rd D)
class DeliverStage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='deliver_stage', verbose_name="User")
    curriculum = models.ForeignKey(Curriculum, on_delete=models.SET_NULL, null=True, related_name='deliver_stages', verbose_name="Curriculum")
    current_module = models.PositiveIntegerField(default=0, verbose_name="Current Module")
    current_lesson = models.PositiveIntegerField(default=0, verbose_name="Current Lesson")
    progress = models.FloatField(default=0.0, verbose_name="Progress")
    completed_lessons = models.JSONField(default=list, verbose_name="Completed Lessons")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    total_lessons = models.PositiveIntegerField(default=0, verbose_name="Total Lessons")

    def reset(self):
        self.curriculum = None
        self.current_module = 0
        self.current_lesson = 0
        self.progress = 0.0
        self.completed_lessons = []
        self.notes = ''
        self.total_lessons = 0
        self.save()

    def set_curriculum(self, curriculum):
        self.curriculum = curriculum
        self.total_lessons = sum(len(module['lessons']) for module in curriculum.content['modules'])
        self.save()

    def update_progress(self):
        if self.curriculum and self.total_lessons > 0:
            completed = len(self.completed_lessons)
            self.progress = (completed / self.total_lessons) * 100
            self.save()

    def complete_lesson(self, module_index, lesson_index):
        lesson_id = f"{module_index}_{lesson_index}"
        if lesson_id not in self.completed_lessons:
            self.completed_lessons.append(lesson_id)
            self.update_progress()

    def get_next_lesson(self):
        if not self.curriculum:
            return None
        
        modules = self.curriculum.content.get('modules', [])
        for module_index, module in enumerate(modules):
            for lesson_index, lesson in enumerate(module.get('lessons', [])):
                lesson_id = f"{module_index}_{lesson_index}"
                if lesson_id not in self.completed_lessons:
                    return module_index, lesson_index, lesson
        
        return None  # All lessons completed

```