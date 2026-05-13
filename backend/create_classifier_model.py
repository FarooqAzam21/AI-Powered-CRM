from sentence_transformers import SentenceTransformer
import pandas as pd
import pickle
import numpy as np
import os

# Sample dataset
data = {
    "message": [
        "My order hasn’t arrived",
        "I want a refund for my purchase",
        "My device is not working properly",
        "Thank you for the quick support",
        "How do I change my password?",
        "The product arrived damaged",
        "When will my delivery come?",
        "I am not happy with the service"
    ],
    "category": [
        "Order Inquiry",
        "Refund",
        "Technical Issue",
        "Feedback",
        "General Inquiry",
        "Complaint",
        "Order Inquiry",
        "Complaint"
    ]
}

df = pd.DataFrame(data)

# Load sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Create embeddings for each category
category_embeddings = {}
for category in df['category'].unique():
    messages = df[df['category'] == category]['message'].tolist()
    embeddings = model.encode(messages)
    category_embeddings[category] = np.mean(embeddings, axis=0)

# Make sure models folder exists
os.makedirs("models", exist_ok=True)

# Save the embeddings properly
with open('models/classifier_model.pkl', 'wb') as f:  # ✅ write binary
    pickle.dump(category_embeddings, f)

print("✅ classifier_model.pkl created successfully!")
