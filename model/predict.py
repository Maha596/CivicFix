import sys
import os
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.ai_classifier import classify_civic_image

def predict(image_path):
    """Command-line and module entry point for AI predictions."""
    result = classify_civic_image(image_path)
    return result

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python predict.py <path_to_image>")
        sys.exit(1)
    
    img_path = sys.argv[1]
    res = predict(img_path)
    print(f"Predicted Category: {res['predicted_category']}")
    print(f"Confidence: {res['confidence']}%")
    print(f"Top 3: {res['top_categories']}")
    print(f"Explanation: {res['explanation']}")
