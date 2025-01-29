import sys
from enum import Enum
from pydantic import BaseModel
from fastapi import FastAPI, Query, HTTPException
from huggingface_hub import hf_hub_download
import fasttext
from setfit import SetFitModel
import pandas as pd
import numpy as np


sys.path.append('cpv_info/')
import cpv_dataframe

ft_repo_id = "tanjapry/fasttext_ausschreibung"
ft_model_path = hf_hub_download(repo_id=ft_repo_id, filename="model.bin")
fasttext_model = fasttext.load_model(ft_model_path)

sf_model_id = "tanjapry/setfit_ausschreibung"
setfit_model = SetFitModel.from_pretrained(sf_model_id)


CPV_DIR = "cpv.json"
cpv_numbers = pd.read_json(CPV_DIR)

app = FastAPI()

class ModelName(str, Enum):
    setfit = "Großes Model"
    fasttext = "Kleines Model"

class User_input(BaseModel):
    model_name : ModelName
    k : int
    q : str

@app.post("/cpv")
async def read_items(input:User_input):
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
    
    if input.model_name is ModelName.setfit:
        if setfit_model is None:
            raise HTTPException(status_code=500, detail="SetFit model not loaded")
        proba = setfit_model.predict_proba(input.q)
        proba_np = proba.numpy()
        top_k_indices = np.argsort(proba_np)[::-1][:input.k]
        top_k_labels = [setfit_model.labels[i] for i in top_k_indices]
        top_k_probabilities = proba_np[top_k_indices]
        top_k_percentages = [f"{prob * 100:.2f}%" for prob in top_k_probabilities]

    elif input.model_name == ModelName.fasttext:
        if fasttext_model is None:
            raise HTTPException(status_code=500, detail="FastText model not loaded")
        predictions = fasttext_model.predict(input.q, k=input.k)
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

    result_df = cpv_dataframe.process_files("cpv_info/cpv_2008_ver_2013.xlsx", "cpv_info/cpv_2008_explanatory_notes_de.pdf")

    cpv_description_list = []

    for label in top_k_labels:
        label_description = result_df[(result_df["classification"] == "division") & (result_df["division"] == label)]["description"].values[0]
        cpv_description_list.append(label_description)

    top_k_predictions = list(zip(bezeichnung_list, cpv_list, cpv_description_list, top_k_percentages))



    return {"model": input.model_name, "anfrage": input.q, "vorhergesagte_bezeichnung": top_k_predictions}

@app.post("/cpv_groups")
async def read_groups(cpv_number: str):
    group_list = []
    bezeichnung_list = []

    group_list = cpv_numbers[(cpv_numbers["classification"] == "group") & (cpv_numbers["division"] == int(str(cpv_number)[:2]))]["CODE"].tolist()
    
    bezeichnung_list = cpv_numbers[(cpv_numbers["classification"] == "group") & (cpv_numbers["division"] == int(str(cpv_number)[:2]))]["DE"].tolist()

    groups_descriptions = list(zip(group_list, bezeichnung_list))

    return groups_descriptions
