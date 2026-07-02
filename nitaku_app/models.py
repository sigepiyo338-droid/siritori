from django.db import models

class Answers(models.Model):
    question = models.ForeignKey('Questions', models.DO_NOTHING, blank=True, null=True)
    choice = models.CharField(max_length=1)

    class Meta:
        managed = False
        db_table = 'answers'
        verbose_name = 'Answer'
        verbose_name_plural = 'Answers'

    def __str__(self):
        return f"Answer {self.id} for Q{self.question_id}: {self.choice}"


class Personalities(models.Model):
    name = models.CharField(max_length=50)
    label = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'personalities'
        verbose_name = 'Personality'
        verbose_name_plural = 'Personalities'

    def __str__(self):
        return f"{self.name} ({self.label})"


class Questions(models.Model):
    text = models.CharField(max_length=200)
    option_a = models.CharField(max_length=100)
    option_b = models.CharField(max_length=100)
    author = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'questions'
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'

    def __str__(self):
        return self.text


class Scores(models.Model):
    question = models.ForeignKey(Questions, models.DO_NOTHING, blank=True, null=True)
    personality = models.ForeignKey(Personalities, models.DO_NOTHING, blank=True, null=True)
    option = models.CharField(max_length=1, blank=True, null=True)
    count = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'scores'
        verbose_name = 'Score'
        verbose_name_plural = 'Scores'

    def __str__(self):
        return f"Score for Q{self.question_id} - {self.personality} ({self.option}): {self.count}"
