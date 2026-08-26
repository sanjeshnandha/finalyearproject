import os
from google import genai

api_key = "AQ.Ab8RN6IrsYmpmknFNDQ2LfcTbnsS71q_gxZnsc9k00ppk1zcZw"
client = genai.Client(api_key=api_key)
for model in client.models.list():
    if "flash" in model.name:
        print(model.name)
