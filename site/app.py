# --- Imports ---
import os
from quart import Quart, render_template, request, jsonify, send_from_directory
from quart_rate_limiter import RateLimiter, rate_limit
from datetime import timedelta
import urllib.parse
import requests
import httpx
import uvicorn
from datetime import datetime
import pandas as pd
from werkzeug.utils import secure_filename


# --- 'Static' values ---
LOCAL_MODELS = ['qwen3_14b_q5km']
REMOTE_MODELS = []
UPLOAD_ARCHIVE = "uploads"
LCPP_URL = "http://127.0.0.1:51791/v1/chat/completions"


# --- App definition ---
app = Quart(__name__, template_folder="pages")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
RateLimiter(app)


# --- Main site ---
@app.route("/")
async def index():
    return await render_template("index.html")


# --- TODO: Jakub ---
## stype 2 - Sprawdzenie poprawności jako 0/1
## Pobieranie template
## Wyświetlanie tabeli wyników
## Czy logowanie KUL?
## Ładniejsze "Pobierz wyniki"
## Logowanie pojedynczych zapytań


# --- Process types/models function ---
async def figure_out(model, stype, syll, conc = ''):
    reply = 'Something went wrong.'

    messages = ""
    if stype == 0 or stype == '0':
        messages = [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. A - All x are y; E - No x are y; I - Some x are y; O - Some x are not y. Check if they\'re logically correct and explain their reasoning. Common checks:\n5 Rules (Classical Method)\n1. Middle Term Distribution (M): A middle term must be distributed (appear as the predicate of a general proposition or the subject of a negative proposition) in at least one premise.\n2. Avoiding Two Negative Premises: A valid conclusion cannot be drawn from two negative premises (e.g., "Some S are not P" and "No S is P").\n3. Negative Consistency: A negative premise implies a negative conclusion (if there is a negative premise, the conclusion must be negative).\n4. Assertion Consistency: Two affirmative premises (e.g., "Every A is B") imply an affirmative conclusion.\n5. Decomposition of Terms in the Conclusion: If a term is distributed in the conclusion, it must also be distributed in the premise from which it originates (e.g., S or P). Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check this syllogism:\n{syll}\nProvide a brief, not long of a response!\nDO NOT REFER TO RULES BY THEIR NUMBERS/IDS!'}]
    elif stype == 1 or stype == '1':
        messages =  [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. A - All x are y; E - No x are y; I - Some x are y; O - Some x are not y. Check if they\'re logically correct and explain their reasoning. Common checks:\n5 Rules (Classical Method)\n1. Middle Term Distribution (M): A middle term must be distributed (appear as the predicate of a general proposition or the subject of a negative proposition) in at least one premise.\n2. Avoiding Two Negative Premises: A valid conclusion cannot be drawn from two negative premises (e.g., "Some S are not P" and "No S is P").\n3. Negative Consistency: A negative premise implies a negative conclusion (if there is a negative premise, the conclusion must be negative).\n4. Assertion Consistency: Two affirmative premises (e.g., "Every A is B") imply an affirmative conclusion.\n5. Decomposition of Terms in the Conclusion: If a term is distributed in the conclusion, it must also be distributed in the premise from which it originates (e.g., S or P). Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check these syllogism premises and make a conclusion based on them:\n{syll}\nProvide a brief, not long of a response!\nDO NOT REFER TO RULES BY THEIR NUMBERS/IDS!'}]
    else:
        reply += " Wrong action type."

    if (model in LOCAL_MODELS):
        reply = await local_prompt(messages)
    elif (model in REMOTE_MODELS):
        reply = await remote_prompt(messages, model)
    else:
        reply += " Wrong model."

    return reply


# --- Ask AI endpoint ---
@app.route("/api/dologic", methods=["POST"])
@rate_limit(1, timedelta(seconds=3))
async def do_logic():
    data = await request.get_json()

    syll = urllib.parse.unquote(data.get("syll", ""))
    stype = urllib.parse.unquote(data.get("type", ""))
    model = urllib.parse.unquote(data.get("model", ""))

    reply = await figure_out(model, stype, syll)

    return jsonify({"result": reply})


# -- Process file endpoint ---
@app.route("/api/domorelogic", methods=["POST"])
@rate_limit(1, timedelta(seconds=3))
async def do_more_logic():
    data = await request.get_json()

    file = urllib.parse.unquote(data.get("filePass", ""))
    stype = urllib.parse.unquote(data.get("type", ""))
    model = urllib.parse.unquote(data.get("model", ""))

    syllos = pd.read_csv("uploads/" + file)
    syllos['response'] = ''

    for i, syllo in syllos.iterrows():
        reply = await figure_out(model, stype, syllo['premises'], syllo['conclusion'])
        syllos.at[i, 'response'] = reply
    
    syllos.to_csv("uploads/" + file)
    return jsonify({"success": True})


# --- Local AI function ---
async def local_prompt(messages):
    async with httpx.AsyncClient() as client:
        response = await client.post(LCPP_URL, json={'messages': messages, 'max_tokens': -1}, timeout=240.0)
    reply = response.json()['choices'][0]['message']['content']
    if "</think>" in reply:
        reply = reply.split("</think>")[1].strip()
    return reply


# --- Remote AI function ---
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


# --- Generate syllogism function ---
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


# --- Access to files ---
@app.route("/scripts/<filename>")
async def serve_scripts(filename):
    return await send_from_directory(os.path.join(".", "scripts"), filename)

@app.route("/styles/<filename>")
async def serve_styles(filename):
    return await send_from_directory(os.path.join(".", "styles"), filename)

@app.route("/uploads/<filename>")
async def server_download(filename):
    return await send_from_directory(os.path.join(".", "uploads"), filename)


# Upload section
@app.route('/api/upload-syllos', methods=['POST'])
async def upload_file():

	files = await request.files
	if 'sylloFile' not in files:
		return jsonify({"success": False, "error": "No syllogism file part in the request"}), 400
	file = files['sylloFile']

	if file.filename == '':
		return jsonify({"success": False, "error": "No selected file"}), 400

	allowed_extensions = ['csv']
	original_filename = secure_filename(file.filename)
	file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''

	if not file_ext or file_ext not in allowed_extensions:
		return jsonify({"success": False, "error": "Invalid file type. Only CSV allowed."}), 400

	os.makedirs(UPLOAD_ARCHIVE, exist_ok=True)

	new_filename = f"upload_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{file_ext}"

	upload_filepath = os.path.join(UPLOAD_ARCHIVE, new_filename)

	try:
		await file.save(upload_filepath)
		return jsonify({"success": True, "filename": new_filename})
	except Exception as e:
		return jsonify({"success": False, "error": "Server error while saving the file."}), 500
	

# --- Error Handlers ---
@app.errorhandler(413)
async def request_entity_too_large(error):
	app.logger.warning(f"Upload failed: File too large (413). Limit is {app.config.get('MAX_CONTENT_LENGTH') / (1024*1024)}MB.")
	return jsonify(success=False, error="File is too large. Please upload a file smaller than {}MB.".format(app.config.get('MAX_CONTENT_LENGTH') // (1024*1024)), limit=app.config.get('MAX_CONTENT_LENGTH') // (1024*1024)), 413


# --- Run ---
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=os.environ.get("MAIN_ADDR"),
        port=51790,
        workers=4,
    )