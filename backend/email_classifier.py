import pickle
import os

_model = None
_category_embeddings = None

EMAIL_CATEGORIES = {
    "Meeting Request": "Requests for appointments, calls, or demos.",
    "Job Application": "Resumes, cover letters, and application follow-ups.",
    "Sales/Spam": "Promotional offers, cold outreach, or irrelevant marketing.",
    "Project Update": "Status reports, task updates, or internal communications.",
    "Urgent Support": "Critical issues, downtimes, or high-priority help requests.",
    "General Inquiry": "Questions about services, pricing, or general information."
}

def get_model():
    global _model
    if _model is None:
        print("📦 Loading SentenceTransformer model (this may take a few seconds)...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def get_embeddings():
    global _category_embeddings
    if _category_embeddings is None:
        # Check if we have a pre-saved model, otherwise compute on fly
        model_path = "models/email_classifier_model.pkl"
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                _category_embeddings = pickle.load(f)
        else:
            print("Computing fresh embeddings for Email Categories...")
            model = get_model()
            _category_embeddings = {
                cat: model.encode(desc) for cat, desc in EMAIL_CATEGORIES.items()
            }
            # Save for later
            os.makedirs("models", exist_ok=True)
            with open(model_path, "wb") as f:
                pickle.dump(_category_embeddings, f)
            
    return _category_embeddings

def classify_email(subject, body):
    from sentence_transformers import util
    full_text = f"Subject: {subject}\nBody: {body}"
    
    model = get_model()
    category_embeddings = get_embeddings()

    msg_emb = model.encode(full_text)

    similarities = {
        cat: util.cos_sim(msg_emb, emb)[0][0].item()
        for cat, emb in category_embeddings.items()
    }

    best_category = max(similarities, key=similarities.get)
    confidence = round(similarities[best_category], 2)

    return best_category, confidence
