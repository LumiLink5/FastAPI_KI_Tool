from enum import Enum
from fastapi import FastAPI, Query, HTTPException
import fasttext
from setfit import SetFitModel
import pandas as pd
import numpy as np


fasttext_model = fasttext.load_model("FastText_model_35x20/model.bin")
setfit_model = SetFitModel.from_pretrained("SetFit_model_23x300")

CPV_DIR = "cpv.json"
cpv_numbers = pd.read_json(CPV_DIR)

app = FastAPI()

class ModelName(str, Enum):
    setfit = "Neuronale Netzwerke"
    fasttext = "Keine Neuronale Netzwerke"

@app.get("/")
async def read_items(
    model_name: ModelName,
    k: int,
    q: str
):
    global fasttext_model, setfit_model

    welcome_message = (
        "Willkommen zur Testanwendung für die automatische Generierung von CPV-Codes für Ausschreibungen. "
        "Diese Anwendung wurde von Dataport in Zusammenarbeit mit der Universität Bremen entwickelt. " 
        "Ziel ist es, den Prozess der Codierung zu optimieren und effizienter zu gestalten. "
    )

    end_message = (
        "Beide Modelle wurden auf denselben Datensätzen trainiert und basieren ausschließlich auf der obersten Ebene der CPV-Nummern (den Divisions). " 
        "Eine detailliertere Betrachtung der hierarchischen Struktur der CPV-Nummern wurde bisher nicht vorgenommen. " 
        "Bei dem Projekt beteiligt sind: Gerhard Klaasen, Robin Fritzsche, Marco Kruse, Andrey Krutilin, Benjamin Haberkorn, Tetiana Prykhodko. " 
        "Bei Fragen sprechen Sie uns gerne an!"
    )
    
    if model_name is ModelName.setfit:
        if setfit_model is None:
            raise HTTPException(status_code=500, detail="SetFit model not loaded")
        proba = setfit_model.predict_proba(q)
        proba_np = proba.numpy()
        top_k_indices = np.argsort(proba_np)[::-1][:k]
        top_k_labels = [setfit_model.labels[i] for i in top_k_indices]
        top_k_probabilities = proba_np[top_k_indices]
        top_k_percentages = [f"{prob * 100:.2f}%" for prob in top_k_probabilities]

    elif model_name == ModelName.fasttext:
        if fasttext_model is None:
            raise HTTPException(status_code=500, detail="FastText model not loaded")
        predictions = fasttext_model.predict(q, k=k)
        top_k_labels = [label.replace('__label__', '') for label in predictions[0]]
        top_k_probabilities = predictions[1]
        top_k_percentages = [f"{prob * 100:.2f}%" for prob in top_k_probabilities]

    print(top_k_labels)

    bezeichnung_list = []

    for label in top_k_labels:
        bezeichnung = cpv_numbers[(cpv_numbers["classification"] == "division") & 
                                        (cpv_numbers["division"] == int(label))]["DE"].values[0]
        bezeichnung_list.append(bezeichnung)

    cpv_list = []

    for label in top_k_labels:
        bezeichnung = cpv_numbers[(cpv_numbers["classification"] == "division") & 
                                        (cpv_numbers["division"] == int(label))]["CODE"].values[0]
        cpv_list.append(bezeichnung)

    top_k_predictions = list(zip(bezeichnung_list, cpv_list, top_k_percentages))

    return {"welcome_message": welcome_message, "model": model_name, "anfrage": q, "vorhergesagte_bezeichnung": top_k_predictions, "end_message": end_message}
