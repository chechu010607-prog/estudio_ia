import os
from dotenv import load_dotenv
from google import genai  

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("No se encontró la GOOGLE_API_KEY en el archivo .env")

# Creamos el cliente global
client = genai.Client(api_key=api_key)

def obtener_cliente():
    return client