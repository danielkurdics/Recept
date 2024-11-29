from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
import os




# http://127.0.0.1:8000/docs
# uvicorn recept:app --reload


# Env fájl betöltés
_ = load_dotenv(find_dotenv())
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)


if client is None:
    print("API kulcs nem található. Ellenőrizd az .env fájlt.")
else:

    # Modell
    model = "gpt-3.5-turbo"
    temperature = 0.3
    tokens = 100

    # FastAPI alkalmazás
    app1 = FastAPI()

    # Bemeneti modell
    class RecipePreferences(BaseModel):
        preferences: str
        diet: str = None

    @app1.post("/recommend")
    async def recommend_recipes(input: RecipePreferences):
        """
        Recepteket ajánl ChatGPT API segítségével a felhasználói preferenciák alapján.
        """
        # Prompt készítése a ChatGPT számára
        diet_info = f" The user follows a {input.diet} diet." if input.diet else ""
        prompt = (
            f"Recommend three recipes based on these preferences: {input.preferences}.{diet_info} "
            "Provide the recipes in a JSON format with 'name', 'ingredients', and 'instructions'."
        )
        
        # Hívás a ChatGPT API-ra
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful recipe assistant."},
                    {"role": "user", "content": prompt}
                    ],
                max_tokens=tokens,
                temperature=temperature
            )

            # A GPT válaszának kinyerése
            gpt_reply = response["choices"][0]["message"]["content"]
            return {"recipes": gpt_reply}

        except Exception as e:
            return {"error": str(e)}
    
