(function () {
    // Sekcja pobierania elementów
    //Buttons
    const sendBtn = document.getElementById("send");
    const uploadBtn = document.getElementById("syllUpload");
    const modeTextBtn = document.getElementById('modeText');
    const modeFileBtn = document.getElementById('modeFile');
    const generateBtn = document.getElementById('generateBtn');
    const toggleGenerateBtn = document.getElementById('toggleGenerate');
    const closeConfusion = document.getElementById('closeConfusion');
    //Inputs
    const syllEl = document.getElementById("syll");
    const typeEl = document.getElementById("type");
    const modelEl = document.getElementById("model");
    const reasonEffort = document.getElementById("reasonEffort");
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
    const confusionContent = document.getElementById('confusionContent');
    //Others
    const sidePanel = document.getElementById('sidePanel');
    const confusionPanel = document.getElementById('confusionPanel');

    // Przełączniki Tekst/Plik
    if (modeTextBtn) {
        modeTextBtn.addEventListener('click', () => {
            document.querySelectorAll('.type-one').forEach(el => el.classList.remove('hidden'));
            document.querySelectorAll('.type-file').forEach(el => el.classList.add('hidden'));
            modeTextBtn.classList.add('active');
            modeFileBtn.classList.remove('active');
        });
    }

    if (modeFileBtn) {
        modeFileBtn.addEventListener('click', () => {
            document.querySelectorAll('.type-one').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.type-file').forEach(el => el.classList.remove('hidden'));
            modeTextBtn.classList.remove('active');
            modeFileBtn.classList.add('active');
        });
    }

    // Sekcja logiki zapytania
    let cooldown = false;

    if (sendBtn) {
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
                const effort = encodeURIComponent(reasonEffort.value);

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
                        body: JSON.stringify({ syll, type, model, effort }),
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
                    const effort = encodeURIComponent(reasonEffort.value);

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
                            ws.send(JSON.stringify({ file: filePass, type, model, effort }));
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
                                    resultFile.href = `results/${m.file}`;
                                    resultFile.parentElement.classList.remove('hidden');
                                    iStatusText.textContent = "Zakończono.";
                                    ws.close();
                                } else if (m.type === 'confusion') {
                                    try {
                                        const labels = m.labels || [];
                                        const matrix = m.matrix || [];
                                        renderConfusion(labels, matrix);
                                        confusionPanel.classList.remove('hidden');
                                        document.body.classList.add('confusion-active');
                                        const metricsEl = document.getElementById('confusionMetrics');
                                        if (m.metrics && metricsEl) {
                                            const fmtv = (v) => (typeof v === 'number' ? v.toFixed(3) : v);
                                            metricsEl.textContent = `Accuracy: ${fmtv(m.metrics.accuracy)}\nMacro Precision: ${fmtv(m.metrics.macro_precision)}\nMacro Recall: ${fmtv(m.metrics.macro_recall)}\nMacro F1: ${fmtv(m.metrics.macro_f1)}\nŁącznie wierszy: ${m.metrics.total}`;
                                        }
                                    } catch (err) {
                                        console.error('Error rendering confusion matrix', err);
                                    }
                                } else if (m.type === 'error' || m.type === 'row_error') {
                                    console.error('Server error:', m);
                                    iStatusText.textContent = "Błąd serwera podczas przetwarzania.";
                                    ws.close();
                                } else if (m.type === 'rate_limit') {
                                    if (!iStatusText.textContent.includes('Limit Groq')) {
                                        iStatusText.textContent = iStatusText.textContent + " Limit Groq, próba ponawiania"
                                    }
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
    }

    // Sekcja logiki wgrywania csv

    if (uploadBtn) {
        uploadBtn.addEventListener("click", async () => {
            uploadDialog.click();
        })
    }

    if (uploadDialog) {
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
    }


    if (syllFile) {
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
    }

    new MutationObserver(() => {
        resultFile.parentElement.classList.toggle('hidden', resultFile.download == '');
    }).observe(resultFile, { attributes: true, attributeFilter: ['href'] });


    // Niestandardowe zapytanie

    if (typeEl) {
        typeEl.addEventListener('change', () => {
            if (typeEl.value == -1) {
                customSPrompt.parentElement.classList.remove('hidden');
            } else {
                customSPrompt.parentElement.classList.add('hidden');
            }
        });
    }

    // Generowanie sylogizmu
    let genCooldown = false;

    if (generateBtn) {
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
    }

    // Przełączanie panelu Generowanie
    if (toggleGenerateBtn) {
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
    }

    // Confusion matrix
    function renderConfusion(labels, matrix) {
        if (!Array.isArray(labels) || !Array.isArray(matrix)) {
            confusionContent.innerText = 'Nieprawidłowy format danych.';
            return;
        }

        let html = '<table><thead><tr><th></th>';
        for (let lb of labels) {
            html += `<th>${escapeHtml(String(lb))}</th>`;
        }
        html += '</tr></thead><tbody>';

        for (let i = 0; i < matrix.length; i++) {
            const row = matrix[i] || [];
            html += `<tr><th>${escapeHtml(String(labels[i] || i))}</th>`;
            for (let j = 0; j < labels.length; j++) {
                const val = row[j] != null ? row[j] : '';
                html += `<td class="value">${escapeHtml(String(val))}</td>`;
            }
            html += '</tr>';
        }

        html += '</tbody></table>';
        confusionContent.innerHTML = html;

        try {
            let maxVal = 0;
            for (let r = 0; r < matrix.length; r++) {
                for (let c = 0; c < (matrix[r] || []).length; c++) {
                    const v = Number(matrix[r][c]) || 0;
                    if (v > maxVal) maxVal = v;
                }
            }

            const table = confusionContent.querySelector('table');
            if (table) {
                const rows = table.tBodies[0].rows;
                for (let i = 0; i < rows.length; i++) {
                    const cells = rows[i].cells;
                    for (let j = 1; j < cells.length; j++) {
                        const cell = cells[j];
                        const raw = cell.textContent.trim();
                        const val = parseFloat(raw.replace(/[^0-9eE+\-.]/g, '')) || 0;
                        const ratio = maxVal > 0 ? (val / maxVal) : 0;
                        const alpha = 0.08 + 0.7 * ratio;
                        cell.style.background = `rgba(108,92,231,${alpha})`;
                        cell.style.transition = 'background 220ms ease, color 220ms ease';
                        cell.style.color = ratio > 0.45 ? '#fff' : '#e2e2e8';
                    }
                }
            }
        } catch (e) {
            console.error('Heatmap rendering failed', e);
        }
    }

    function escapeHtml(s) {
        return s.replace(/[&<>"']/g, function (c) {
            return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
        });
    }

    if (closeConfusion) {
        closeConfusion.addEventListener('click', () => {
            confusionPanel.classList.add('hidden');
            document.body.classList.remove('confusion-active');
            confusionContent.innerHTML = 'Brak danych.';
        });
    }

    if (reasonEffort && modelEl) {
        modelEl.addEventListener('change', () => {
            if (['openai/gpt-oss-20b','openai/gpt-oss-120b','qwen/qwen3-32b'].includes(modelEl.value)) {
                reasonEffort.parentElement.classList.remove('hidden');
            } else {
                reasonEffort.parentElement.classList.add('hidden');
                reasonEffort.value = 'none';
            }
        })
    }
})();