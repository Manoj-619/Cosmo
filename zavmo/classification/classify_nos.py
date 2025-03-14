from CrossValidation.classifier import *
from CrossValidation.crossval import *
from CrossValidation.evaluation import *


import joblib
import os
import numpy as np
from utils import get_batch_openai_embedding, get_parent_ssa

model = joblib.load(os.path.join("zavmo/classification/models", "SSA_classification_model.pkl"))

missed_nos_records = pd.read_csv(os.path.join("zavmo/classification/data/test", "nos.csv"))

sample_text_for_embeddings = [f"Industry: {r['industry']}\n\nOverview: {r['overview']}\n\n" for i,r in missed_nos_records.iterrows()]
X_embeddings  = get_batch_openai_embedding(sample_text_for_embeddings, dimensions=768)

print("\n\nPredicting sub SSA....")
predicted_sub_SSAs = model.predict(np.array(X_embeddings))
df = pd.DataFrame(sample_text_for_embeddings, columns=["text"])
df["predicted_sub_SSA"] = predicted_sub_SSAs

print("\n\nGetting SSA....")
df["SSA"] = df["predicted_sub_SSA"].apply(get_parent_ssa)
df['nos_id'] = missed_nos_records['nos_id'].tolist()

# Create mapping dictionaries for SSA and sub-SSA by ofqual_id
ssa_mapping = dict(zip(df['nos_id'], df['SSA']))
sub_ssa_mapping = dict(zip(df['nos_id'], df['predicted_sub_SSA']))

# Map the values back to missed_ofqual_records using the ofqual_id
missed_nos_records['SSA'] = missed_nos_records['nos_id'].map(ssa_mapping)
missed_nos_records['predicted_sub_SSA'] = missed_nos_records['nos_id'].map(sub_ssa_mapping)

# Save the updated dataframe
missed_nos_records.to_excel(os.path.join("zavmo/classification/data/predicted", "missed_nos_records_with_predictions.xlsx"), index=False)