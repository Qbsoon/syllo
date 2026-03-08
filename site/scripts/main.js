(function () {
    // Sekcja pobierania elementów
    //Buttons
    const sendBtn = document.getElementById("send");
    const uploadBtn = document.getElementById("syllUpload");
    const modeTextBtn = document.getElementById('modeText');
    const modeFileBtn = document.getElementById('modeFile');
    //Inputs
    const syllEl = document.getElementById("syll");
    const typeEl = document.getElementById("type");
    const modelEl = document.getElementById("model");
    const uploadDialog = document.getElementById("uploadDialog");
    const syllFile = document.getElementById("syllFile");
    //Output
    const resultEl = document.getElementById("result");
    const spinner = document.getElementById("spinner");
    const statusText = document.getElementById("status-text");
    const resultFile = document.getElementById("resultFile");

    // Przełączniki Tekst/Plik
    modeTextBtn.addEventListener('click', () => {
        document.querySelectorAll('.type-one').forEach(el => el.classList.remove('hidden'));
        document.querySelectorAll('.type-file').forEach(el => el.classList.add('hidden'));
        modeTextBtn.classList.add('active');
        modeFileBtn.classList.remove('active');
    });

    modeFileBtn.addEventListener('click', () => {
        document.querySelectorAll('.type-one').forEach(el => el.classList.add('hidden'));
        document.querySelectorAll('.type-file').forEach(el => el.classList.remove('hidden'));
        modeTextBtn.classList.remove('active');
        modeFileBtn.classList.add('active');
    });

    // Sekcja logiki zapytania
    let cooldown = false;

    sendBtn.addEventListener("click", async () => {
        if (cooldown) {
            statusEl.textContent = "Odczekaj 3 sekundy między zapytaniami.";
            return;
        }

        if (modeTextBtn.classList.contains('active')) {
            const syll = encodeURIComponent(syllEl.value);
            const type = encodeURIComponent(typeEl.value);
            const model = encodeURIComponent(modelEl.value);

            spinner.classList.remove("hidden");
            let elapsed = 0;
            statusText.textContent = " Przetwarzanie... 0.0s";
            const timer = setInterval(() => {
                elapsed += 100;
                statusText.textContent = ` Przetwarzanie... ${(elapsed / 1000).toFixed(1)}s`;
            }, 100);

            sendBtn.disabled = true;
            cooldown = true;

            try {
                const res = await fetch("/api/dologic", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ syll, type, model }),
                });

                clearInterval(timer);
                spinner.classList.add("hidden");

                if (res.status === 429) {
                    statusEl.textContent = "Ograniczenie przepustowości - poczekaj 3 sekundy.";
                } else if (res.ok) {
                    const data = await res.json();
                    resultEl.value = data.result;
                    statusText.textContent = `Czas: ${(elapsed / 1000).toFixed(1)}s`;
                } else {
                    statusText.textContent = "Error: " + res.statusText;
                }
            } catch (err) {
                clearInterval(timer);
                spinner.classList.add("hidden");
                statusEl.textContent = "Network error.";
            }

            setTimeout(() => {
                cooldown = false;
                sendBtn.disabled = false;
            }, 3000);
        }
        else if (modeFileBtn.classList.contains('active')) {
            const filename = syllFile.dataset.value;
            if (filename != '') {
                const filePass = encodeURIComponent(filename);
                const type = encodeURIComponent(typeEl.value);
                const model = encodeURIComponent(modelEl.value);

                spinner.classList.remove("hidden");
                let elapsed = 0;
                statusText.textContent = " Przetwarzanie... 0.0s";
                const timer = setInterval(() => {
                    elapsed += 100;
                    statusText.textContent = ` Przetwarzanie... ${(elapsed / 1000).toFixed(1)}s`;
                }, 100);

                sendBtn.disabled = true;
                cooldown = true;
                
                try {
                    const response = await fetch('/api/domorelogic', {
                        method: 'POST',
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ filePass, type, model }),
                    });

                    clearInterval(timer);
                    spinner.classList.add("hidden");

                    if (response.status === 429) {
                        statusEl.textContent = "Ograniczenie przepustowości - poczekaj 3 sekundy.";
                    }

                    const result = await response.json()
                    if (result.success) {
                        resultFile.download = filename;
                        resultFile.href = `uploads/${filename}`;
                        resultFile.parentElement.classList.remove('hidden');
                    }
                    else {
                        console.log('Processing file failed');
                        throw new Error(procResult.error || 'Processing file failed.');
                    }
                } catch (err) {
                    clearInterval(timer);
                    spinner.classList.add("hidden");
                    statusEl.textContent = "Network error.";
                }

                setTimeout(() => {
                    cooldown = false;
                    sendBtn.disabled = false;
                }, 3000);
            }
        }
    });

    uploadBtn.addEventListener("click", async () => {
        uploadDialog.click();
    })

    uploadDialog.addEventListener('change', async (event) => {
        const file = event.target.files[0];
        if (!file) {
            console.log("No file selected.");
            return;
        }

        const allowedTypes = ['text/csv', 'application/vnd.ms-excel', 'text/plain'];
        if (!allowedTypes.includes(file.type.toLowerCase())) {
            alert("Nieprawidłowy typ pliku");
            uploadDialog.value = '';
            return;
        }

        const formData = new FormData();
        formData.append('sylloFile', file);

        try {
            resultFile.download = ''
            resultFile.href = ''

            const response = await fetch('/api/upload-syllos', {
                method: 'POST',
                body: formData,
            });

            if (response.status === 413) {
                const errorData = await response.json();
                alert(errorData.error || `Przekroczono limit rozmiaru: ${errorData.limit} MB.`);
                return;
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Server error during upload.' }));
                throw new Error(errorData.error || `Upload failed with status: ${response.status}`);
            }

            const result = await response.json();
            if (result.success && result.filename) {
                if (syllFile) {
                    syllFile.value = file.name;
                    syllFile.value = file.name;
                    syllFile.dataset.value = result.filename;
                    resultFile.download = '';
                    resultFile.href = '';
                    resultFile.parentElement.classList.add('hidden');
                }
            } else {
                throw new Error(result.error || 'Upload failed: No filename returned.');
            }
        } catch (error) {
            console.error('Error uploading file:', error);
            alert(`Błąd wgrywania pliku: ${error.message}`);
        } finally {
            uploadDialog.value = '';
        }
    });

    syllFile.addEventListener('dragover',  (e) => {
        e.preventDefault();
        syllFile.classList.add('dragover');
    });

    syllFile.addEventListener('dragleave', () => {
        syllFile.classList.remove('dragover');
    });

    syllFile.addEventListener('drop', async (e) => {
        e.preventDefault();
        syllFile.classList.remove('dragover');
        const file = e.dataTransfer.files[0];

        const allowedTypes = ['text/csv', 'application/vnd.ms-excel', 'text/plain'];
        if (!allowedTypes.includes(file.type.toLowerCase())) {
            alert("Nieprawidłowy typ pliku");
            uploadDialog.value = '';
            return;
        }

        const formData = new FormData();
        formData.append('sylloFile', file);

        try {
            const response = await fetch('/api/upload-syllos', {
                method: 'POST',
                body: formData,
            });

            if (response.status === 413) {
                const errorData = await response.json();
                alert(errorData.error || `Przekroczono limit rozmiaru: ${errorData.limit} MB.`);
                return;
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Server error during upload.' }));
                throw new Error(errorData.error || `Upload failed with status: ${response.status}`);
            }

            const result = await response.json();
            if (result.success && result.filename) {
                if (syllFile) {
                    syllFile.value = file.name;
                    syllFile.dataset.value = result.filename;
                    resultFile.download = '';
                    resultFile.href = '';
                    resultFile.parentElement.classList.add('hidden');
                }
            } else {
                throw new Error(result.error || 'Upload failed: No filename returned.');
            }
        } catch (error) {
            console.error('Error uploading file:', error);
            alert(`Błąd wgrywania pliku: ${error.message}`);
        } finally {
            uploadDialog.value = '';
        }
    });

    new MutationObserver(() => {
        resultFile.parentElement.classList.toggle('hidden', resultFile.download == '');
    }).observe(resultFile, { attributes: true, attributeFilter: ['href'] });
})();