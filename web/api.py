from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle
import pandas as pd
from keras import models

with open('encoding_vars.pkl', 'rb') as f:
    my_data = pickle.load(f)

num = my_data['num']
categ = my_data['categ']
encoder = my_data['encoder']
scaler = my_data['scaler']

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = models.load_model('../modeling/model.keras')

class Features(BaseModel):
    features: list

@app.post("/predict/")
def predict(features: Features):
    feature_names = ['area', 'rooms', 'floor', 'rent', 'parking', 'construction_year', 'elevator', 'location', 
                     'voivodship', 'outdoor_space','heating', 'building']
    new_observation = pd.DataFrame([features.features], columns=feature_names)
    new_observation_encoded = pd.DataFrame(encoder.transform(new_observation[categ]), columns=encoder.get_feature_names_out(categ))
    new_observation = pd.concat([new_observation.drop(categ, axis=1).reset_index(drop=True), new_observation_encoded], axis=1)
    new_observation[num] = scaler.transform(new_observation[num])
    prediction = model.predict(new_observation, verbose = 0)
    return int(prediction[0])