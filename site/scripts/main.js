(function () {
    // Sekcja pobierania elementów
    //Buttons
    const sendBtn = document.getElementById("send");
    const uploadBtn = document.getElementById("syllUpload");
    const modeTextBtn = document.getElementById('modeText');
    const modeFileBtn = document.getElementById('modeFile');
    const generateBtn = document.getElementById('generateBtn');
    const toggleGenerateBtn = document.getElementById('toggleGenerate');
    //Inputs
    const syllEl = document.getElementById("syll");
    const typeEl = document.getElementById("type");
    const modelEl = document.getElementById("model");
    const uploadDialog = document.getElementById("uploadDialog");
    const syllFile = document.getElementById("syllFile");
    const customSPrompt = document.getElementById("customSPrompt");
    const numSyll = document.getElementById("numSyll");
    const minPremise = document.getElementById('minPremise');
    const maxPremise = document.getElementById('maxPremise');
    //Output
    const resultEl = document.getElementById("result");
    const spinner = document.getElementById("spinner");
    const tStatusText = document.getElementById("time-status-text");
    const iStatusText = document.getElementById("i-status-text");
    const genSpinner = document.getElementById('genSpinner');
    const genTStatusText = document.getElementById('gen-time-status-text');
    const genIStatusText = document.getElementById("gen-i-status-text");
    const resultFile = document.getElementById("resultFile");
    //Others
    const sidePanel = document.getElementById('sidePanel');

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
            tStatusText.textContent = "Poczekaj na zakończenie zapytania.";
            return;
        }

        iStatusText.textContent = '';
        tStatusText.textContent = '';

        if (modeTextBtn.classList.contains('active')) {
            const syll = encodeURIComponent(syllEl.value);
            let type = '';
            if (typeEl.value != -1) {
                type = encodeURIComponent(typeEl.value);
            }
            else
            {
                type = encodeURIComponent(customSPrompt.value);
            }
            const model = encodeURIComponent(modelEl.value);

            spinner.classList.remove("hidden");
            let elapsed = 0;
            tStatusText.textContent = " Przetwarzanie... 0.0s";
            const timer = setInterval(() => {
                elapsed += 100;
                tStatusText.textContent = ` Przetwarzanie... ${(elapsed / 1000).toFixed(1)}s`;
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
                    tStatusText.textContent = "Ograniczenie przepustowości - poczekaj 3 sekundy.";
                } else if (res.ok) {
                    const data = await res.json();
                    resultEl.value = data.result;
                    tStatusText.textContent = `Czas: ${(elapsed / 1000).toFixed(1)}s`;
                } else {
                    tStatusText.textContent = "Error: " + res.statusText;
                }
            } catch (err) {
                clearInterval(timer);
                spinner.classList.add("hidden");
                tStatusText.textContent = "Network error.";
            } finally {
                cooldown = false;
                sendBtn.disabled = false;
            }
        }
        else if (modeFileBtn.classList.contains('active')) {
            const filename = syllFile.dataset.value;
            if (filename != '') {
                const filePass = encodeURIComponent(filename);
                let type = '';
                if (typeEl.value != -1) {
                    type = encodeURIComponent(typeEl.value);
                }
                else
                {
                    type = encodeURIComponent(customSPrompt.value);
                }
                const model = encodeURIComponent(modelEl.value);

                spinner.classList.remove("hidden");
                let elapsed = 0;
                tStatusText.textContent = " Przetwarzanie... 0.0s";
                const timer = setInterval(() => {
                    elapsed += 100;
                    tStatusText.textContent = ` Przetwarzanie... ${(elapsed / 1000).toFixed(1)}s`;
                }, 100);

                sendBtn.disabled = true;
                cooldown = true;
                
                try {
                    const protocol = (location.protocol === 'https:') ? 'wss' : 'ws';
                    const wsUrl = `${protocol}://${location.host}/ws/domorelogic`;
                    const ws = new WebSocket(wsUrl);

                    ws.addEventListener('open', () => {
                        ws.send(JSON.stringify({ file: filePass, type, model }));
                        iStatusText.textContent = " Połączono. Przetwarzanie pliku...";
                    });

                    ws.addEventListener('message', (ev) => {
                        try {
                            const m = JSON.parse(ev.data);
                            if (m.type === 'progress') {
                                iStatusText.textContent = `Wiersz ${m.idx + 1}/${m.total}`;
                            } else if (m.type === 'started') {
                                iStatusText.textContent = `Rozpoczęto: ${m.file}`;
                            } else if (m.type === 'done') {
                                resultFile.download = filename;
                                resultFile.href = `uploads/${filename}`;
                                resultFile.parentElement.classList.remove('hidden');
                                iStatusText.textContent = "Zakończono.";
                                ws.close();
                            } else if (m.type === 'error' || m.type === 'row_error') {
                                console.error('Server error:', m);
                                iStatusText.textContent = "Błąd serwera podczas przetwarzania.";
                                ws.close();
                            }
                        } catch (err) {
                            console.error('WS parse error', err);
                        }
                    });

                    ws.addEventListener('close', () => {
                        spinner.classList.add('hidden');
                        clearInterval(timer);
                        cooldown = false;
                        sendBtn.disabled = false;
                        tStatusText.textContent = ` Czas: ${(elapsed / 1000).toFixed(1)}s`;
                    });

                    ws.addEventListener('error', (e) => {
                        console.error('WebSocket error', e);
                        iStatusText.textContent = "Błąd połączenia WebSocket.";
                        spinner.classList.add('hidden');
                        clearInterval(timer);
                    });

                } catch (err) {
                    clearInterval(timer);
                    spinner.classList.add("hidden");
                    iStatusText.textContent = "Network error.";
                }
            }
        }
    });

    // Sekcja logiki wgrywania csv

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


    // Niestandardowe zapytanie

    typeEl.addEventListener('change', () => {
        if (typeEl.value == -1) {
            customSPrompt.parentElement.classList.remove('hidden');
        } else {
            customSPrompt.parentElement.classList.add('hidden');
        }
    });

    // Generowanie sylogizmu
    let genCooldown = false;

    generateBtn.addEventListener('click', async () => {
        if (genCooldown) {
            tStatusText.textContent = "Poczekaj na koniec zapytania.";
            return;
        }

        const minA = encodeURIComponent(Number(minPremise.value) + 1);
        const maxA = encodeURIComponent(Number(maxPremise.value) + 1);

        genIStatusText.textContent = '';
        genTStatusText.textContent = '';
        genSpinner.classList.remove("hidden");
        let elapsed = 0;
        genTStatusText.textContent = " Przetwarzanie... 0.0s";
        const timer = setInterval(() => {
            elapsed += 100;
            genTStatusText.textContent = ` Przetwarzanie... ${(elapsed / 1000).toFixed(1)}s`;
        }, 100);

        generateBtn.disabled = true;
        genCooldown = true;

        try {
            if (modeTextBtn.classList.contains('active')) {
                const response = await fetch('/api/generateone', {
                    method: 'POST',
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ minA, maxA }),
                });
                if (response.status === 429) {
                    genTStatusText.textContent = "Ograniczenie przepustowości - poczekaj 3 sekundy.";
                } else if (response.ok) {
                    const result = await response.json();
                    
                    if (result.success) {
                        if (result.result) {
                            syllEl.value = result.result;
                        } else {
                            tStatusText.textContent = 'Something went wrong with retrieving the generated syllogism';
                        }
                    } else {
                        if (result.result) {
                            tStatusText.textContent = response.result;
                        } else {
                            tStatusText.textContent = 'Something went wrong with generating a syllogism';
                        }
                    }
                    genTStatusText.textContent = `Czas: ${(elapsed / 1000).toFixed(1)}s`;
                }
                clearInterval(timer);
                genSpinner.classList.add("hidden");
                genCooldown = false;
                generateBtn.disabled = false;
            } else if (modeFileBtn.classList.contains('active')) {
                const num = encodeURIComponent(numSyll.value);

                const protocol = (location.protocol === 'https:') ? 'wss' : 'ws';
                const wsUrl = `${protocol}://${location.host}/ws/generatemany`;
                const ws = new WebSocket(wsUrl);

                ws.addEventListener('open', () => {
                    ws.send(JSON.stringify({ num, minA, maxA }));
                    genIStatusText.textContent = " Połączono. Przetwarzanie...";
                });

                ws.addEventListener('message', (ev) => {
                    try {
                        const m = JSON.parse(ev.data);
                        if (m.type === 'done') {
                            syllFile.value = m.filename;
                            syllFile.dataset.value = m.filename;
                            resultFile.download = '';
                            resultFile.href = '';
                            resultFile.parentElement.classList.add('hidden');
                            genIStatusText.textContent = "Zakończono.";
                            ws.close();
                        } else if (m.type === 'error') {
                            console.error('Server error:', m);
                            genIStatusText.textContent = "Błąd serwera podczas przetwarzania.";
                            ws.close();
                        }
                    } catch (err) {
                        console.error('WS parse error', err);
                    }
                });

                ws.addEventListener('close', () => {
                    clearInterval(timer);
                    genSpinner.classList.add("hidden");
                    genCooldown = false;
                    generateBtn.disabled = false;
                    genTStatusText.textContent = ` Czas: ${(elapsed / 1000).toFixed(1)}s`;
                });

                ws.addEventListener('error', (e) => {
                    console.error('WebSocket error', e);
                    genIStatusText.textContent = "Błąd połączenia WebSocket.";
                    genSpinner.classList.add('hidden');
                    clearInterval(timer);
                });

            }
        } catch (error) {
            clearInterval(timer);
            genSpinner.classList.add("hidden");
            console.error('Error generating:', error);
            genTStatusText.textContent = `Błąd generowania sylogizmów: ${error.message}`;
        }
    })

    // Przełączanie panelu Generowanie
    toggleGenerateBtn.addEventListener('click', () => {
        const active = !sidePanel.classList.contains('hidden');
        if (active) {
            sidePanel.classList.add('hidden');
            document.body.classList.remove('generating-active');
            toggleGenerateBtn.classList.remove('active');
        } else {
            sidePanel.classList.remove('hidden');
            document.body.classList.add('generating-active');
            toggleGenerateBtn.classList.add('active');
        }
    });
})();