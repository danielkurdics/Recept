from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
import os
import json
import re
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# uvicorn recept_1:appl --reload


def sanitize_json(response_text):
    """
    Sanitize a potentially malformed JSON string.
    """
    # Remove extraneous text before/after JSON
    json_start = response_text.find("{")
    json_end = response_text.rfind("}")
    if json_start == -1 or json_end == -1:
        raise ValueError("No JSON object found in response.")
    response_text = response_text[json_start:json_end + 1]

    # Replace single quotes with double quotes
    response_text = response_text.replace("'", '"')

    # Remove trailing commas inside JSON objects or arrays
    response_text = re.sub(r",\s*([}\]])", r"\1", response_text)

    # Ensure JSON keys and values are properly quoted
    response_text = re.sub(r'(?<!")(\b\w+\b)(?=\s*:)', r'"\1"', response_text)

    return response_text

def extract_recipes(text):
    """
    Extract recipes from malformed JSON using regex as a fallback.
    """
    recipe_pattern = re.compile(r'"name":\s*"(.*?)".*?"ingredients":\s*\[(.*?)\].*?"instructions":\s*"(.*?)"', re.DOTALL)
    matches = recipe_pattern.findall(text)

    recipes = []
    for match in matches:
        name, ingredients, instructions = match
        ingredients = [ing.strip().strip('"') for ing in ingredients.split(",")]
        recipes.append({
            "name": name.strip(),
            "ingredients": ingredients,
            "instructions": instructions.strip(),
        })

    if not recipes:
        raise ValueError("No recipes found in the response.")

    return recipes

# Load environment variables from the .env file
_ = load_dotenv(find_dotenv())
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

OpenAI.api_key = api_key

# FastAPI application
appl = FastAPI()

# Add CORS middleware to allow frontend to access the backend
appl.add_middleware(
CORSMiddleware,
allow_origins=["*"],  # Allow all origins (for testing purposes)
allow_credentials=True,
allow_methods=["*"],  # Allow all HTTP methods
allow_headers=["*"],  # Allow all headers
)

# Serve static files (HTML, CSS, JS)
appl.mount("/static", StaticFiles(directory="static"), name="static")

@appl.get("/")
async def serve_index():
    with open(os.path.join("static", "index.html")) as f:
        return HTMLResponse(content=f.read(), status_code=200)

# Input model for recipe preferences
class RecipePreferences(BaseModel):
    preferences: str
    diet: str = None



@appl.post("/recommend")
async def recommend_recipes(input: RecipePreferences):
    """
    Recommend recipes based on user preferences using ChatGPT API.
    """
    diet_info = f" The user follows a {input.diet} diet." if input.diet else ""
    prompt = (
        f"Recommend three recipes based on these preferences: {input.preferences}.{diet_info} "
        "Provide the recipes in a JSON format with 'name', 'ingredients', and 'instructions'."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful recipe assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
            temperature=0.3,
        )

        recipes_raw = response.choices[0].message.content.strip()

        try:
            sanitized_recipes = sanitize_json(recipes_raw)
            recipes_json = json.loads(sanitized_recipes)
            return {"recipes": json.dumps(recipes_json)}
        except (ValueError, json.JSONDecodeError):
            # Fallback to regex extraction
            extracted_recipes = extract_recipes(recipes_raw)
            return {"recipes": json.dumps(extracted_recipes)}
        
    except Exception as e:
        return {"error": str(e)}
