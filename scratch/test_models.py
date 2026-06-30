import os
import sys
import django

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "siritori_project.settings")
django.setup()

from nitaku_app.models import Question, Personality, Answer, Score

def test_query():
    print("Testing Django ORM queries on twotakukun_web models...")
    
    questions = Question.objects.all()
    print(f"Questions count: {questions.count()}")
    for q in questions[:5]:
        print(f" - Question ID: {q.id}, Text: '{q.text}' (by {q.author})")
        
    personalities = Personality.objects.all()
    print(f"Personalities count: {personalities.count()}")
    for p in personalities[:5]:
        print(f" - Personality: {p.name} ({p.label})")

    answers = Answer.objects.all()
    print(f"Answers count: {answers.count()}")

    scores = Score.objects.all()
    print(f"Scores count: {scores.count()}")
    print("Query test completed successfully!")

if __name__ == "__main__":
    test_query()
