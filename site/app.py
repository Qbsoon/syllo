# Imports
import os
from quart import Quart, render_template, request, jsonify, send_from_directory
from quart_rate_limiter import RateLimiter, rate_limit
from datetime import timedelta
import urllib.parse
import requests
import httpx
import uvicorn


# App definition
app = Quart(__name__, template_folder="pages")
RateLimiter(app)


# Main site
@app.route("/")
async def index():
    return await render_template("index.html")


# Ask AI endpoint
@app.route("/dologic", methods=["POST"])
@rate_limit(1, timedelta(seconds=3))
async def do_logic():
    data = await request.get_json()

    syll = urllib.parse.unquote(data.get("syll", ""))
    stype = urllib.parse.unquote(data.get("type", ""))

    url = "http://127.0.0.1:51791/v1/chat/completions"
    reply = 'Something went wrong'

    messages = ""
    if stype == 0 or stype == '0':
        messages = [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. A - All x are y; E - No x are y; I - Some x are y; O - Some x are not y. Check if they\'re logically correct and explain their reasoning. Common checks:\n5 Rules (Classical Method)\n1. Middle Term Distribution (M): A middle term must be distributed (appear as the predicate of a general proposition or the subject of a negative proposition) in at least one premise.\n2. Avoiding Two Negative Premises: A valid conclusion cannot be drawn from two negative premises (e.g., "Some S are not P" and "No S is P").\n3. Negative Consistency: A negative premise implies a negative conclusion (if there is a negative premise, the conclusion must be negative).\n4. Assertion Consistency: Two affirmative premises (e.g., "Every A is B") imply an affirmative conclusion.\n5. Decomposition of Terms in the Conclusion: If a term is distributed in the conclusion, it must also be distributed in the premise from which it originates (e.g., S or P). Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check this syllogism:\n{syll}\nProvide a brief, not long of a response!\nDO NOT REFER TO RULES BY THEIR NUMBERS/IDS!'}]
    elif stype == 1 or stype == '1':
        messages =  [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. A - All x are y; E - No x are y; I - Some x are y; O - Some x are not y. Check if they\'re logically correct and explain their reasoning. Common checks:\n5 Rules (Classical Method)\n1. Middle Term Distribution (M): A middle term must be distributed (appear as the predicate of a general proposition or the subject of a negative proposition) in at least one premise.\n2. Avoiding Two Negative Premises: A valid conclusion cannot be drawn from two negative premises (e.g., "Some S are not P" and "No S is P").\n3. Negative Consistency: A negative premise implies a negative conclusion (if there is a negative premise, the conclusion must be negative).\n4. Assertion Consistency: Two affirmative premises (e.g., "Every A is B") imply an affirmative conclusion.\n5. Decomposition of Terms in the Conclusion: If a term is distributed in the conclusion, it must also be distributed in the premise from which it originates (e.g., S or P). Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check these syllogism premises and make a conclusion based on them:\n{syll}\nProvide a brief, not long of a response!\nDO NOT REFER TO RULES BY THEIR NUMBERS/IDS!'}]

    reply = local_prompt(messages)

    return jsonify({"result": reply})


# Local AI function
async def local_prompt(messages):
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={'messages': messages, 'max_tokens': -1}, timeout=240.0)
    reply = response.json()['choices'][0]['message']['content']
    if "</think>" in reply:
        reply = reply.split("</think>")[1].strip()
    return reply


# Remote AI function
## TODO: ADAM
## Otrzymuje tablicę obiektów json: [{'role': 'system', 'content': 'system_prompt'}, {'role': 'user', 'content': 'user_prompt'}] i nazwę/identyfikator modelu
## Odpytuje wybrany model groq i zwraca odpowiedź
## Format wartości zmiennej 'model' taki jak ci odpowiada, spisz tylko potem jakie wartości dozwolone mają być przekazywane w tej zmiennej
## Importy zapisz na początku funkcji remote_prompt
## Daj znać, jeśli wersje jakichś bibliotek mają być nie najnowsze, ale konkretne
## Daj znać, jeśli czegoś dodatkowego ci potrzeba, albo pomocy z czymś
async def remote_prompt(messages, model):
    reply = 'placeholder'
    return reply


# Generate syllogism function
## TODO: Martin
## Otrzymuje: num - liczba sylogizmów, sampling - zawartość sampling file, min_a, max_a - liczby tak jak w generatorze
## Katalog biblioteki, w którym są te jej wymagane dwa pliki .py i podkatalog 'history'
## Odpytuje plik biblioteki generowania
## Zakładamy myślę, że zawsze jest tryb 'Syllogism', chociaż ewentualnie można dodać w parametry przekazywane do funkcji generate syllo argument 'mode == "Syllogism" ' i wtedy będzie z domyślną wartością, której nie będziemy musieli ustawiać, ale będzie w razie czego można dostosować
## Wczytanie biblioteki zmienione tak, żeby w wywołaniu przyjmowało sampling jako treść json 
## Końcówka funkcji głównej kodu biblioteki zmieniona tak, żeby poza zapisywaniem do csv, zwracało też w return wyniki
## Zapis csv do katalogu history/ w katalogu biblioteki, nazwy plików to może być na przykład data i godzina w formacie "rrrr-MM-dd_HH:mm:ss"
## Najlepiej żeby potem funkcja generate_syllo zwracała tablicę obiektów [{'premises': '', 'conclusion': '', 'sat': 0/1}, {...}, ...], ale jeśli tak wolisz, to DataFramem też w porządku zamiast json
## Importy zapisz na początku funkcji generate_syllo
## Daj znać, jeśli wersje jakichś bibliotek mają być nie najnowsze, ale konkretne
## Daj znać, jeśli czegoś dodatkowego ci potrzeba, albo pomocy z czymś
async def generate_syllo(num, sampling, min_a, max_a):
    result = []
    return result


# Access to files
@app.route("/scripts/<filename>")
async def serve_scripts(filename):
    return await send_from_directory(os.path.join(".", "scripts"), filename)

@app.route("/styles/<filename>")
async def serve_styles(filename):
    return await send_from_directory(os.path.join(".", "styles"), filename)


# Run
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=os.environ.get("MAIN_ADDR", "0.0.0.0"),
        port=51790,
        workers=4,
    )