from sentence_transformers import SentenceTransformer, util
import pickle
import os

_model = None
_category_embeddings = None

def get_model():
    global _model
    if _model is None:
        print("Loading SentenceTransformer model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def get_embeddings():
    global _category_embeddings
    if _category_embeddings is None:
        model_path = "models/classifier_model.pkl"
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                _category_embeddings = pickle.load(f)
        else:
            print(f"Warning: {model_path} not found.")
            _category_embeddings = {}
    return _category_embeddings

def classify_message(message):
    model = get_model()
    category_embeddings = get_embeddings()

    if not category_embeddings:
        return "Unknown", 0.0

    msg_emb = model.encode(message)

    similarities = {
        cat: util.cos_sim(msg_emb, emb)[0][0].item()
        for cat, emb in category_embeddings.items()
    }

    best_category = max(similarities, key=similarities.get)
    confidence = round(similarities[best_category], 2)

    return best_category, confidence
