from CrossValidation.classifier import *
from CrossValidation.crossval import *
from CrossValidation.evaluation import *


import joblib
import os
import numpy as np
from utils import get_batch_openai_embedding, get_parent_ssa

model = joblib.load(os.path.join("zavmo/classification/models", "SSA_classification_model.pkl"))

missed_ofqual_records = pd.read_csv(os.path.join("zavmo/classification/data/test", "missed_ofqual_records.csv"))

# Group by ofqual_id and aggregate the text columns
data = missed_ofqual_records.groupby('ofqual_id').agg({
    'title': lambda x: ', '.join(x.fillna('').astype(str)),
    'description': lambda x: ' '.join(x.fillna('').astype(str)), 
    'overview': 'first',  # Take first overview since it's same for each ofqual_id
    'id': lambda x: list(x),
    'learning_outcomes': lambda x: list(x),
}).reset_index()

## title + description + overview
sample_text_for_embeddings = [f"{r['title']}\n\n{r['description']}\n\n{r['overview']}" for i,r in data.iterrows()]

print("\n\nGenerating Embeddings....")
X_embeddings  = get_batch_openai_embedding(sample_text_for_embeddings, dimensions=768)

print("\n\nPredicting sub SSA....")
predicted_sub_SSAs = model.predict(np.array(X_embeddings))
df = pd.DataFrame(sample_text_for_embeddings, columns=["text"])
df["predicted_sub_SSA"] = predicted_sub_SSAs

print("\n\nGetting SSA....")
df["SSA"] = df["sub_SSA"].apply(get_parent_ssa)  ## predicted sub SSA
df['ofqual_id'] = data['ofqual_id'].tolist()

# Create mapping dictionaries for SSA and sub-SSA by ofqual_id
ssa_mapping = dict(zip(df['ofqual_id'], df['SSA']))
sub_ssa_mapping = dict(zip(df['ofqual_id'], df['sub_SSA']))

# Map the values back to missed_ofqual_records using the ofqual_id
missed_ofqual_records['SSA'] = missed_ofqual_records['ofqual_id'].map(ssa_mapping)
missed_ofqual_records['sub_SSA'] = missed_ofqual_records['ofqual_id'].map(sub_ssa_mapping)

# Save the updated dataframe
missed_ofqual_records.to_excel(os.path.join("zavmo/classification/data/predicted", "ofqual_classified.xlsx"), index=False)
